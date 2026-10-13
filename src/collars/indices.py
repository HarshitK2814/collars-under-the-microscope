"""Replications of Cboe strategy indices with the Tier-B surface, used to calibrate and validate the pricer.

Rules follow the Cboe methodologies (CLLZ: data/raw/cllz_methodology.pdf). Simplifications, all [Reconstruction]:
the 11:00 a.m. / VWAP strike-setting level is proxied by the day's open; the two-call CLLZ portfolio is
replaced by one call at the continuous zero-cost strike; all legs pay the same half-spread h (VWAP fills sit inside the quote, so h is an effective cost).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from collars.engine import Leg, Quote, floor_strike, run, third_fridays, zero_cost_call
from collars.surface import SurfaceParams


def cllz_rule(qt: Quote) -> list[Leg]:
    K1, K2 = floor_strike(0.975 * qt.S), floor_strike(0.95 * qt.S)
    cost = qt.fill("put", K1, +1) - qt.fill("put", K2, -1)       # ask(2.5% OTM) - bid(5% OTM)
    Kc = zero_cost_call(qt, cost, at="fill")                     # bid(call) = cost
    return [Leg("put", K1, +1), Leg("put", K2, -1), Leg("call", Kc, -1)]


def bxm_rule(qt: Quote) -> list[Leg]:
    K = np.ceil(qt.S / 5) * 5                                    # ATM call, strike just above the index
    return [Leg("call", K, -1)]


def put_rule(qt: Quote) -> list[Leg]:
    K = np.floor(qt.S / 5) * 5                                   # ATM put, strike just below the index
    return [Leg("put", K, -1)]


def pput_rule(qt: Quote) -> list[Leg]:
    return [Leg("put", floor_strike(0.95 * qt.S), +1)]


INDICES = {
    "CLLZ": (cllz_rule, "equity"),
    "BXM": (bxm_rule, "equity"),
    "PUT": (put_rule, "cash"),
    "PPUT": (pput_rule, "equity"),
}


def replicate(market: pd.DataFrame, name: str, p: SurfaceParams, start: str, end: str) -> pd.DataFrame:
    """Model vs actual index returns between consecutive monthly roll dates."""
    rule, und = INDICES[name]
    rolls = third_fridays(market.index, start, end)
    res = run(market, rolls, rule, p, roll_at="open", underlying=und)
    model = res.nav.reindex(rolls)
    actual = market[name].reindex(rolls)
    out = pd.DataFrame({"model": model.pct_change(), "actual": actual.pct_change()}).dropna()
    return out


def tracking(market: pd.DataFrame, p: SurfaceParams, start: str, end: str,
             names: tuple[str, ...] = tuple(INDICES)) -> pd.DataFrame:
    rows = {}
    for n in names:
        d = replicate(market, n, p, start, end)
        e = d["model"] - d["actual"]
        rows[n] = {"months": len(d), "te_ann": e.std() * np.sqrt(12), "bias_ann": e.mean() * 12,
                   "corr": d["model"].corr(d["actual"]), "rmse_m": np.sqrt((e ** 2).mean())}
    return pd.DataFrame(rows).T
