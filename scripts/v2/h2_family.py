"""H2: PBO (CSCV, 16 blocks) and deflated Sharpe over the 168-member collar family, 2011-01..2019-12 (dev+val).
Daily net returns (v1 half-spread paid on every leg at every reset), excess of the T-bill. Signal bar: reset-day close."""

from __future__ import annotations

import numpy as np
import pandas as pd

from qcore.validation import deflated_sharpe, expected_max_sharpe, pbo_cscv

from collars.v2.common import RUNS, TABLES, dump, market, rf_daily, sharpe_ci, specs, surface
from collars.v2.family import family_navs, family_returns

START, END = "2011-01", "2019-12"


def main() -> dict:
    m, p = market(), surface()
    cache = RUNS / "family_navs_2011_2019.parquet"
    if cache.exists():
        navs = pd.read_parquet(cache)
    else:
        navs, _ = family_navs(m, p, specs(), START, END)
        navs.to_parquet(cache)
    R = family_returns(navs)
    rf = rf_daily(m).reindex(R.index)
    X = R.sub(rf, axis=0)
    sr_d = X.mean() / X.std(ddof=1)                      # per-day Sharpe of each member
    sr_var = float(sr_d.var(ddof=1))
    pb = pbo_cscv(X, n_blocks=16)
    best = sr_d.idxmax()
    dsr = deflated_sharpe(X[best], n_trials=X.shape[1], sr_var=sr_var)
    ann = lambda s: s * np.sqrt(252)
    ci = sharpe_ci(R[best], rf)
    base = "fixed_phase0"
    tab = pd.DataFrame({"sharpe": ann(sr_d), "ann_return": (1 + R).prod() ** (252 / len(R)) - 1})
    tab.sort_values("sharpe", ascending=False).to_csv(TABLES / "h2_family_sharpe.csv")
    res = {
        "window": f"{START}..{END} (development + validation)", "n_members": int(X.shape[1]), "n_days": int(len(X)),
        "n_resets_per_member": 36, "pbo": pb["pbo"], "n_combinations": pb["n_combinations"],
        "best_member": best, "best_sharpe_ci": ci, "expected_max_sharpe_noise_annual": ann(expected_max_sharpe(X.shape[1], sr_var)),
        "dsr_best": dsr, "family_sharpe_median": float(ann(sr_d).median()),
        "family_sharpe_min": float(ann(sr_d).min()), "family_sharpe_max": float(ann(sr_d).max()),
        "v1_baseline_phase0_sharpe": float(ann(sr_d[base])), "v1_baseline_rank": int((sr_d > sr_d[base]).sum() + 1),
        "cost_note": "v1 half-spread h on every leg at each reset; no commissions, no impact; capacity not modelled here",
    }
    res["H2_supported"] = bool(res["pbo"] > 0.5 and dsr < 0.90)
    np.save(RUNS / "h2_logits.npy", pb["logits"])
    dump("h2_family.json", res)
    print({k: v for k, v in res.items() if k != "best_sharpe_ci"}, ci)
    return res


if __name__ == "__main__":
    main()
