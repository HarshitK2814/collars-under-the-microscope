"""Real Cboe SPX chain snapshot: measured bid-ask half-spread in vol points, SVI fit, open interest.
The snapshot is one date only (no history), so it informs costs and a cross-check, never the backtest surface."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq, least_squares

from collars import pricing


def read_chain(path: str | Path) -> tuple[pd.DataFrame, float, dt.date]:
    d = json.loads(Path(path).read_text())["data"]
    S = float(d["current_price"])
    rows = []
    for o in d["options"]:
        sym = o["option"]
        body = sym[3:] if sym.startswith("SPX") and not sym.startswith("SPXW") else sym[4:]
        bid, ask = o.get("bid") or 0.0, o.get("ask") or 0.0
        if bid > 0 and ask > bid:
            rows.append({"expiry": dt.datetime.strptime(body[:6], "%y%m%d").date(),
                         "kind": "call" if body[6] == "C" else "put", "K": int(body[7:]) / 1000,
                         "bid": bid, "ask": ask, "oi": o.get("open_interest") or 0.0})
    return pd.DataFrame(rows), S, dt.date.fromisoformat(d["last_trade_time"][:10])


def implied(target, F, K, tau, r, kind) -> float:
    try:
        return brentq(lambda s: pricing.price(F, K, tau, r, s, kind) - target, 1e-3, 3.0, xtol=1e-7)
    except ValueError:
        return np.nan


def halfspread_table(chain, S, asof, expiry, r, q) -> pd.DataFrame:
    """Per OTM option on one expiry: moneyness, mid IV, half-spread in vol units h = (ask-bid)/2/vega (vega per 1.00),
    the same unit as surface.yaml `h` (fill = mid +/- h * vega)."""
    tau = (expiry - asof).days / 365
    F = S * np.exp((r - q) * tau)
    sub = chain[chain["expiry"] == expiry]
    sub = sub[((sub["kind"] == "put") & (sub["K"] < F)) | ((sub["kind"] == "call") & (sub["K"] >= F))]
    out = []
    for o in sub.itertuples():
        mid = (o.bid + o.ask) / 2
        iv = implied(mid, F, o.K, tau, r, o.kind)
        if not np.isfinite(iv):
            continue
        vega = pricing.greeks(S, o.K, tau, r, q, iv, o.kind).vega
        if vega <= 0:
            continue
        out.append({"kind": o.kind, "K": o.K, "mny": o.K / S, "iv": iv, "h": (o.ask - o.bid) / 2 / vega,
                    "oi": o.oi, "tau": tau, "F": F})
    return pd.DataFrame(out)


def svi_w(k, p):
    a, b, rho, m, s = p
    return a + b * (rho * (k - m) + np.sqrt((k - m) ** 2 + s * s))


def fit_svi(k: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Raw SVI total-variance slice w(k) by bounded least squares (one expiry)."""
    x0 = [max(w.min() * 0.5, 1e-4), 0.1, -0.5, 0.0, 0.1]
    lb = [-1.0, 1e-4, -0.999, -1.0, 1e-3]
    ub = [2.0, 5.0, 0.999, 1.0, 2.0]
    res = least_squares(lambda p: svi_w(k, p) - w, x0, bounds=(lb, ub), max_nfev=5000)
    return res.x
