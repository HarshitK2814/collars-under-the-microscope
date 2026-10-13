"""The fund-style quarterly put-spread collar, its variants, the phase family, the ladder and the beta-matched benchmark.

Baseline [Reconstruction] (see research/institutional_methodology.md):
  reset at the 16:00 close of the reset day; K1 = m1*S, K2 = m2*S rounded to the 5-point strike grid;
  Kc solved for zero net premium at MID, rounded to 5 points; all legs expire at the next reset day
  (PM-settled at the close); fills pay h vol points of half-spread on every leg at the open.
Equity sleeve: S&P 500 with dividends (= total return), notional hedge ratio 1.0.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from collars.engine import Leg, Quote, Result, calendar_resets, quarter_ends, round_strike, run, zero_cost_call
from collars.surface import SurfaceParams

TRADING_DAYS_PER_QUARTER = 63


@dataclass(frozen=True)
class CollarSpec:
    m1: float = 0.95
    m2: float = 0.80
    strikes: str = "fixed"            # "fixed" moneyness or "vol" (volatility units, RQ2)
    z1: float = np.nan                # vol-unit distances (fitted on development)
    z2: float = np.nan
    legs: tuple[str, ...] = ("long_put", "short_put", "short_call")
    hedge_ratio: float = 1.0

    def rule(self, qt: Quote) -> list[Leg]:
        if self.strikes == "fixed":
            K1, K2 = round_strike(self.m1 * qt.S), round_strike(self.m2 * qt.S)
        else:
            atm = float(qt.vol(qt.F)) * np.sqrt(qt.tau)
            K1 = round_strike(qt.F * np.exp(-self.z1 * atm))
            K2 = round_strike(qt.F * np.exp(-self.z2 * atm))
        cost = float(qt.mid("put", K1) - qt.mid("put", K2))
        Kc = round_strike(zero_cost_call(qt, cost, at="mid"))
        h = self.hedge_ratio
        all_legs = {"long_put": Leg("put", K1, +h), "short_put": Leg("put", K2, -h), "short_call": Leg("call", Kc, -h)}
        return [all_legs[k] for k in self.legs]


def reset_dates(index: pd.DatetimeIndex, start: str, end: str, phase: int) -> list[pd.Timestamp]:
    """Quarterly resets (quarter-end + phase trading days), padded one quarter each side of [start, end]
    so the evaluation window is always covered by an open position. The padding reset *after* the window
    is only a calendar date (the expiry of the last collar); no data after `end` enter the window's returns."""
    lo = (pd.Timestamp(start) - pd.offsets.QuarterEnd(2)).strftime("%Y-%m-%d")
    hi = (pd.Timestamp(end) + pd.offsets.QuarterEnd(2)).strftime("%Y-%m-%d")
    return quarter_ends(index, lo, hi, phase)


def window(nav: pd.Series, start: str, end: str) -> pd.Series:
    lo = pd.Period(start).start_time
    hi = pd.Period(end).end_time
    s = nav[(nav.index >= lo) & (nav.index <= hi)]
    prev = nav[nav.index < lo]
    if len(prev):   # anchor at the last close before the window so the first day's return counts
        s = pd.concat([prev.iloc[-1:], s])
    return s / s.iloc[0]


def run_phase(market: pd.DataFrame, spec: CollarSpec, p: SurfaceParams, start: str, end: str,
              phase: int = 0) -> Result:
    rolls = reset_dates(market.index, start, end, phase)
    res = run(market, rolls, spec.rule, p, roll_at="close", underlying="equity")
    res.nav = window(res.nav, start, end)
    return res


def run_phases(market, spec, p, start, end, phases=range(TRADING_DAYS_PER_QUARTER)) -> tuple[pd.DataFrame, dict]:
    navs, rolls = {}, {}
    for ph in phases:
        r = run_phase(market, spec, p, start, end, ph)
        navs[ph], rolls[ph] = r.nav, r.rolls
    return pd.DataFrame(navs).ffill(), rolls


def ladder(navs: pd.DataFrame, phases: tuple[int, ...]) -> pd.Series:
    """Equal-notional tranches held without cross-rebalancing: V^L = mean of the tranche NAVs."""
    return navs[list(phases)].mean(axis=1)


def ladders(navs: pd.DataFrame, n_tranches: int = 3, step: int = 21) -> pd.DataFrame:
    """All distinct ladders (phases phi, phi+step, ...) for phi = 0..step-1."""
    return pd.DataFrame({phi: ladder(navs, tuple(phi + k * step for k in range(n_tranches)))
                         for phi in range(step)})


def beta_matched(market: pd.DataFrame, rolls: pd.DataFrame, nav_index: pd.DatetimeIndex) -> pd.Series:
    """beta_ex (the collar's delta per unit NAV at each reset, known at the reset close) in S&P 500 TR,
    the rest in T-bills, rebalanced at each reset. Returns a NAV on nav_index (normalised to 1)."""
    tr = market["spxtr"].pct_change()
    bill = (market["r"].shift() * market.index.to_series().diff().dt.days / 365).fillna(0.0)
    beta = rolls["delta"].reindex(market.index).ffill().shift()   # the reset-close beta applies from the next day
    ret = (beta * tr + (1 - beta) * bill).reindex(nav_index).fillna(0.0)
    ret.iloc[0] = 0.0
    return (1 + ret).cumprod()


def daily_returns(nav: pd.Series) -> pd.Series:
    return nav.pct_change().dropna()


def annualised_return(nav: pd.Series) -> float:
    years = (nav.index[-1] - nav.index[0]).days / 365.25
    return float((nav.iloc[-1] / nav.iloc[0]) ** (1 / years) - 1)


def run_calendar(market: pd.DataFrame, spec: CollarSpec, p: SurfaceParams, start: str, end: str,
                 offset_months: int) -> Result:
    """The collar on a month-end calendar offset from quarter-ends (the fund family's Fund 2 / Fund 3 calendars)."""
    lo = (pd.Timestamp(start) - pd.offsets.MonthEnd(6)).strftime("%Y-%m")
    hi = (pd.Timestamp(end) + pd.offsets.MonthEnd(6)).strftime("%Y-%m")
    rolls = calendar_resets(market.index, lo, hi, offset_months)
    res = run(market, rolls, spec.rule, p, roll_at="close", underlying="equity")
    res.nav = window(res.nav, start, end)
    return res
