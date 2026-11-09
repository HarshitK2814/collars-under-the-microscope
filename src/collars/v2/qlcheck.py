"""QuantLib cross-check of the Black-76 pricer (collars.pricing). QuantLib is an independent implementation."""

from __future__ import annotations

import numpy as np

from collars import pricing


def ql_value(S: float, K: float, tau: float, r: float, q: float, sigma: float, kind: str) -> dict:
    import QuantLib as ql

    today = ql.Date(2, 1, 2025)
    ql.Settings.instance().evaluationDate = today
    days = max(int(round(tau * 365)), 1)
    expiry = today + days
    dc = ql.Actual365Fixed()
    typ = ql.Option.Call if kind == "call" else ql.Option.Put
    opt = ql.VanillaOption(ql.PlainVanillaPayoff(typ, K), ql.EuropeanExercise(expiry))
    spot = ql.QuoteHandle(ql.SimpleQuote(S))
    proc = ql.BlackScholesMertonProcess(
        spot, ql.YieldTermStructureHandle(ql.FlatForward(today, q, dc)),
        ql.YieldTermStructureHandle(ql.FlatForward(today, r, dc)),
        ql.BlackVolTermStructureHandle(ql.BlackConstantVol(today, ql.NullCalendar(), sigma, dc)))
    opt.setPricingEngine(ql.AnalyticEuropeanEngine(proc))
    return {"price": opt.NPV(), "delta": opt.delta(), "gamma": opt.gamma(), "vega": opt.vega(), "tau_used": days / 365}


def max_errors(n: int = 400, seed: int = 0) -> dict:
    """Random grid: S=1, strike 0.7-1.3, tau 0.05-1y, r 0-5%, q 0-3%, sigma 8-60%. Errors per unit of S."""
    rng = np.random.default_rng(seed)
    e = {"price": [], "delta": [], "gamma": [], "vega": []}
    for _ in range(n):
        K, tau = rng.uniform(0.7, 1.3), round(rng.uniform(0.05, 1.0) * 365) / 365
        r, q, sg = rng.uniform(0, 0.05), rng.uniform(0, 0.03), rng.uniform(0.08, 0.6)
        kind = "call" if rng.random() < 0.5 else "put"
        a = ql_value(1.0, K, tau, r, q, sg, kind)
        g = pricing.greeks(1.0, K, tau, r, q, sg, kind)
        e["price"].append(abs(a["price"] - g.price)), e["delta"].append(abs(a["delta"] - g.delta))
        e["gamma"].append(abs(a["gamma"] - g.gamma)), e["vega"].append(abs(a["vega"] - g.vega))
    return {k: float(np.max(v)) for k, v in e.items()} | {"n": n}
