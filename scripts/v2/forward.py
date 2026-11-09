"""P2 v2 forward paper tracker. Books: phase0_collar (fixed 95/80 quarterly collar, resets on quarter-end closes),
ladder_0_21_42 (equal-notional 3 tranches), jheqx_fund (Yahoo adjusted close, total return). Daily returns from the
forward start in configs/splits_v2.yaml (2026-11), written through qcore.splits.select (locked by the v2 prereg hash).
Signal/strike bar: reset-day close, held to the next reset; v1 half-spread paid on every leg; no commissions or impact.
Usage: python scripts/v2/forward.py [--refresh]   (re-downloads Cboe/FRED/Yahoo and rebuilds the market panel first).
Idempotent: only new (date, book) rows are appended."""

from __future__ import annotations

import sys

import pandas as pd

from qcore.splits import file_hash, select

from collars.config import RAW
from collars.strategy import ladder, run_phase
from collars.v2.common import PREREG, ROOT, market, specs, splits, surface
from collars.v2.forward import extend_market
from collars.v2.forward_log import append_new

OUT = ROOT / "results" / "v2" / "forward" / "forward.csv"


def refresh() -> None:
    import yfinance as yf

    from collars.data import download
    from collars.data.load import build
    download.download_cboe(), download.download_fred(), download.download_yahoo()
    d = yf.download("JHEQX", start="2020-12-01", auto_adjust=True, progress=False)
    if isinstance(d.columns, pd.MultiIndex):
        d.columns = d.columns.get_level_values(0)
    d.to_csv(RAW / "yahoo_JHEQX.csv")
    build()


def main(do_refresh: bool = False) -> int:
    if do_refresh:
        refresh()
    m, p, spec = market(), surface(), specs()["fixed"]
    sp = splits()
    mx = extend_market(m)
    lo = "2025-01"
    hi = mx.index[-1].strftime("%Y-%m")
    navs = {ph: run_phase(mx, spec, p, lo, hi, ph).nav for ph in (0, 21, 42)}
    nav_df = pd.DataFrame(navs).ffill()
    books = {"phase0_collar": navs[0], "ladder_0_21_42": ladder(nav_df, (0, 21, 42))}
    ret = {k: v[v.index <= m.index[-1]].pct_change().dropna() for k, v in books.items()}
    fund = pd.read_csv(RAW / "yahoo_JHEQX.csv", index_col=0, parse_dates=True)["Close"].pct_change().dropna()
    ret["jheqx_fund"] = fund
    h = file_hash(PREREG)
    rows = []
    for name, r in ret.items():
        f = select(r, sp, "forward", PREREG)
        rows.append(pd.DataFrame({"date": f.index, "book": name, "net_return": f.to_numpy(), "prereg_hash": h}))
    n_new = append_new(OUT, pd.concat(rows, ignore_index=True))
    days = pd.read_csv(OUT, parse_dates=["date"])["date"].nunique()
    print(f"data ends {m.index[-1].date()}; forward start {sp.forward[0]}; new rows {n_new}; forward days tracked: {days}")
    return days


if __name__ == "__main__":
    main("--refresh" in sys.argv)
