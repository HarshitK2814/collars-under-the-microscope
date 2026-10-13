"""Daily Greek P&L attribution per leg for one run of the collar (spec Section 6).

For each leg and day t-1 -> t (Greeks at t-1, same strike):
    dV ≈ Δ dS + ½ Γ dS² + ν dσ + Θ dt + ε
The gamma + theta terms together are the leg's variance-risk-premium channel: for Black-Scholes,
Θ ≈ -½ Γ S² σ², so ½Γ dS² + Θ dt ≈ ½ Γ S² (realised² - implied²) dt.
Contributions are expressed per unit of index at the reset (divided by S0 of that quarter) and summed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from collars import pricing
from collars.surface import SurfaceParams, implied_vol, vol_matrix, vs_vol

LEG_NAMES = {0: "long_put", 1: "short_put", 2: "short_call"}


def attribute(market: pd.DataFrame, rolls: pd.DataFrame, p: SurfaceParams,
              start: str | None = None, end: str | None = None) -> pd.DataFrame:
    idx = market.index
    S, r, q, V = market["spx"].to_numpy(), market["r"].to_numpy(), market["q"].to_numpy(), vol_matrix(market)
    lo = pd.Period(start).start_time if start else idx[0]
    hi = pd.Period(end).end_time if end else idx[-1]
    rows = []
    n_legs = sum(1 for c in rolls.columns if c.startswith("K") and c[1:].isdigit())
    for d0, rr in rolls.iterrows():
        i0, i1 = idx.get_loc(d0), idx.get_loc(rr["expiry"])
        for j in range(n_legs):
            K, qty = rr[f"K{j}"], rr[f"q{j}"]
            if pd.isna(K):
                continue
            kind = "put" if j < 2 else "call"
            if n_legs < 3:   # ablations: infer the kind from strike vs spot
                kind = "call" if K > rr["S0"] else "put"
            prev = None
            for i in range(i0, i1 + 1):
                d = idx[i]
                tau = (rr["expiry"] - d).days / 365
                if tau <= 0:
                    val = max(S[i] - K, 0) if kind == "call" else max(K - S[i], 0)
                    g = None
                else:
                    F = S[i] * np.exp((r[i] - q[i]) * tau)
                    sig = float(implied_vol(K, F, tau, vs_vol(V[i], tau), p))
                    g = pricing.greeks(S[i], K, tau, r[i], q[i], sig, kind)
                    val = g.price
                if prev is not None and lo <= d <= hi:
                    pg, pS, psig, pd_ = prev
                    dS = S[i] - pS
                    dt = (d - pd_).days / 365
                    dsig = (sig - psig) if g is not None else 0.0
                    parts = {"delta": pg.delta * dS, "gamma": 0.5 * pg.gamma * dS * dS,
                             "vega": pg.vega * dsig, "theta": pg.theta * dt}
                    total = val - pg.price
                    rows.append({"date": d, "reset": d0, "leg": LEG_NAMES.get(j, f"leg{j}"),
                                 **{k: qty * v / rr["S0"] for k, v in parts.items()},
                                 "total": qty * total / rr["S0"]})
                if g is not None:
                    prev = (g, S[i], sig, d)
    out = pd.DataFrame(rows)
    out["residual"] = out["total"] - out[["delta", "gamma", "vega", "theta"]].sum(axis=1)
    out["gamma_theta_vrp"] = out["gamma"] + out["theta"]
    return out


def summarise(attr: pd.DataFrame) -> pd.DataFrame:
    """Sum of contributions per leg, in % of index notional per year."""
    years = (attr["date"].max() - attr["date"].min()).days / 365.25
    cols = ["delta", "gamma", "theta", "gamma_theta_vrp", "vega", "residual", "total"]
    s = attr.groupby("leg")[cols].sum() / years * 100
    s.loc["all_legs"] = s.sum()
    return s.round(3)
