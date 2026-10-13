"""Pipeline entry point.

    python scripts/run.py download                 # Cboe, FRED, Yahoo (+ market panel)
    python scripts/calibrate.py                    # Tier-B surface on development (writes configs/surface.yaml)
    python scripts/run.py fit-strikes              # vol-unit z1, z2 on development (writes configs/strategy.yaml)
    python scripts/run.py track --period validation      # pricer tracking vs Cboe indices
    python scripts/run.py analyse --period development,validation
    python scripts/run.py analyse --period test,recent   # needs PREREG_HASH (see qcore.splits)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy.optimize import brentq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qcore.splits import Splits, guard  # noqa: E402

from collars.config import RESEARCH, RESULTS, ROOT, load  # noqa: E402

PREREG = RESEARCH / "preregistration.md"
TABLES = RESULTS / "tables"


def _params():
    from collars.surface import SurfaceParams
    return SurfaceParams.from_dict(yaml.safe_load((ROOT / "configs" / "surface.yaml").read_text()))


def _strategy_cfg() -> dict:
    return yaml.safe_load((ROOT / "configs" / "strategy.yaml").read_text())


def _market():
    from collars.data.load import load as load_market
    return load_market()


def _check(period: str) -> tuple[str, str]:
    splits = Splits.from_dict(load("splits"))
    guard(period, PREREG)
    lo, hi = getattr(splits, period)
    if hi is None:
        hi = _market().index[-1].strftime("%Y-%m")
    return lo, hi


def step_download() -> None:
    from collars.data import download
    from collars.data.load import build
    for f in (download.download_cboe, download.download_fred, download.download_yahoo):
        for k, v in f().items():
            print(k, v)
    build()


def step_fit_strikes() -> None:
    """z_j such that the development-period average moneyness K_j/S equals m_j (3-month tenor, every day)."""
    from collars.surface import implied_vol, vol_matrix, vs_vol
    lo, hi = _check("development")
    m = _market().loc[lo:hi]
    p = _params()
    tau = 91 / 365
    fs = np.exp((m["r"] - m["q"]).to_numpy() * tau)                  # F / S
    V = vol_matrix(m)
    atm = np.array([float(implied_vol(1.0, 1.0, tau, vs_vol(V[i], tau), p)) for i in range(len(m))]) * np.sqrt(tau)
    cfg = {"m1": 0.95, "m2": 0.80}
    for j, mj in (("z1", 0.95), ("z2", 0.80)):
        cfg[j] = round(float(brentq(lambda z: np.mean(fs * np.exp(-z * atm)) - mj, 0.0, 10.0)), 5)
    cfg["fitted_on"] = f"development {lo}..{hi}"
    cfg["fitted_at"] = datetime.now().isoformat(timespec="seconds")
    (ROOT / "configs" / "strategy.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    print(cfg)


def step_track(period: str) -> None:
    from collars.indices import tracking
    lo, hi = _check(period)
    t = tracking(_market(), _params(), lo, hi)
    t.to_csv(TABLES / f"tracking_{period}.csv")
    print(period, "\n", t.round(4))


def _specs():
    from collars.strategy import CollarSpec
    c = _strategy_cfg()
    return (CollarSpec(m1=c["m1"], m2=c["m2"]),
            CollarSpec(m1=c["m1"], m2=c["m2"], strikes="vol", z1=c["z1"], z2=c["z2"]))


def step_analyse(period: str, n_boot: int) -> dict:
    from collars import analysis as A
    from collars.attribution import attribute, summarise
    from collars.strategy import CollarSpec, beta_matched, ladders, run_phase, run_phases
    lo, hi = _check(period)
    market, p = _market(), _params()
    fixed, vol = _specs()
    rf = (market["r"].shift() * market.index.to_series().diff().dt.days / 365).fillna(0)
    out: dict = {"period": period, "window": [lo, hi], "surface": p.__dict__, "run_at": datetime.now().isoformat()}

    # ---- RQ1: 63 phases, 21 ladders
    navs, rolls = run_phases(market, fixed, p, lo, hi)
    tab = A.phase_table(navs, rf)
    lad = ladders(navs)
    lad_tab = A.phase_table(lad, rf)
    tab.to_csv(TABLES / f"{period}_phases_fixed.csv")
    lad_tab.to_csv(TABLES / f"{period}_ladders.csv")
    navs.to_parquet(RESULTS / "runs" / f"{period}_navs_fixed.parquet")
    out["rq1"] = {"single": A.dispersion(tab), "ladder": A.dispersion(lad_tab),
                  "h1": A.h1_bootstrap(navs, n_boot=n_boot)}
    allr = pd.concat(rolls.values())
    allr["cap"] = allr["K2"] / allr["S0"] - 1
    out["caps"] = {"mean": allr["cap"].mean(), "p10": allr["cap"].quantile(.1), "p90": allr["cap"].quantile(.9),
                   "share_in_3.5_5.5": float(allr["cap"].between(0.035, 0.055).mean()),
                   "phase0_mean": rolls[0]["cap"].mean() if "cap" in rolls[0] else
                   float((rolls[0]["K2"] / rolls[0]["S0"] - 1).mean()),
                   "cost_bp_per_reset": float((allr["cost"] / allr["S0"]).mean() * 1e4)}

    # ---- RQ3: phase 0 (the fund's calendar) and the ladder vs beta-matched, plus distribution over phases
    rq3 = {}
    for name, nav, rr in (("phase0", navs[0], rolls[0]),):
        bench = beta_matched(market, rr, nav.index)
        rq3[name] = A.beta_matched_comparison(nav, bench, rf, n_boot=n_boot)
        rq3[name]["beta_ex_mean"] = float(rr["delta"].mean())
    per_phase = {}
    for ph in navs.columns:
        b = beta_matched(market, rolls[ph], navs[ph].index)
        mc, mb = A.monthly(navs[ph]), A.monthly(b)
        per_phase[ph] = {"return_forgone": A.metrics(b, rf)["ann_return"] - tab.loc[ph, "ann_return"],
                         "cvar95_reduction": A.cvar(mb) - A.cvar(mc)}
    pp = pd.DataFrame(per_phase).T
    pp.to_csv(TABLES / f"{period}_rq3_per_phase.csv")
    rq3["share_phases_collar_beats_bench_return"] = float((pp["return_forgone"] < 0).mean())
    rq3["share_phases_cvar_reduced"] = float((pp["cvar95_reduction"] > 0).mean())
    out["rq3"] = rq3

    # ---- benchmarks for phase 0
    spx = (market["spxtr"] / market["spxtr"]).reindex(navs.index)
    tr = market["spxtr"].reindex(navs.index)
    bm = {"collar_phase0": navs[0], "spx_tr": tr / tr.iloc[0],
          "beta_matched_phase0": beta_matched(market, rolls[0], navs.index)}
    for k in ("CLLZ", "PPUT", "BXM"):
        s = market[k].reindex(navs.index).ffill()
        bm[k] = s / s.iloc[0]
    from collars.config import RAW
    jh = pd.read_csv(RAW / "yahoo_JHEQX.csv", index_col=0, parse_dates=True)["Close"].reindex(navs.index).ffill()
    jh_overlap = jh.dropna()
    if jh.notna().iloc[0]:
        bm["JHEQX_nav"] = jh / jh.iloc[0]
    bm_tab = pd.DataFrame({k: {**A.metrics(v, rf)} for k, v in bm.items()}).T
    for k, v in bm.items():
        bm_tab.loc[k, "sharpe_ci_lo"], bm_tab.loc[k, "sharpe_ci_hi"] = A.sharpe_ci(v, rf, n_boot=n_boot)
    bm_tab.to_csv(TABLES / f"{period}_benchmarks.csv")
    pd.DataFrame(bm).to_parquet(RESULTS / "runs" / f"{period}_benchmark_navs.parquet")
    if len(jh_overlap) > 250:   # fund NAV (incl. stock selection and fees) vs the phase-0 reconstruction, on the overlap
        c0 = navs[0].reindex(jh_overlap.index)
        a, b = c0.pct_change().dropna(), jh_overlap.pct_change().dropna()
        ma, mb = A.monthly(c0), A.monthly(jh_overlap)
        out["jheqx_tracking"] = {"from": str(jh_overlap.index[0].date()), "corr_daily": float(a.corr(b)),
                                 "te_ann_daily": float((a - b).std() * np.sqrt(252)),
                                 "corr_monthly": float(ma.corr(mb)),
                                 "te_ann_monthly": float((ma - mb).std() * np.sqrt(12)),
                                 "ann_return_model": float(A.metrics(c0 / c0.iloc[0], rf)["ann_return"]),
                                 "ann_return_fund": float(A.metrics(jh_overlap / jh_overlap.iloc[0], rf)["ann_return"])}

    # ---- RQ2: fixed vs vol-unit strikes, hedge-effectiveness stability across VIX regimes
    vnavs, vrolls = run_phases(market, vol, p, lo, hi)
    vtab = A.phase_table(vnavs, rf)
    vtab.to_csv(TABLES / f"{period}_phases_volstrikes.csv")
    st = {}
    for ph in navs.columns:
        reg = A.vix_regime(market, rolls[ph].index)
        hf = A.hedge_effectiveness(navs[ph], market, reg)
        hv = A.hedge_effectiveness(vnavs[ph], market, A.vix_regime(market, vrolls[ph].index))
        st[ph] = {"he_fixed_low": hf[0], "he_fixed_mid": hf[1], "he_fixed_high": hf[2],
                  "he_vol_low": hv[0], "he_vol_mid": hv[1], "he_vol_high": hv[2],
                  "stab_fixed": hf.max() - hf.min(), "stab_vol": hv.max() - hv.min()}
    st = pd.DataFrame(st).T
    st.to_csv(TABLES / f"{period}_rq2_stability.csv")
    d = st["stab_vol"] - st["stab_fixed"]
    out["rq2"] = {"stab_fixed_mean": st["stab_fixed"].mean(), "stab_vol_mean": st["stab_vol"].mean(),
                  "diff_mean": d.mean(), "share_phases_vol_more_stable": float((d < 0).mean()),
                  "he_fixed_by_regime": st[["he_fixed_low", "he_fixed_mid", "he_fixed_high"]].mean().to_dict(),
                  "he_vol_by_regime": st[["he_vol_low", "he_vol_mid", "he_vol_high"]].mean().to_dict(),
                  "vol_single_sd": vtab["ann_return"].std(), "vol_mean_return": vtab["ann_return"].mean(),
                  "fixed_mean_return": tab["ann_return"].mean(), "n_nan_regimes": int(st.isna().sum().sum())}

    # ---- leg attribution (phase 0)
    attr = attribute(market, rolls[0], p, lo, hi)
    summ = summarise(attr)
    summ.to_csv(TABLES / f"{period}_attribution_phase0.csv")
    out["attribution_pct_per_year"] = summ.to_dict()

    # ---- ablations (phase 0 and dispersion over phases)
    abl = {}
    for name, legs in {"full": ("long_put", "short_put", "short_call"),
                       "no_short_put": ("long_put", "short_call"),
                       "no_short_call": ("long_put", "short_put"),
                       "no_long_put": ("short_put", "short_call")}.items():
        spec = CollarSpec(m1=fixed.m1, m2=fixed.m2, legs=legs)
        nv = run_phase(market, spec, p, lo, hi, 0).nav
        abl[name] = A.metrics(nv, rf)
    pd.DataFrame(abl).T.to_csv(TABLES / f"{period}_ablation_phase0.csv")
    out["ablation_phase0"] = abl

    (RESULTS / "runs").mkdir(exist_ok=True, parents=True)
    path = RESULTS / "runs" / f"summary_{period}.json"
    path.write_text(json.dumps(out, indent=2, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))
    print(json.dumps({k: out[k] for k in ("rq1", "rq2", "caps")}, indent=1, default=str)[:4000])
    return out


def step_robust(period: str, n_boot: int) -> pd.DataFrame:
    """Pre-registered robustness grid: H1 ratio and phase-0 metrics under alternative choices."""
    from dataclasses import replace

    from collars import analysis as A
    from collars.strategy import CollarSpec, ladders, run_phases
    lo, hi = _check(period)
    market, p = _market(), _params()
    base, _ = _specs()
    rf = (market["r"].shift() * market.index.to_series().diff().dt.days / 365).fillna(0)
    variants = {"baseline": (base, p)}
    for h in (0.0025, 0.005, 0.01):
        variants[f"half_spread_{h * 100:g}vp"] = (base, replace(p, h=h))
    for m1 in (0.93, 0.945, 0.95, 0.97):
        for m2 in (0.75, 0.80, 0.85):
            if (m1, m2) != (0.95, 0.80):
                variants[f"m{m1}_{m2}"] = (CollarSpec(m1=m1, m2=m2), p)
    variants["hedge_ratio_0.87"] = (CollarSpec(hedge_ratio=0.87), p)
    rows = {}
    for name, (spec, pp) in variants.items():
        navs, _ = run_phases(market, spec, pp, lo, hi)
        tab, lad = A.phase_table(navs, rf), A.phase_table(ladders(navs), rf)
        ratio = tab["ann_return"].std() / lad["ann_return"].std()
        rows[name] = {"sd_single": tab["ann_return"].std(), "sd_ladder": lad["ann_return"].std(), "ratio": ratio,
                      "range_single": tab["ann_return"].max() - tab["ann_return"].min(),
                      "phase0_ann": tab.loc[0, "ann_return"], "phase0_sharpe": tab.loc[0, "sharpe"],
                      "phase0_maxdd": tab.loc[0, "max_dd"], "mean_ann": tab["ann_return"].mean()}
        print(name, {k: round(v, 4) for k, v in rows[name].items()})
    if period == "test":   # the pre-registered "excluding 2020" check: 2021-2023 only
        navs, _ = run_phases(market, base, p, "2021-01", hi)
        tab, lad = A.phase_table(navs, rf), A.phase_table(ladders(navs), rf)
        rows["excl_2020"] = {"sd_single": tab["ann_return"].std(), "sd_ladder": lad["ann_return"].std(),
                             "ratio": tab["ann_return"].std() / lad["ann_return"].std(),
                             "range_single": tab["ann_return"].max() - tab["ann_return"].min(),
                             "phase0_ann": tab.loc[0, "ann_return"], "phase0_sharpe": tab.loc[0, "sharpe"],
                             "phase0_maxdd": tab.loc[0, "max_dd"], "mean_ann": tab["ann_return"].mean()}
    out = pd.DataFrame(rows).T
    out.to_csv(TABLES / f"{period}_robustness.csv")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["download", "fit-strikes", "track", "analyse", "robust"])
    ap.add_argument("--period", default="development")
    ap.add_argument("--n-boot", type=int, default=2000)
    a = ap.parse_args()
    if a.step == "download":
        step_download()
    elif a.step == "fit-strikes":
        step_fit_strikes()
    else:
        for per in a.period.split(","):
            {"track": step_track, "analyse": lambda x: step_analyse(x, a.n_boot),
             "robust": lambda x: step_robust(x, a.n_boot)}[a.step](per)
