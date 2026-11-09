"""H1: VIX3M vs GJR-GARCH(1,1,1)-t forecast of the next-63-day realised variance of the S&P 500.
Forecast origin = close t (data up to and including t); label = mean of squared log returns over t+1..t+63."""

from __future__ import annotations

import numpy as np
import pandas as pd

H = 63


def realised_forward(r: pd.Series, h: int = H) -> pd.Series:
    """mean(r^2) over t+1..t+h, indexed at t (NaN if the window is incomplete)."""
    r2 = r.pow(2)
    return r2[::-1].rolling(h).mean()[::-1].shift(-1)


def garch_forward_variance(r: pd.Series, h: int = H, refit_every: int = 63, min_obs: int = 750) -> pd.Series:
    """Mean over steps 1..h of the GJR-GARCH(1,1,1)-t conditional-variance forecast made at close t (daily variance).
    Parameters are fitted on data strictly before each refit block (expanding), then held fixed over the block."""
    from arch import arch_model

    y = r.dropna() * 100
    n = len(y)
    out = pd.Series(np.nan, index=y.index, dtype=float)
    for start in range(min_obs, n, refit_every):
        end = min(start + refit_every, n)
        res = arch_model(y.iloc[:start], mean="Constant", vol="GARCH", p=1, o=1, q=1, dist="t").fit(disp="off")
        full = arch_model(y.iloc[:end], mean="Constant", vol="GARCH", p=1, o=1, q=1, dist="t").fix(res.params)
        origins = y.index[start - 1:end - 1] if end < n else y.index[start - 1:]
        f = full.forecast(horizon=h, start=origins[0], reindex=False, method="analytic")
        v = f.variance.loc[origins].mean(axis=1) / 1e4
        out.loc[origins] = v.to_numpy()
    return out.reindex(r.index)


def qlike(rv: pd.Series, f: pd.Series) -> pd.Series:
    x = rv / f
    return x - np.log(x) - 1


def fit_scale(rv: pd.Series, f: pd.Series) -> float:
    return float(rv.mean() / f.mean())
