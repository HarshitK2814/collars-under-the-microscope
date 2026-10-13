"""POST-HOC (after the locked test was opened): the fund family's own ladder.

JPMorgan Hedged Equity 2 and 3 run the same collar on hedge periods offset by one and two months (497K), i.e. the
industry's implementation of our phase-0 / 21 / 42 ladder. For each fund and N-PORT snapshot:
  * strikes as multiples of the S&P 500 close on that collar's reset day (last trading day of the month three
    months before expiry), and the frozen model's zero-cost call for the fund's put strikes;
  * NAV total returns (Yahoo, adjusted), and our phase-0 / 21 / 42 collars over the same window.

    python scripts/sister_funds.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from collars import analysis as A  # noqa: E402
from collars.config import INTERIM, RAW, RESULTS, ROOT  # noqa: E402
from collars.data.load import load as load_market  # noqa: E402
from collars.engine import Quote, zero_cost_call  # noqa: E402
from collars.strategy import CollarSpec, run_calendar  # noqa: E402
from collars.surface import SurfaceParams, vol_matrix, vs_vol  # noqa: E402

LEG = {("Put", "Purchased"): "K1", ("Put", "Written"): "K2", ("Call", "Written"): "Kc"}


def strikes(fund: str, m: pd.DataFrame, p: SurfaceParams) -> pd.DataFrame:
    f = INTERIM / ("nport_options.parquet" if fund == "HE1" else f"nport_options_{fund}.parquet")
    legs = pd.read_parquet(f)
    V = vol_matrix(m)
    rows = []
    for period, g in legs.groupby(level=0):
        expiry = g["expiry"].iloc[0]
        reset_month = (expiry.to_period("M") - 3)
        reset = m.index[m.index.to_period("M") == reset_month][-1]
        S, i = m.loc[reset, "spx"], m.index.get_loc(reset)
        row = {"fund": fund, "period": period.date(), "reset_day": reset.date(), "expiry": expiry.date(), "spx_reset": S}
        for _, l in g.iterrows():
            row[LEG[(l["put_call"], l["written_or_purchased"])]] = l["strike"]
        tau = (expiry - reset).days / 365
        r, q = m["r"].iloc[i], m["q"].iloc[i]
        F = S * np.exp((r - q) * tau)
        qt = Quote(S, F, tau, r, q, vs_vol(V[i], tau), p)
        kc = zero_cost_call(qt, float(qt.mid("put", row["K1"]) - qt.mid("put", row["K2"])))
        row.update({"K1_mny": row["K1"] / S, "K2_mny": row["K2"] / S, "cap": row["Kc"] / S - 1, "model_cap": kc / S - 1})
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    m = load_market()
    p = SurfaceParams.from_dict(yaml.safe_load((ROOT / "configs" / "surface.yaml").read_text()))
    tab = pd.concat([strikes(f, m, p) for f in ("HE1", "HE2", "HE3")])
    tab.to_csv(RESULTS / "tables" / "posthoc_sister_fund_strikes.csv", index=False)
    e = tab["model_cap"] - tab["cap"]
    print(tab.groupby("fund").agg(n=("cap", "size"), K1=("K1_mny", "mean"), K2=("K2_mny", "mean"),
                                  cap=("cap", "mean"), model_cap=("model_cap", "mean")).round(4))
    print("model cap MAE by fund:", e.abs().groupby(tab["fund"]).mean().round(4).to_dict(), "corr", round(tab.cap.corr(tab.model_cap), 3))

    # NAVs: common window from the sister funds' first full month
    import yfinance as yf
    navs = {}
    for f, tk in {"HE1": "JHEQX", "HE2": "JHDRX", "HE3": "JHTRX"}.items():
        d = yf.download(tk, start="2020-12-01", auto_adjust=True, progress=False)
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)
        d.to_csv(RAW / f"yahoo_{tk}.csv")
        navs[f] = d["Close"]
    nav = pd.DataFrame(navs).dropna()
    start = nav.index[0] + pd.offsets.MonthBegin(1)
    lo, hi = start.strftime("%Y-%m"), m.index[-1].strftime("%Y-%m")
    nav = nav.loc[start:]
    nav = nav / nav.iloc[0]
    # our collar on each fund's exact 497K calendar (month-end offsets 0 / 1 / 2)
    model = {f: run_calendar(m, CollarSpec(), p, lo, hi, k).nav for f, k in (("HE1", 0), ("HE2", 1), ("HE3", 2))}
    model = pd.DataFrame(model).reindex(nav.index).ffill()
    model = model / model.iloc[0]
    rf = (m["r"].shift() * m.index.to_series().diff().dt.days / 365).fillna(0)
    out = {}
    for f in nav:
        out[f"{f}_fund_NAV"] = A.metrics(nav[f], rf)
        out[f"{f}_model"] = A.metrics(model[f], rf)
    ladder_fund = nav.mean(axis=1)
    out["ladder_of_3_funds"] = A.metrics(ladder_fund, rf)
    out["ladder_model"] = A.metrics(model.mean(axis=1), rf)
    res = pd.DataFrame(out).T
    ann = res["ann_return"]
    res.to_csv(RESULTS / "tables" / "posthoc_sister_fund_navs.csv")
    corr = {f: round(A.monthly(nav[f]).corr(A.monthly(model[f])), 3) for f in nav}
    print(f"window {nav.index[0].date()} .. {nav.index[-1].date()}")
    print(res[["ann_return", "ann_vol", "sharpe", "max_dd", "cvar95_m"]].round(4))
    print("fund NAV spread across the three calendars:", round(ann[[f'{f}_fund_NAV' for f in nav]].max() - ann[[f'{f}_fund_NAV' for f in nav]].min(), 4))
    print("model spread across the three calendars:", round(ann[[f'{f}_model' for f in nav]].max() - ann[[f'{f}_model' for f in nav]].min(), 4))
    print("monthly corr model vs fund:", corr)
    pd.concat([nav.add_suffix("_nav"), model.add_suffix("_model")], axis=1).to_parquet(RESULTS / "runs" / "posthoc_sister_navs.parquet")


if __name__ == "__main__":
    main()
