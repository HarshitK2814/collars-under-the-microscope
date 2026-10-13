"""Black-76 on the forward: prices, Greeks, and the zero-cost call strike of a put-spread collar.

Conventions: `F` forward, `K` strike, `tau` years to expiry, `r` continuously compounded rate,
`sigma` implied vol. Greeks are with respect to spot S (F = S e^{(r-q)tau}), so
delta_S = e^{-q tau} * N(d1) for a call; puts have negative delta. Vega is per 1.00 of vol.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm


def _d1d2(F, K, tau, sigma):
    sd = sigma * np.sqrt(tau)
    d1 = (np.log(F / K) + 0.5 * sd * sd) / sd
    return d1, d1 - sd


def price(F, K, tau, r, sigma, kind: str):
    """Undiscounted-forward Black-76 price, discounted at r. kind is 'call' or 'put'."""
    d1, d2 = _d1d2(F, K, tau, sigma)
    df = np.exp(-r * tau)
    if kind == "call":
        return df * (F * norm.cdf(d1) - K * norm.cdf(d2))
    if kind == "put":
        return df * (K * norm.cdf(-d2) - F * norm.cdf(-d1))
    raise ValueError(kind)


@dataclass(frozen=True)
class Greeks:
    price: float
    delta: float   # dV/dS
    gamma: float   # d2V/dS2
    vega: float    # dV/dsigma (per 1.00 vol)
    theta: float   # dV/dt per year (calendar time passing, tau shrinking)


def greeks(S, K, tau, r, q, sigma, kind: str) -> Greeks:
    F = S * np.exp((r - q) * tau)
    d1, d2 = _d1d2(F, K, tau, sigma)
    dq, dr = np.exp(-q * tau), np.exp(-r * tau)
    pdf = norm.pdf(d1)
    p = price(F, K, tau, r, sigma, kind)
    gamma = dq * pdf / (S * sigma * np.sqrt(tau))
    vega = S * dq * pdf * np.sqrt(tau)
    common = -S * dq * pdf * sigma / (2 * np.sqrt(tau))
    if kind == "call":
        delta = dq * norm.cdf(d1)
        theta = common + q * S * dq * norm.cdf(d1) - r * K * dr * norm.cdf(d2)
    else:
        delta = -dq * norm.cdf(-d1)
        theta = common - q * S * dq * norm.cdf(-d1) + r * K * dr * norm.cdf(-d2)
    return Greeks(float(p), float(delta), float(gamma), float(vega), float(theta))


VolFn = Callable[[float], float]   # strike -> implied vol for the fixed expiry


def zero_cost_call_strike(F: float, tau: float, r: float, K1: float, K2: float,
                          vol: VolFn, k_max_mult: float = 2.0) -> float:
    """Solve C(Kc) = P(K1) - P(K2) for Kc > F by Brent's method.

    Raises ValueError if the put spread is too expensive to finance with any call above F
    (never silently re-solve: the caller records that as a disclosure-inconsistent reset).
    """
    target = price(F, K1, tau, r, vol(K1), "put") - price(F, K2, tau, r, vol(K2), "put")
    f = lambda k: price(F, k, tau, r, vol(k), "call") - target
    lo, hi = F, F * k_max_mult
    if f(lo) < 0:
        raise ValueError("put spread costs more than the ATM-forward call")
    return float(brentq(f, lo, hi, xtol=1e-8 * F))
