import numpy as np
import pandas as pd
import pytest

from collars.engine import calendar_resets, floor_strike, quarter_ends, run, third_fridays
from collars.strategy import CollarSpec, beta_matched, run_phase
from collars.surface import SurfaceParams, vs_vol

P = SurfaceParams(c=0.9, a=-0.1, b=0.02, h=0.0)


@pytest.fixture(scope="module")
def market():
    """Synthetic 3-year market: GBM index, flat 20% vol term structure, 2% rate, 1.5% dividends."""
    rng = np.random.default_rng(1)
    idx = pd.bdate_range("2015-01-01", "2017-12-31")
    n = len(idx)
    S = 2000 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
    div = S * 0.015 / 252
    df = pd.DataFrame({"spx": S, "spx_open": S * (1 + rng.normal(0, 0.002, n)), "div": div,
                       "q": 0.015, "r": 0.02}, index=idx)
    for c in ["vix9d", "vix", "vix3m", "vix6m", "vix1y"]:
        df[c] = 0.20
    tr = (1 + (df["spx"].pct_change().fillna(0) + (div / df["spx"].shift()).fillna(0))).cumprod()
    df["spxtr"] = tr
    return df


def test_no_legs_tracks_total_return(market):
    rolls = quarter_ends(market.index, "2015-01", "2017-12")
    nav = run(market, rolls, lambda qt: [], P).nav
    tr = market["spxtr"].reindex(nav.index)
    assert nav.iloc[-1] / nav.iloc[0] == pytest.approx(tr.iloc[-1] / tr.iloc[0], rel=1e-9)


def test_collar_is_zero_cost_and_bounded(market):
    res = run_phase(market, CollarSpec(), P, "2015-07", "2017-06", phase=0)
    rolls = res.rolls
    assert (rolls["net_mid"].abs() / rolls["S0"] < 0.002).all()     # zero cost up to 5-point strike rounding
    cap = rolls["K2"] / rolls["S0"] - 1
    assert (cap > 0).all() and (cap < 0.15).all()
    # a quarter's collar return can never be below the put-spread floor by more than the 80% tail
    q = res.nav.resample("QE").last().pct_change().dropna()
    assert q.min() > -0.30


def test_no_lookahead(market):
    """Changing every input after a date must leave the NAV up to that date unchanged."""
    spec = CollarSpec()
    base = run_phase(market, spec, P, "2015-07", "2017-06", phase=5).nav
    cut = pd.Timestamp("2016-08-15")
    shocked = market.copy()
    after = shocked.index > cut
    shocked.loc[after, ["spx", "spx_open", "spxtr"]] *= 0.7
    shocked.loc[after, ["vix9d", "vix", "vix3m", "vix6m", "vix1y"]] = 0.45
    alt = run_phase(shocked, spec, P, "2015-07", "2017-06", phase=5).nav
    pd.testing.assert_series_equal(base[base.index <= cut], alt[alt.index <= cut])


def test_beta_matched_uses_reset_beta_from_next_day(market):
    res = run_phase(market, CollarSpec(), P, "2015-07", "2017-06", phase=0)
    b = beta_matched(market, res.rolls, res.nav.index)
    assert b.iloc[0] == 1.0 and b.notna().all()
    assert 0.2 < res.rolls["delta"].mean() < 1.0


def test_calendars():
    idx = pd.bdate_range("2020-01-01", "2020-12-31")
    qe = quarter_ends(idx, "2020-01", "2020-12")
    assert [d.strftime("%m-%d") for d in qe] == ["03-31", "06-30", "09-30", "12-31"]
    assert quarter_ends(idx, "2020-01", "2020-12", phase=1)[0] == pd.Timestamp("2020-04-01")
    tf = third_fridays(idx, "2020-01", "2020-03")
    assert [d.day for d in tf] == [17, 21, 20]
    assert floor_strike(2000.0) == 1995.0 and floor_strike(2001.0) == 2000.0


def test_sister_fund_calendars():
    """The three fund calendars (offset 0/1/2 months) reset in different months, one month apart."""
    idx = pd.bdate_range("2021-01-01", "2021-12-31")
    m0 = [d.month for d in calendar_resets(idx, "2021-01", "2021-12", 0)]
    m1 = [d.month for d in calendar_resets(idx, "2021-01", "2021-12", 1)]
    m2 = [d.month for d in calendar_resets(idx, "2021-01", "2021-12", 2)]
    assert m0 == [3, 6, 9, 12] and m1 == [1, 4, 7, 10] and m2 == [2, 5, 8, 11]
    # each is the last trading day of its month
    for d in calendar_resets(idx, "2021-01", "2021-12", 1):
        assert (d + pd.offsets.BDay(1)).month != d.month


def test_vs_vol_interpolates_total_variance():
    v = np.array([0.1, 0.2, 0.2, 0.2, 0.2])
    assert vs_vol(v, 30 / 365) == pytest.approx(0.2)
    assert 0.1 < vs_vol(v, 20 / 365) < 0.2
