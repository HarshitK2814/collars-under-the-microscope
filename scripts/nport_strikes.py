"""Actual fund strikes per quarter as multiples of the S&P 500 close on the prior quarter-end (the reset day).

    python scripts/nport_strikes.py --period validation
    python scripts/nport_strikes.py --period test,recent     # needs PREREG_HASH (see qcore.splits)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qcore.splits import Splits, select  # noqa: E402

from collars.config import INTERIM, RAW, RESEARCH, RESULTS, load  # noqa: E402

LEG = {("Put", "Purchased"): "K1_long_put", ("Put", "Written"): "K2_short_put", ("Call", "Written"): "Kc_short_call"}


def model_call(reset: pd.Timestamp, K1: float, K2: float, expiry: pd.Timestamp) -> dict:
    """Zero-cost (mid) call strike from the frozen Tier-B surface at the reset-day close, given the fund's put strikes."""
    import yaml
    from collars.data.load import load as load_market
    from collars.engine import Quote, zero_cost_call
    from collars.surface import SurfaceParams, vol_matrix, vs_vol
    from collars.config import ROOT
    m = load_market()
    p = SurfaceParams.from_dict(yaml.safe_load((ROOT / "configs" / "surface.yaml").read_text()))
    i = m.index.get_loc(reset)
    S, r, q = m["spx"].iloc[i], m["r"].iloc[i], m["q"].iloc[i]
    tau = (expiry - reset).days / 365
    F = S * np.exp((r - q) * tau)
    qt = Quote(S, F, tau, r, q, vs_vol(vol_matrix(m)[i], tau), p)
    Kc = zero_cost_call(qt, float(qt.mid("put", K1) - qt.mid("put", K2)))
    return {"model_Kc": Kc, "model_cap": Kc / S - 1, "vix3m_reset": m["vix3m"].iloc[i]}


def table(periods: list[str]) -> pd.DataFrame:
    splits = Splits.from_dict(load("splits"))
    legs = pd.read_parquet(INTERIM / "nport_options.parquet")
    legs = pd.concat([select(legs, splits, p, RESEARCH / "preregistration.md") for p in periods])
    spx = pd.read_csv(RAW / "yahoo_GSPC.csv", index_col=0, parse_dates=True)["Close"]
    out = []
    for period, g in legs.groupby(level=0):
        # reset day = last trading day of the previous calendar quarter (the 497K hedge-period rule)
        reset = spx.loc[: (period - pd.offsets.QuarterEnd(1))].index[-1]
        row = {"period": period.date(), "reset_day": reset.date(), "spx_reset": spx[reset],
               "expiry": g["expiry"].iloc[0].date(), "contracts": g["contracts"].abs().iloc[0]}
        for _, leg in g.iterrows():
            name = LEG[(leg["put_call"], leg["written_or_purchased"])]
            row[name] = leg["strike"]
            row[name.split("_")[0] + "_mny"] = leg["strike"] / spx[reset]
        row["cap"] = row["Kc_mny"] - 1
        row.update(model_call(reset, row["K1_long_put"], row["K2_short_put"], pd.Timestamp(row["expiry"])))
        row["notional_over_assets"] = row["contracts"] * 100 * spx[reset] / g["tot_assets"].iloc[0]
        out.append(row)
    return pd.DataFrame(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", default="validation")
    periods = ap.parse_args().period.split(",")
    t = table(periods)
    t.to_csv(RESULTS / "tables" / f"nport_strikes_{'_'.join(periods)}.csv", index=False)
    with pd.option_context("display.width", 200, "display.max_columns", 20, "display.precision", 4):
        print(t)
