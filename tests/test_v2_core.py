import datetime as dt

import numpy as np
import pandas as pd
import pytest

from collars import pricing
from collars.v2 import chainfit, hawkes_panel, volfc


def test_quantlib_matches_black76():
    pytest.importorskip("QuantLib")
    from collars.v2.qlcheck import max_errors

    e = max_errors(n=60)
    assert e["price"] < 2e-4 and e["delta"] < 2e-4 and e["gamma"] < 2e-3 and e["vega"] < 2e-3


def test_realised_forward_uses_only_future_days():
    r = pd.Series(np.arange(1.0, 11.0), index=pd.bdate_range("2020-01-01", periods=10))
    f = volfc.realised_forward(r, h=3)
    assert f.iloc[0] == pytest.approx(np.mean([4.0, 9.0, 16.0]))   # days 2..4
    assert np.isnan(f.iloc[-1]) and np.isnan(f.iloc[-3])


def test_qlike_zero_at_truth_and_positive_elsewhere():
    s = pd.Series([1.0, 2.0])
    assert (volfc.qlike(s, s) == 0).all()
    assert (volfc.qlike(s, s * 2) > 0).all() and (volfc.qlike(s, s / 2) > 0).all()


def test_garch_forecast_is_causal():
    pytest.importorskip("arch")
    rng = np.random.default_rng(0)
    idx = pd.bdate_range("2000-01-01", periods=1100)
    r = pd.Series(rng.standard_t(6, 1100) * 0.01, index=idx)
    f1 = volfc.garch_forward_variance(r, h=5, refit_every=50, min_obs=800)
    r2 = r.copy()
    r2.iloc[1050:] *= 10          # perturb the future only
    f2 = volfc.garch_forward_variance(r2, h=5, refit_every=50, min_obs=800)
    ok = f1.dropna().index[f1.dropna().index < idx[1049]]
    assert len(ok) > 100
    np.testing.assert_allclose(f1[ok], f2[ok], rtol=1e-6)
    assert (f1.dropna() > 0).all()


def test_events_and_intensity_are_causal():
    rng = np.random.default_rng(1)
    idx = pd.bdate_range("2000-01-01", periods=3000)
    r = pd.Series(rng.normal(0, 0.01, 3000), index=idx)
    r.iloc[rng.choice(np.arange(300, 3000), 80, replace=False)] -= 0.05
    ev = hawkes_panel.crash_events(r)
    assert ev.sum() >= 20
    d = idx[[1500, 2000, 2500]]
    a = hawkes_panel.intensity_at(ev, d)
    r2 = r.copy()
    r2.iloc[2400:] *= 3          # change events after the dates 1500 and 2000 only
    b = hawkes_panel.intensity_at(hawkes_panel.crash_events(r2), d)
    assert a.iloc[0] == pytest.approx(b.iloc[0]) and a.iloc[1] == pytest.approx(b.iloc[1])
    assert (a.dropna() > 0).all()


def test_svi_recovers_known_slice():
    k = np.linspace(-0.4, 0.3, 40)
    p = np.array([0.01, 0.1, -0.6, 0.0, 0.15])
    got = chainfit.fit_svi(k, chainfit.svi_w(k, p))
    np.testing.assert_allclose(chainfit.svi_w(k, got), chainfit.svi_w(k, p), atol=1e-5)


def test_halfspread_recovers_constant_vol_spread():
    S, r, q, sg, h = 100.0, 0.02, 0.01, 0.2, 0.004
    asof, exp = dt.date(2025, 1, 1), dt.date(2025, 4, 1)
    tau = (exp - asof).days / 365
    F = S * np.exp((r - q) * tau)
    rows = []
    for K in range(80, 121, 5):
        kind = "put" if K < F else "call"
        mid = float(pricing.price(F, K, tau, r, sg, kind))
        v = pricing.greeks(S, K, tau, r, q, sg, kind).vega
        rows.append({"expiry": exp, "kind": kind, "K": float(K), "bid": mid - h * v, "ask": mid + h * v, "oi": 1.0})
    tab = chainfit.halfspread_table(pd.DataFrame(rows), S, asof, exp, r, q)
    assert len(tab) >= 8
    assert tab["h"].median() == pytest.approx(h, rel=0.02)
