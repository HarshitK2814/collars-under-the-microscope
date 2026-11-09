"""H3: past-only Hawkes intensity of large S&P moves at each reset close."""

from __future__ import annotations

import numpy as np
import pandas as pd

from qcore.hawkes import fit_hawkes_exp, hawkes_intensity


def crash_events(r: pd.Series, k: float = 2.5, com: float = 60, both: bool = False) -> pd.Series:
    """True on day t if r_t < -k * sigma_{t-1} (EWMA of r^2 through t-1; both=True uses |r_t|). Known at close t."""
    sig = np.sqrt(r.pow(2).ewm(com=com, min_periods=250).mean().shift(1))
    x = r.abs() if both else -r
    return (x > k * sig).fillna(False)


def intensity_at(ev: pd.Series, dates: pd.DatetimeIndex, min_events: int = 20) -> pd.Series:
    """Intensity at each date using events strictly before it; parameters refit each January on events before it.
    Times are integer trading-day positions of the full series."""
    idx = ev.index
    pos = pd.Series(np.arange(len(idx)), index=idx)
    mask = ev.to_numpy(dtype=bool)
    t_ev = pos.to_numpy(dtype=float)[mask]
    d_ev = idx[mask]
    out = pd.Series(np.nan, index=pd.DatetimeIndex(dates))
    fits: dict[int, dict | None] = {}
    for d in out.index:
        y = d.year
        if y not in fits:
            cut = pd.Timestamp(year=y, month=1, day=1)
            tt = t_ev[d_ev < cut]
            if len(tt) >= min_events:
                T = float((idx < cut).sum())
                fits[y] = fit_hawkes_exp(tt, T)
            else:
                fits[y] = None
        p = fits[y]
        if p is None:
            continue
        out[d] = hawkes_intensity(t_ev[d_ev < d], p, np.array([float(pos[d])]))[0]
    return out


def realised_vol(r: pd.Series, n: int = 63) -> pd.Series:
    return r.rolling(n).std() * np.sqrt(252)
