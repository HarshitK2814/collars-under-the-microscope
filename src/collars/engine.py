"""Event-driven option-overlay backtester with daily mark-to-market.

A strategy is a list of roll dates. At each roll the expiring legs settle at intrinsic value, and a new set of
legs (from a `LegRule`) is opened and held to the next roll. The NAV follows the Cboe strategy-index formula

    1 + R_t = (U_t + DIV_t + sum_i q_i O_i,t) / (U_{t-1} + sum_i q_i O_i,t-1)

where U is one unit of the S&P 500 (dividends via DIV) or, for cash-secured indices, a T-bill account.

Bar convention (no look-ahead):
  roll_at="close": strikes, fills and marks use day t's 16:00 close and that close's VIX-family surface.
                   Expiring options settle at the close of the roll day (PM-settled, like quarterly SPX options).
  roll_at="open":  expiring options settle at day t's open (proxy for the AM Special Opening Quotation, used by the
                   monthly Cboe indices); new legs are priced at the open using the *previous* close's surface.
Marks between rolls use each day's close. Fills: buys at mid + h * vega, sells at mid - h * vega (h in vol points).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from collars import pricing
from collars.surface import SurfaceParams, implied_vol, vol_matrix, vs_vol

# ---------------------------------------------------------------------------------------------- legs


@dataclass(frozen=True)
class Leg:
    kind: str      # "call" / "put"
    K: float
    qty: float     # +1 long, -1 short (per unit of underlying)
    spread: float = 1.0   # fraction of the half-spread paid (0 = filled at mid, e.g. VWAP-based indices)


@dataclass(frozen=True)
class Quote:
    """Everything a leg rule may use at the roll bar (all known at that bar)."""
    S: float
    F: float
    tau: float
    r: float
    q: float
    sig_vs: float
    p: SurfaceParams

    def vol(self, K):
        return implied_vol(K, self.F, self.tau, self.sig_vs, self.p)

    def mid(self, kind: str, K):
        return pricing.price(self.F, K, self.tau, self.r, self.vol(K), kind)

    def vega(self, kind: str, K):
        return pricing.greeks(self.S, K, self.tau, self.r, self.q, float(self.vol(K)), kind).vega

    def fill(self, kind: str, K, qty: float, spread: float = 1.0):
        """Price paid (qty > 0) or received (qty < 0) per option, including the half-spread."""
        return float(self.mid(kind, K)) + np.sign(qty) * spread * self.p.h * self.vega(kind, K)


LegRule = Callable[[Quote], list[Leg]]


def floor_strike(x: float, step: float = 5.0) -> float:
    """First listed strike strictly below x."""
    k = np.floor(x / step) * step
    return k - step if k >= x else k


def round_strike(x: float, step: float = 5.0) -> float:
    return float(np.round(x / step) * step)


def zero_cost_call(qt: Quote, cost: float, at: str = "mid") -> float:
    """Call strike whose premium (mid, or bid if at='fill') equals `cost`; continuous strike."""
    prem = (lambda k: qt.fill("call", k, -1)) if at == "fill" else (lambda k: float(qt.mid("call", k)))
    lo, hi = qt.F * 0.98, qt.F * 1.6
    f = lambda k: prem(k) - cost
    if f(lo) < 0:
        raise ValueError("cost exceeds near-ATM call premium")
    if f(hi) > 0:
        return hi
    return float(brentq(f, lo, hi, xtol=1e-6 * qt.F))


# ---------------------------------------------------------------------------------------------- run


@dataclass
class Result:
    nav: pd.Series
    rolls: pd.DataFrame
    daily: pd.DataFrame = field(default_factory=pd.DataFrame)


def _quote(m: dict, i: int, S: float, expiry: pd.Timestamp, date: pd.Timestamp, p: SurfaceParams) -> Quote:
    tau = max((expiry - date).days, 1) / 365
    r, q = m["r"][i], m["q"][i]
    F = S * np.exp((r - q) * tau)
    return Quote(S, F, tau, r, q, vs_vol(m["vols"][i], tau), p)


def _mark(legs: list[Leg], qt: Quote) -> float:
    return float(sum(l.qty * qt.mid(l.kind, l.K) for l in legs))


def _intrinsic(legs: list[Leg], S: float) -> float:
    return float(sum(l.qty * (max(S - l.K, 0) if l.kind == "call" else max(l.K - S, 0)) for l in legs))


def run(market: pd.DataFrame, roll_dates: list[pd.Timestamp], rule: LegRule, p: SurfaceParams,
        roll_at: str = "close", underlying: str = "equity", record_daily: bool = False) -> Result:
    """Simulate the overlay from roll_dates[0] to roll_dates[-1]. Each leg set expires at the next roll date."""
    idx = market.index
    pos = {d: idx.get_loc(d) for d in roll_dates}
    m = {"S": market["spx"].to_numpy(), "O": market["spx_open"].to_numpy(), "div": market["div"].to_numpy(),
         "r": market["r"].to_numpy(), "q": market["q"].to_numpy(), "vols": vol_matrix(market)}

    nav_vals, nav_idx, roll_rows, daily_rows = [], [], [], []
    nav = 1.0
    for j in range(len(roll_dates) - 1):
        d0, d1 = roll_dates[j], roll_dates[j + 1]
        i0, i1 = pos[d0], pos[d1]
        # --- open new legs at the roll bar
        if roll_at == "close":
            S0, surf_i = m["S"][i0], i0
        else:
            S0, surf_i = m["O"][i0], i0 - 1
        qt = _quote(m, surf_i, S0, d1, d0, p)
        legs = rule(qt)
        mid0 = _mark(legs, qt)
        fill0 = float(sum(l.qty * qt.fill(l.kind, l.K, l.qty, l.spread) for l in legs))
        if underlying == "equity":
            U0 = S0
        else:  # cash-secured: T-bills equal to the (single) short put strike, premium received added
            U0 = sum(l.K for l in legs if l.kind == "put" and l.qty < 0) - fill0
        base = U0 + mid0
        nav *= base / (U0 + fill0)  # transaction-cost drag (1 when filled at mid)
        greeks = [pricing.greeks(S0, l.K, qt.tau, qt.r, qt.q, float(qt.vol(l.K)), l.kind) for l in legs]
        delta = (1.0 if underlying == "equity" else 0.0) + sum(l.qty * g.delta for l, g in zip(legs, greeks))
        roll_rows.append({
            "date": d0, "expiry": d1, "S0": S0, "F": qt.F, "tau": qt.tau, "sig_vs": qt.sig_vs,
            **{f"K{n}": l.K for n, l in enumerate(legs)}, **{f"q{n}": l.qty for n, l in enumerate(legs)},
            **{f"iv{n}": float(qt.vol(l.K)) for n, l in enumerate(legs)},
            "net_mid": mid0, "net_fill": fill0, "cost": fill0 - mid0,
            "delta": delta / (base / S0) if underlying == "equity" else delta,
            "vega": sum(l.qty * g.vega for l, g in zip(legs, greeks)) / base,
            "gamma": sum(l.qty * g.gamma for l, g in zip(legs, greeks)) * S0 * S0 / base,
        })
        if roll_at == "open":  # rest of the roll day: open -> close
            qc = _quote(m, i0, m["S"][i0], d1, d0, p)
            U_c = m["S"][i0] if underlying == "equity" else U0
            v = U_c + _mark(legs, qc)
            nav *= v / base
            base = v
            if record_daily:
                daily_rows.append((d0, m["S"][i0], v, legs, qc))
        prev_U = U0 if roll_at == "close" else (m["S"][i0] if underlying == "equity" else U0)
        nav_vals.append(nav), nav_idx.append(d0)
        for i in range(i0 + 1, i1 + 1):
            d = idx[i]
            if underlying == "equity":
                U = m["S"][i] if not (i == i1 and roll_at == "open") else m["O"][i]
                div = m["div"][i]
            else:
                U = prev_U * np.exp(m["r"][i - 1] * (d - idx[i - 1]).days / 365)
                div = 0.0
            if i == i1:  # expiry: settle at close (PM) or open (AM)
                opt = _intrinsic(legs, m["S"][i] if roll_at == "close" else m["O"][i])
            else:
                qd = _quote(m, i, m["S"][i], d1, d, p)
                opt = _mark(legs, qd)
                if record_daily:
                    daily_rows.append((d, m["S"][i], U + opt, legs, qd))
            v = U + div + opt
            nav *= v / base
            base, prev_U = U + opt, U
            if i < i1:
                nav_vals.append(nav), nav_idx.append(d)
            else:
                nav_before_roll = nav
        nav = nav_before_roll
    nav_vals.append(nav), nav_idx.append(roll_dates[-1])
    s = pd.Series(nav_vals, index=pd.DatetimeIndex(nav_idx), name="nav")
    s = s[~s.index.duplicated(keep="last")]
    return Result(s, pd.DataFrame(roll_rows).set_index("date"))


# ---------------------------------------------------------------------------------------------- calendars


def third_fridays(index: pd.DatetimeIndex, start: str, end: str) -> list[pd.Timestamp]:
    """Monthly roll dates: third Friday, or the preceding trading day if it is a holiday."""
    out = []
    for mth in pd.period_range(start, end, freq="M"):
        first = mth.start_time
        fri = first + pd.offsets.Week(weekday=4) if first.weekday() != 4 else first
        third = fri + pd.Timedelta(days=14)
        prior = index[index <= third]
        if len(prior) and prior[-1] >= third - pd.Timedelta(days=4):
            out.append(prior[-1])
    return out


def quarter_ends(index: pd.DatetimeIndex, start: str, end: str, phase: int = 0) -> list[pd.Timestamp]:
    """Last trading day of each calendar quarter, shifted forward by `phase` trading days."""
    s = pd.Series(index, index=index)
    qe = s.groupby(index.to_period("Q")).last()
    locs = [index.get_loc(d) + phase for d in qe.values]
    dates = [index[l] for l in locs if l < len(index)]
    lo, hi = pd.Period(start).start_time, pd.Period(end).end_time
    return [d for d in dates if lo <= d <= hi]


def calendar_resets(index: pd.DatetimeIndex, start: str, end: str, offset_months: int = 0) -> list[pd.Timestamp]:
    """Last trading day of every third month, offset by `offset_months` from calendar quarter-ends
    (0 = Mar/Jun/Sep/Dec, 1 = Jan/Apr/Jul/Oct, 2 = Feb/May/Aug/Nov): the 497K hedge-period calendars."""
    s = pd.Series(index, index=index)
    me = s.groupby(index.to_period("M")).last()
    keep = [d for per, d in me.items() if (per.month - 3 - offset_months) % 3 == 0]
    lo, hi = pd.Period(start).start_time, pd.Period(end).end_time
    return [d for d in keep if lo <= d <= hi]
