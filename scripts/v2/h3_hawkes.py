"""H3: does past-only Hawkes intensity of large S&P down-moves at the reset close predict the collar's quarterly return
relative to the beta-matched benchmark? Fixed 95/80 strikes, 63 phases, resets 2011-01..2019-12. Prereg v2 H3."""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from collars.strategy import beta_matched, run_phase
from collars.v2 import hawkes_panel as hp
from collars.v2.common import RUNS, TABLES, dump, market, specs, surface


def panel() -> pd.DataFrame:
    cache = RUNS / "h3_quarter_panel.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    m, p, spec = market(), surface(), specs()["fixed"]
    rows = []
    for ph in range(63):
        res = run_phase(m, spec, p, "2011-01", "2019-12", ph)
        bm = beta_matched(m, res.rolls, res.nav.index)
        for d0, row in res.rolls.iterrows():
            d1 = row["expiry"]
            if d0 >= pd.Timestamp("2011-01-01") and d1 <= pd.Timestamp("2019-12-31") and d0 in res.nav.index and d1 in res.nav.index:
                rows.append({"phase": ph, "d0": d0, "d1": d1,
                             "collar": res.nav[d1] / res.nav[d0] - 1, "bm": bm[d1] / bm[d0] - 1})
    df = pd.DataFrame(rows)
    df["y"] = df["collar"] - df["bm"]
    df.to_parquet(cache)
    return df


def nw(y: pd.Series, X: pd.DataFrame, lags: int = 63) -> dict:
    r = sm.OLS(y, sm.add_constant(X)).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return {"coef": r.params.to_dict(), "t": r.tvalues.to_dict(), "n": int(r.nobs), "r2": float(r.rsquared)}


def main() -> dict:
    m = market()
    r = np.log(m["spx"]).diff().dropna()
    df = panel()
    out = {"n_pairs": int(len(df)), "n_unique_d0": int(df["d0"].nunique()),
           "mean_y_per_quarter": float(df["y"].mean()), "sd_y": float(df["y"].std())}
    rv = hp.realised_vol(r)
    for name, both in (("down_events", False), ("both_sided_events", True)):
        ev = hp.crash_events(r, both=both)
        lam = hp.intensity_at(ev, pd.DatetimeIndex(sorted(df["d0"].unique())))
        d = df.assign(lam=df["d0"].map(lam), rv=df["d0"].map(rv)).dropna(subset=["lam", "rv"])
        g = d.groupby("d0").agg(y=("y", "mean"), lam=("lam", "first"), rv=("rv", "first")).sort_index()
        out[name] = {"n_events_total": int(ev.sum()), "mean_intensity": float(g["lam"].mean()),
                     "multivariate": nw(g["y"], g[["lam", "rv"]]), "univariate": nw(g["y"], g[["lam"]])}
        g.to_csv(TABLES / f"h3_{name}_by_reset_date.csv")
    h = out["down_events"]["multivariate"]
    out["H3_supported"] = bool(h["coef"]["lam"] > 0 and h["t"]["lam"] > 2)
    out["nw_lags"] = 63
    dump("h3_hawkes.json", out)
    print(out["down_events"], out["H3_supported"])
    return out


if __name__ == "__main__":
    main()
