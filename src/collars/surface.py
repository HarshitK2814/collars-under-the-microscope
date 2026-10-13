"""Tier-B implied-vol surface from free Cboe data.

    sigma(K, tau) = c * sigma_VS(tau) + a * x + b * x^2,     x = ln(K / F) / sqrt(tau)

sigma_VS(tau) is the variance-swap vol at tenor tau, interpolated linearly in total variance
(sigma^2 * tau) across VIX9D / VIX / VIX3M / VIX6M / VIX1Y closes, flat outside the quoted range.
c < 1 maps variance-swap vol to ATM-forward vol; a (< 0) is the skew and b the smile curvature per unit of
standardised moneyness. (c, a, b) and the half-spread h are fitted on the development period only
(scripts/calibrate.py) and then frozen in configs/surface.yaml.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

TENORS = np.array([9, 30, 93, 186, 365]) / 365
VOL_COLS = ["vix9d", "vix", "vix3m", "vix6m", "vix1y"]
MIN_VOL = 0.03


@dataclass(frozen=True)
class SurfaceParams:
    c: float = 0.90
    a: float = -0.10
    b: float = 0.02
    h: float = 0.005     # half-spread in vol points (0.005 = 0.5 vol pt)

    @classmethod
    def from_dict(cls, d: dict) -> "SurfaceParams":
        return cls(**{k: float(d[k]) for k in ("c", "a", "b", "h")})


def vs_vol(vols: np.ndarray, tau: float) -> float:
    """Variance-swap vol at tenor tau from one day's row of VIX-family vols (NaN tenors skipped)."""
    ok = ~np.isnan(vols)
    T, v = TENORS[ok], vols[ok]
    if tau <= T[0]:
        return float(v[0])
    if tau >= T[-1]:
        return float(v[-1])
    return float(np.sqrt(np.interp(tau, T, v * v * T) / tau))


def implied_vol(K, F: float, tau: float, sig_vs: float, p: SurfaceParams):
    x = np.log(np.asarray(K, dtype=float) / F) / np.sqrt(tau)
    return np.maximum(p.c * sig_vs + p.a * x + p.b * x * x, MIN_VOL)


def vol_matrix(market: pd.DataFrame) -> np.ndarray:
    return market[VOL_COLS].to_numpy(dtype=float)
