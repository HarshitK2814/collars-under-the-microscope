"""D4: adaptive conformal intervals on the pricer's call-cap error vs disclosed N-PORT strikes (all seen period).
Pricer: frozen VIX-based surface, zero-cost call strike at MID given the fund's own put strikes (model_cap).
Interval for the disclosed cap at quarter t uses errors through t-1 only (qcore.aci_intervals)."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import beta

from qcore.conformal import aci_intervals

from collars.v2.common import ROOT, SEEN, dump

T = ROOT / "results" / "tables"


def clopper(k: int, n: int, a: float = 0.05) -> list[float]:
    lo = 0.0 if k == 0 else beta.ppf(a / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - a / 2, k + 1, n - k)
    return [float(lo), float(hi)]


def series() -> dict[str, pd.DataFrame]:
    a = pd.concat([pd.read_csv(T / f"nport_strikes_{s}.csv") for s in ("development_validation", "test", "recent")])
    a = a.assign(fund="HE1")[["fund", "period", "cap", "model_cap"]]
    b = pd.read_csv(T / "posthoc_sister_fund_strikes.csv")
    b = b[b["fund"] != "HE1"][["fund", "period", "cap", "model_cap"]]
    allf = pd.concat([a, b])
    allf["period"] = pd.to_datetime(allf["period"])
    return {f: g.sort_values("period").reset_index(drop=True) for f, g in allf.groupby("fund")}


def main() -> dict:
    out = {"label": SEEN, "alpha": 0.1, "gamma": 0.02, "window": 8, "funds": {}}
    cov_all, n_all = 0, 0
    for f, g in series().items():
        y = pd.Series(g["cap"].to_numpy(), index=g["period"])
        yhat = pd.Series(g["model_cap"].to_numpy(), index=g["period"])
        err = (yhat - y)
        ci = aci_intervals(y, yhat, alpha=0.1, gamma=0.02, window=8)
        ok = ci["covered"].dropna()
        k, n = int(ok.sum()), int(len(ok))
        cov_all += k
        n_all += n
        out["funds"][f] = {"n_quarters": int(len(g)), "n_scored": n, "covered": k, "coverage": k / n,
                           "coverage_95ci": clopper(k, n),
                           "mean_error_pp": float(err.mean() * 100), "mae_pp": float(err.abs().mean() * 100),
                           "mean_interval_width_pp": float((ci["hi"] - ci["lo"]).mean() * 100)}
    out["pooled"] = {"n_scored": n_all, "covered": cov_all, "coverage": cov_all / n_all,
                     "coverage_95ci": clopper(cov_all, n_all)}
    out["note"] = ("Small samples (about 20 scored quarters per fund, serially dependent): the CI is exact-binomial and "
                   "optimistic. Disclosed option values at period ends are expiry-day intrinsic values, so strikes, not values, test the pricer.")
    dump("conformal_nport.json", out)
    print(out["pooled"], {k: (v["coverage"], v["mae_pp"]) for k, v in out["funds"].items()})
    return out


if __name__ == "__main__":
    main()
