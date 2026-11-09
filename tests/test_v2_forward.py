import numpy as np
import pandas as pd

from collars.engine import quarter_ends, run
from collars.strategy import CollarSpec, ladder
from collars.surface import SurfaceParams
from collars.v2.forward import extend_market
from collars.v2.forward_log import append_new

P = SurfaceParams(c=0.9, a=-0.1, b=0.02, h=0.005)


def _market(n_end="2017-12-31"):
    rng = np.random.default_rng(1)
    idx = pd.bdate_range("2015-01-01", n_end)
    n = len(idx)
    S = 2000 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
    df = pd.DataFrame({"spx": S, "spx_open": S, "div": S * 0.015 / 252, "q": 0.015, "r": 0.02}, index=idx)
    for c in ["vix9d", "vix", "vix3m", "vix6m", "vix1y"]:
        df[c] = 0.20
    df["spxtr"] = (1 + df["spx"].pct_change().fillna(0)).cumprod()
    return df


def test_placeholders_do_not_change_nav_on_real_dates():
    full = _market()
    cut = full[full.index <= "2017-09-15"]
    ext = extend_market(cut, until="2018-12-31")
    spec = CollarSpec()
    rolls = quarter_ends(ext.index, "2015-01", "2018-06")
    r_ext = run(ext, rolls, spec.rule, P)
    # same run, but on the real data only up to the last reset that has a real expiry
    real_rolls = [d for d in rolls if d <= cut.index[-1]]
    r_cut = run(cut, real_rolls, spec.rule, P)
    common = r_cut.nav.index[:-1]   # the last point is the final roll date (roll cost applied only when a next period exists)
    np.testing.assert_allclose(r_ext.nav.reindex(common).to_numpy(), r_cut.nav.reindex(common).to_numpy(), rtol=1e-12)


def test_extend_fills_late_vol_and_zero_dividends():
    m = _market("2016-06-30")
    m.loc[m.index[-1], ["vix", "vix3m"]] = np.nan
    e = extend_market(m, until="2016-07-29")
    assert e[["vix", "vix3m"]].notna().all().all()
    assert (e["div"].iloc[len(m):] == 0).all() and e.index.is_monotonic_increasing


def test_ladder_is_mean_of_tranche_navs():
    idx = pd.bdate_range("2020-01-01", periods=3)
    navs = pd.DataFrame({0: [1.0, 1.1, 1.2], 21: [1.0, 1.0, 1.0], 42: [1.0, 0.9, 0.8]}, index=idx)
    assert np.allclose(ladder(navs, (0, 21, 42)).to_numpy(), [1.0, 1.0, 1.0])


def test_append_is_idempotent(tmp_path):
    p = tmp_path / "f.csv"
    rows = pd.DataFrame({"date": pd.to_datetime(["2026-11-02", "2026-11-03"]), "book": "phase0_collar",
                         "net_return": 0.001, "prereg_hash": "h"})
    assert append_new(p, rows) == 2 and append_new(p, rows) == 0
    assert len(pd.read_csv(p)) == 2
