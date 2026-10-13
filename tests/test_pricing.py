import numpy as np
import pytest

from collars.pricing import greeks, price, zero_cost_call_strike


def test_put_call_parity():
    F, K, tau, r, s = 4000.0, 3800.0, 0.25, 0.04, 0.2
    c, p = price(F, K, tau, r, s, "call"), price(F, K, tau, r, s, "put")
    assert c - p == pytest.approx(np.exp(-r * tau) * (F - K), rel=1e-10)


def test_known_value():
    # Hull-style check: F=K=100, tau=1, r=0, sigma=0.2 -> ATM = F*(2N(0.1)-1) = 7.9656
    assert price(100.0, 100.0, 1.0, 0.0, 0.2, "call") == pytest.approx(7.965567, abs=1e-5)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_greeks_match_finite_differences(kind):
    S, K, tau, r, q, s = 4000.0, 3900.0, 0.25, 0.04, 0.015, 0.18
    g = greeks(S, K, tau, r, q, s, kind)
    h = 0.001 * S
    up = greeks(S + h, K, tau, r, q, s, kind).price
    dn = greeks(S - h, K, tau, r, q, s, kind).price
    assert g.delta == pytest.approx((up - dn) / (2 * h), rel=1e-3)
    assert g.gamma == pytest.approx((up - 2 * g.price + dn) / h**2, rel=1e-2)
    dv = 1e-4
    assert g.vega == pytest.approx(
        (greeks(S, K, tau, r, q, s + dv, kind).price - greeks(S, K, tau, r, q, s - dv, kind).price) / (2 * dv),
        rel=1e-4)
    dt = 1e-5
    assert g.theta == pytest.approx(
        -(greeks(S, K, tau + dt, r, q, s, kind).price - greeks(S, K, tau - dt, r, q, s, kind).price) / (2 * dt),
        rel=1e-3)


def test_zero_cost_collar_costs_zero():
    S, tau, r = 4000.0, 0.25, 0.03
    F = S * np.exp(r * tau)
    vol = lambda k: 0.18 - 0.3 * np.log(k / F)      # downward skew
    K1, K2 = 0.95 * S, 0.80 * S
    Kc = zero_cost_call_strike(F, tau, r, K1, K2, vol)
    assert Kc > F
    net = (price(F, K1, tau, r, vol(K1), "put") - price(F, K2, tau, r, vol(K2), "put")
           - price(F, Kc, tau, r, vol(Kc), "call"))
    assert net == pytest.approx(0.0, abs=1e-6)
    assert 0.0 < Kc / S - 1 < 0.10
