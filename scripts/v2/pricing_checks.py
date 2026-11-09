"""Descriptive D1 (bid-ask haircut stress), D2 (QuantLib), D3 (SVI vs frozen surface on the one real chain),
D5 (capacity vs open interest). Prereg v2 'Descriptive'."""

from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd

from collars.pricing import greeks
from collars.strategy import CollarSpec, annualised_return, ladder, run_phase
from collars.surface import implied_vol, vol_matrix, vs_vol
from collars.v2 import chainfit, qlcheck
from collars.v2.common import RAW_CHAIN, ROOT, RUNS, SEEN, TABLES, dump, market, rf_daily, sharpe_ci, specs, surface, unlock


def chain_block(m, p) -> dict:
    chain, S, asof = chainfit.read_chain(RAW_CHAIN)
    i = len(m) - 1
    r, q = float(m["r"].iloc[i]), float(m["q"].iloc[i])
    target = pd.Timestamp(asof) + pd.Timedelta(days=91)
    exps = sorted(chain["expiry"].unique(), key=lambda e: abs((pd.Timestamp(e) - target).days))
    exp = exps[0]
    ht = chainfit.halfspread_table(chain, S, asof, exp, r, q)
    band = ht[(ht["mny"] >= 0.78) & (ht["mny"] <= 1.10)]
    puts, calls = band[band["kind"] == "put"], band[band["kind"] == "call"]
    h_chain = float(band["h"].median())
    # SVI vs frozen surface on the same expiry (OTM options, 0.80-1.05 moneyness)
    tau, F = float(ht["tau"].iloc[0]), float(ht["F"].iloc[0])
    fit = ht[(ht["mny"] >= 0.80) & (ht["mny"] <= 1.05)]
    k, w = np.log(fit["K"].to_numpy() / F), (fit["iv"].to_numpy() ** 2) * tau
    sp = chainfit.fit_svi(k, w)
    iv_svi = np.sqrt(np.maximum(chainfit.svi_w(k, sp), 1e-8) / tau)
    sig_vs = vs_vol(vol_matrix(m)[i], tau)
    iv_frz = np.array([float(implied_vol(K, F, tau, sig_vs, p)) for K in fit["K"]])
    # capacity: fund legs vs open interest at the nearest strikes
    nport = pd.read_csv(ROOT / "results" / "tables" / "nport_strikes_recent.csv")
    last = nport.iloc[-1]
    contracts = float(last["contracts"])
    ois = {}
    for name, K in (("long_put_K1", last["K1_mny"]), ("short_put_K2", last["K2_mny"]), ("short_call_Kc", last["Kc_mny"])):
        kind = "call" if "call" in name else "put"
        sub = chain[(chain["expiry"] == exp) & (chain["kind"] == kind)]
        near = sub.iloc[(sub["K"] - K * S).abs().argsort()[:3]]
        ois[name] = {"nearest_strikes": near["K"].tolist(), "open_interest_sum_3": float(near["oi"].sum())}
    return {
        "as_of": str(asof), "expiry": str(exp), "spot": S, "n_options_used": int(len(band)),
        "h_v1_volpts": p.h * 100, "h_chain_median_volpts": h_chain * 100,
        "h_chain_put_wing_median_volpts": float(puts["h"].median()) * 100,
        "h_chain_call_wing_median_volpts": float(calls["h"].median()) * 100,
        "h_chain_p25_p75_volpts": [float(band["h"].quantile(.25)) * 100, float(band["h"].quantile(.75)) * 100],
        "svi_params_a_b_rho_m_s": sp.tolist(), "svi_rmse_volpts": float(np.sqrt(np.mean((iv_svi - fit["iv"]) ** 2)) * 100),
        "frozen_surface_rmse_volpts": float(np.sqrt(np.mean((iv_frz - fit["iv"]) ** 2)) * 100),
        "frozen_surface_bias_volpts": float(np.mean(iv_frz - fit["iv"]) * 100),
        "capacity_fund_contracts_per_leg_latest_n_port": contracts, "capacity_nport_period": str(last["period"]),
        "capacity_chain_open_interest": ois,
        "capacity_note": "one chain snapshot of a different expiry from the fund's; a rough scale check, not a capacity estimate",
    }, h_chain


def run_ladder(m, p, spec, start, end, phases=(0, 21, 42)):
    navs = {ph: run_phase(m, spec, p, start, end, ph).nav for ph in phases}
    df = pd.DataFrame(navs).ffill()
    return navs[0], ladder(df, tuple(phases))


def stress(m, p, h_grid: dict, spec, start, end, label) -> list[dict]:
    rf = rf_daily(m)
    out = []
    base = {}
    for name, h in h_grid.items():
        ph = dataclasses.replace(p, h=h)
        single, lad = run_ladder(m, ph, spec, start, end)
        for kind, nav in (("phase0", single), ("ladder_0_21_42", lad)):
            ret = nav.pct_change().dropna()
            row = {"window": label, "h_name": name, "h_volpts": h * 100, "book": kind,
                   "ann_return": annualised_return(nav), **sharpe_ci(ret, rf.reindex(ret.index), n_boot=500)}
            out.append(row)
    df = pd.DataFrame(out)
    for kind in df["book"].unique():
        a0 = df[(df["book"] == kind) & (df["h_name"] == "zero")]["ann_return"].iloc[0]
        df.loc[df["book"] == kind, "cost_drag_vs_zero_pct"] = (a0 - df.loc[df["book"] == kind, "ann_return"]) * 100
    return df.to_dict("records")


def main() -> dict:
    unlock("test")
    m, p = market(), surface()
    spec = specs()["fixed"]
    res = {"quantlib_max_abs_error": qlcheck.max_errors(400)}
    cb, h_chain = chain_block(m, p)
    res["chain"] = cb
    grid = {"zero": 0.0, "v1": p.h, "chain": h_chain, "2x_v1": 2 * p.h, "4x_v1": 4 * p.h}
    rows = stress(m, p, grid, spec, "2011-01", "2019-12", "dev+val 2011-2019")
    rows += stress(m, p, grid, spec, "2020-01", "2026-09", f"2020-2026-09 {SEEN}")
    pd.DataFrame(rows).to_csv(TABLES / "haircut_stress.csv", index=False)
    # dispersion of 63 phases at v1 h (from the H2 cache) and at 2x chain h
    cache = RUNS / "family_navs_2011_2019.parquet"
    disp = {}
    if cache.exists():
        navs = pd.read_parquet(cache)
        cols = [c for c in navs.columns if c.startswith("fixed_phase")]
        ann = navs[cols].apply(annualised_return)
        disp["v1_h"] = {"std_ann_return_pct": float(ann.std() * 100), "min_pct": float(ann.min() * 100), "max_pct": float(ann.max() * 100)}
    ph2 = dataclasses.replace(p, h=2 * p.h)
    ann2 = pd.Series({ph: annualised_return(run_phase(m, spec, ph2, "2011-01", "2019-12", ph).nav) for ph in range(63)})
    disp["2x_v1_h"] = {"std_ann_return_pct": float(ann2.std() * 100), "min_pct": float(ann2.min() * 100), "max_pct": float(ann2.max() * 100)}
    res["phase_dispersion_dev_val"] = disp
    res["n_collars_per_window_resets"] = "quarterly resets; 36 in dev+val, 27 in the seen window"
    dump("pricing_checks.json", res)
    print(res["quantlib_max_abs_error"], cb["h_v1_volpts"], cb["h_chain_median_volpts"], cb["svi_rmse_volpts"], cb["frozen_surface_rmse_volpts"], disp)
    return res


if __name__ == "__main__":
    main()
