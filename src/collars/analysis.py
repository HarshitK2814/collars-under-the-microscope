"""Statistics for RQ1-RQ3 on one evaluation window. Pure functions of NAV panels; no data loading.

RQ1  timing luck: sd across the 63 phases of annualised return (TL), vs sd across the 21 three-tranche ladders.
     H1 statistic: ratio = TL_single / TL_ladder, with a joint stationary-bootstrap CI (all phases resampled on
     the same days, mean block = one quarter).
RQ2  hedge-effectiveness stability: HE_g = 1 - var(collar daily) / var(S&P TR daily) within VIX regime g
     (VIX tercile at the most recent reset, expanding window since 1990). Stability = max_g HE - min_g HE.
RQ3  collar vs beta-matched S&P/T-bill benchmark: return forgone, CVaR95 (monthly) reduction, Sharpe difference.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from qcore.bootstrap import percentile_ci, stationary_indices

PERIODS_PER_YEAR = 252


def ann_return_from_rets(r: np.ndarray, years: float) -> np.ndarray:
    return np.prod(1 + r, axis=0) ** (1 / years) - 1


def years_of(idx: pd.DatetimeIndex) -> float:
    return (idx[-1] - idx[0]).days / 365.25


def monthly(nav: pd.Series) -> pd.Series:
    return nav.resample("ME").last().pct_change().dropna()


def cvar(r: pd.Series, level: float = 0.95) -> float:
    """Expected shortfall as a positive loss number."""
    q = r.quantile(1 - level)
    return float(-r[r <= q].mean())


def max_dd(nav: pd.Series) -> float:
    return float((nav / nav.cummax() - 1).min())


def metrics(nav: pd.Series, rf_daily: pd.Series) -> dict:
    r = nav.pct_change().dropna()
    ex = r - rf_daily.reindex(r.index).fillna(0)
    m = monthly(nav)
    return {"ann_return": (nav.iloc[-1] / nav.iloc[0]) ** (1 / years_of(nav.index)) - 1,
            "ann_vol": r.std() * np.sqrt(PERIODS_PER_YEAR),
            "sharpe": ex.mean() / ex.std() * np.sqrt(PERIODS_PER_YEAR),
            "max_dd": max_dd(nav), "cvar95_m": cvar(m), "worst_month": m.min(), "months": len(m),
            "days": len(r)}


def sharpe_ci(nav: pd.Series, rf_daily: pd.Series, n_boot: int = 2000, seed: int = 0) -> tuple[float, float]:
    r = nav.pct_change().dropna()
    ex = (r - rf_daily.reindex(r.index).fillna(0)).to_numpy()
    rng = np.random.default_rng(seed)
    draws = np.empty(n_boot)
    for b in range(n_boot):
        s = ex[stationary_indices(len(ex), 63, rng)]
        draws[b] = s.mean() / s.std() * np.sqrt(PERIODS_PER_YEAR)
    return percentile_ci(draws)


def phase_table(navs: pd.DataFrame, rf_daily: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({ph: metrics(navs[ph], rf_daily) for ph in navs.columns}).T


def dispersion(table: pd.DataFrame) -> dict:
    ar = table["ann_return"]
    return {"sd": ar.std(ddof=1), "range": ar.max() - ar.min(), "iqr": ar.quantile(0.75) - ar.quantile(0.25),
            "min": ar.min(), "max": ar.max(), "mean": ar.mean(),
            "maxdd_sd": table["max_dd"].std(ddof=1), "maxdd_range": table["max_dd"].max() - table["max_dd"].min()}


def h1_bootstrap(navs: pd.DataFrame, n_tranches: int = 3, step: int = 21, n_boot: int = 2000,
                 mean_block: float = 63, seed: int = 0) -> dict:
    """Joint stationary bootstrap of the daily returns of all phases; rebuild single and ladder NAVs per draw."""
    R = navs.pct_change().dropna().to_numpy()            # days x 63
    years = years_of(navs.index)
    rng = np.random.default_rng(seed)
    lad_cols = [[phi + k * step for k in range(n_tranches)] for phi in range(step)]
    ratios, sd_s, sd_l, d0 = (np.empty(n_boot) for _ in range(4))
    for b in range(n_boot):
        s = R[stationary_indices(len(R), mean_block, rng)]
        final = np.prod(1 + s, axis=0)                   # final NAV per phase
        single = final ** (1 / years) - 1
        lad_final = np.array([final[c].mean() for c in lad_cols])
        ladder = lad_final ** (1 / years) - 1
        sd_s[b], sd_l[b] = single.std(ddof=1), ladder.std(ddof=1)
        ratios[b] = sd_s[b] / sd_l[b]
        d0[b] = ladder[0] - single[0]                    # ladder(0,21,42) minus the fund's phase 0
    final = navs.iloc[-1].to_numpy() / navs.iloc[0].to_numpy()
    single = final ** (1 / years) - 1
    ladder = np.array([final[c].mean() for c in lad_cols]) ** (1 / years) - 1
    return {"sd_single": single.std(ddof=1), "sd_ladder": ladder.std(ddof=1),
            "ratio": single.std(ddof=1) / ladder.std(ddof=1), "ratio_ci": percentile_ci(ratios),
            "ratio_boot_p_below_2": float((ratios < 2).mean()),
            "ladder0_minus_phase0": ladder[0] - single[0], "ladder0_minus_phase0_ci": percentile_ci(d0),
            "ladder0_minus_phase0_p": float(2 * min((d0 < 0).mean(), (d0 > 0).mean())),
            "n_boot": n_boot, "mean_block_days": mean_block}


def vix_regime(market: pd.DataFrame, reset_dates: pd.DatetimeIndex) -> pd.Series:
    """Tercile (0 low, 1 mid, 2 high) of VIX at each reset vs its own history up to that day (expanding)."""
    vix = market["vix"].dropna()
    out = {}
    for d in reset_dates:
        hist = vix.loc[:d]
        pct = (hist < hist.iloc[-1]).mean()
        out[d] = int(min(pct * 3, 2.999))
    return pd.Series(out, name="regime")


def hedge_effectiveness(nav: pd.Series, market: pd.DataFrame, regimes: pd.Series) -> pd.Series:
    r = nav.pct_change().dropna()
    tr = market["spxtr"].pct_change().reindex(r.index)
    reg = regimes.reindex(market.index).ffill().shift().reindex(r.index)
    out = {}
    for g in (0, 1, 2):
        m = reg == g
        out[g] = 1 - r[m].var() / tr[m].var() if m.sum() > 20 else np.nan
    return pd.Series(out)


def beta_matched_comparison(nav: pd.Series, bench: pd.Series, rf_daily: pd.Series, n_boot: int = 2000,
                            seed: int = 0) -> dict:
    """Collar minus beta-matched benchmark, with joint-bootstrap CIs (mean block one quarter)."""
    r = pd.concat([nav.pct_change(), bench.pct_change()], axis=1, keys=["c", "b"]).dropna()
    rf = rf_daily.reindex(r.index).fillna(0).to_numpy()
    X = r.to_numpy()
    years = years_of(nav.index)

    def stats(x, rfx):
        ar = np.prod(1 + x, axis=0) ** (1 / years) - 1
        ex = x - rfx[:, None]
        sh = ex.mean(0) / ex.std(0) * np.sqrt(PERIODS_PER_YEAR)
        return ar, sh

    ar, sh = stats(X, rf)
    rng = np.random.default_rng(seed)
    d_ar, d_sh = np.empty(n_boot), np.empty(n_boot)
    for b in range(n_boot):
        ii = stationary_indices(len(X), 63, rng)
        a, s = stats(X[ii], rf[ii])
        d_ar[b], d_sh[b] = a[0] - a[1], s[0] - s[1]
    mc, mb = monthly(nav), monthly(bench)
    return {"collar_ann": ar[0], "bench_ann": ar[1], "return_forgone": ar[1] - ar[0],
            "return_diff_ci": percentile_ci(d_ar),
            "sharpe_collar": sh[0], "sharpe_bench": sh[1], "sharpe_diff": sh[0] - sh[1],
            "sharpe_diff_ci": percentile_ci(d_sh), "sharpe_diff_p": float(2 * min((d_sh < 0).mean(), (d_sh > 0).mean())),
            "cvar95_collar": cvar(mc), "cvar95_bench": cvar(mb), "cvar95_reduction": cvar(mb) - cvar(mc),
            "maxdd_collar": max_dd(nav), "maxdd_bench": max_dd(bench)}
