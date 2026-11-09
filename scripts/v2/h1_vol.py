"""H1: GJR-GARCH vs VIX3M as the vol input (QLIKE on next-63-day realised S&P variance). Prereg v2 H1.
Origin = close t. Scales fitted on development labels ending <= 2016-12-31; evaluated on validation labels ending
<= 2019-12-31. Seen period (2020-01 onward labels) is descriptive only."""

from __future__ import annotations

import numpy as np
import pandas as pd

from qcore.bootstrap import bootstrap_stat, percentile_ci

from collars.v2 import volfc
from collars.v2.common import RUNS, SEEN, dump, market, unlock


def main() -> dict:
    unlock("test")  # the seen-period descriptive rows read 2020+
    m = market()
    r = np.log(m["spx"]).diff().dropna()
    cache = RUNS / "garch_fwd63.parquet"
    if cache.exists():
        g = pd.read_parquet(cache)["g"]
    else:
        g = volfc.garch_forward_variance(r)
        g.to_frame("g").to_parquet(cache)
    rv = volfc.realised_forward(r)
    label_end = pd.Series(r.index, index=r.index).shift(-volfc.H)        # date at which the 63-day window ends
    A = (m["vix3m"].reindex(r.index) / 100) ** 2 / 252
    B = (m["vix"].reindex(r.index) / 100) ** 2 / 252
    df = pd.DataFrame({"rv": rv, "A": A, "B": B, "G": g, "end": label_end}).dropna()
    dev = df[(df.index >= "2011-01-01") & (df["end"] <= "2016-12-31")]
    val = df[(df.index >= "2017-01-01") & (df["end"] <= "2019-12-31")]
    seen = df[(df.index >= "2020-01-01")]
    k = {c: volfc.fit_scale(dev["rv"], dev[c]) for c in ("A", "B", "G")}

    def evaluate(d: pd.DataFrame) -> dict:
        L = pd.DataFrame({c: volfc.qlike(d["rv"], d[c] * k[c]) for c in ("A", "B", "G")})
        out = {"n_origins": int(len(d)), "mean_qlike": {c: float(L[c].mean()) for c in L}}
        for name, other in (("vix3m_minus_garch", "A"), ("vix_minus_garch", "B")):
            diff = (L[other] - L["G"]).reset_index(drop=True)
            draws = bootstrap_stat(diff, lambda s: float(s.mean()), n_boot=2000, mean_block=63, seed=0)
            lo, hi = percentile_ci(draws)
            out[name] = {"mean": float(diff.mean()), "lo": lo, "hi": hi}
        rmse = {c: float(np.sqrt(((np.sqrt(d[c] * k[c] * 252) - np.sqrt(d["rv"] * 252)) ** 2).mean())) for c in ("A", "B", "G")}
        out["vol_rmse_annualised"] = rmse
        return out

    res = {"origin": "close t", "label": "mean r^2 over t+1..t+63", "scales_fit_on_dev": k,
           "n_dev": int(len(dev)),
           "validation": evaluate(val), "validation_period": "2017-01..2019-12 (label end <= 2019-12-31)",
           "seen_period": evaluate(seen), "seen_label": SEEN}
    res["H1_supported"] = bool(res["validation"]["vix3m_minus_garch"]["lo"] > 0)
    dump("h1_vol.json", res)
    print(res["validation"], res["H1_supported"])
    return res


if __name__ == "__main__":
    main()
