"""Forward tracking helpers. A collar position opened on the last reset expires after the data end, so the market
panel is extended with flat placeholder business days. The engine reads row i only for marks on date i and for rolls
at the roll date, so NAV on every real date is unchanged by the placeholders (tested)."""

from __future__ import annotations

import pandas as pd


def extend_market(m: pd.DataFrame, until: str = "2027-12-31") -> pd.DataFrame:
    m = m.dropna(subset=["spx"]).copy()
    fill = [c for c in ("r", "q", "vix9d", "vix", "vix3m", "vix6m", "vix1y") if c in m]
    m[fill] = m[fill].ffill()          # a vol index published a day late is carried forward (stale mark, stated)
    new = pd.bdate_range(m.index[-1] + pd.Timedelta(days=1), until)
    ext = pd.DataFrame({c: m[c].iloc[-1] for c in m.columns}, index=new)
    if "div" in ext:
        ext["div"] = 0.0
    out = pd.concat([m, ext])
    out.index.name = m.index.name
    return out
