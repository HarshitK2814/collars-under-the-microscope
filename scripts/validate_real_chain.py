"""POST-HOC real-option-quote validation of the Tier-B surface (no WRDS / OptionMetrics needed).

Cboe publishes a free delayed full SPX option chain as JSON. It is a *current snapshot* only (no history, so it
cannot be used in the backtest), but it is real, exchange-sourced option data, which is exactly what the free VIX-based
surface was accused of not having. This script:
  * downloads the chain, picks the expiry closest to 91 days,
  * builds the frozen surface from today's VIX-family closes and prices the same strikes,
  * compares model implied vol to the chain's mid-based implied vol across the 80%-105% moneyness band,
  * solves the collar (0.95/0.80 puts, zero-cost call) on BOTH the real chain and the model and compares the cap.

    python scripts/validate_real_chain.py
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from collars.config import RAW, RESULTS, ROOT  # noqa: E402
from collars.data.load import load as load_market  # noqa: E402
from collars.engine import Quote, zero_cost_call  # noqa: E402
from collars.pricing import price  # noqa: E402
from collars.surface import SurfaceParams, implied_vol, vol_matrix, vs_vol  # noqa: E402

URL = "https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json"


def load_chain() -> tuple[pd.DataFrame, float, dt.date]:
    r = requests.get(URL, headers={"User-Agent": "Mozilla/5.0 (research)"}, timeout=60)
    r.raise_for_status()
    (RAW / "cboe_spx_chain.json").write_bytes(r.content)
    d = r.json()["data"]
    S = float(d["current_price"])
    rows = []
    for o in d["options"]:
        sym = o["option"]                      # e.g. SPXW261016C00200000 or SPX261016C...
        body = sym[3:] if sym.startswith("SPX") and not sym.startswith("SPXW") else sym[4:]
        exp = dt.datetime.strptime(body[:6], "%y%m%d").date()
        cp = body[6]
        strike = int(body[7:]) / 1000
        bid, ask = o.get("bid") or 0, o.get("ask") or 0
        if bid > 0 and ask > 0:
            rows.append({"expiry": exp, "kind": "call" if cp == "C" else "put", "K": strike,
                         "mid": (bid + ask) / 2, "iv_cboe": o.get("iv"), "oi": o.get("open_interest", 0)})
    return pd.DataFrame(rows), S, dt.date.fromisoformat(d["last_trade_time"][:10])


def bs_implied_vol(target, F, K, tau, r, kind) -> float:
    from scipy.optimize import brentq
    f = lambda s: price(F, K, tau, r, s, kind) - target
    try:
        return brentq(f, 1e-3, 3.0, xtol=1e-6)
    except ValueError:
        return np.nan


def main() -> None:
    chain, S, asof = load_chain()
    m = load_market()
    p = SurfaceParams.from_dict(yaml.safe_load((ROOT / "configs" / "surface.yaml").read_text()))
    i = len(m) - 1                                     # latest close for the VIX-family surface
    r, q = m["r"].iloc[i], m["q"].iloc[i]

    # expiry closest to 91 days
    target = asof + dt.timedelta(days=91)
    exps = sorted(chain["expiry"].unique(), key=lambda e: abs((e - target).days))
    exp = exps[0]
    tau = (exp - asof).days / 365
    F = S * np.exp((r - q) * tau)
    sig_vs = vs_vol(vol_matrix(m)[i], tau)
    sub = chain[chain["expiry"] == exp].copy()
    # OTM only: puts below F, calls above F (the liquid wing)
    sub = sub[((sub["kind"] == "put") & (sub["K"] < F)) | ((sub["kind"] == "call") & (sub["K"] >= F))]
    sub["mny"] = sub["K"] / S
    band = sub[(sub["mny"] >= 0.80) & (sub["mny"] <= 1.05)].copy()
    band["iv_model"] = [float(implied_vol(k, F, tau, sig_vs, p)) for k in band["K"]]
    band["iv_real"] = [bs_implied_vol(row.mid, F, row.K, tau, r, row.kind) for row in band.itertuples()]
    band = band.dropna(subset=["iv_real"])
    band["iv_err"] = band["iv_model"] - band["iv_real"]

    qt = Quote(S, F, tau, r, q, sig_vs, p)
    K1, K2 = round(0.95 * S / 5) * 5, round(0.80 * S / 5) * 5
    kc_model = zero_cost_call(qt, float(qt.mid("put", K1) - qt.mid("put", K2)))

    # real-chain collar: interpolate real mids at K1, K2, then find the real call strike with matching premium
    def real_mid(kind, K):
        d = sub[sub["kind"] == kind].sort_values("K")
        return float(np.interp(K, d["K"], d["mid"]))
    cost_real = real_mid("put", K1) - real_mid("put", K2)
    calls = sub[(sub["kind"] == "call") & (sub["K"] > F)].sort_values("K")
    kc_real = float(np.interp(-cost_real, -calls["mid"], calls["K"]))    # mid decreasing in K

    out = {
        "as_of": asof.isoformat(), "spot": round(S, 2), "expiry": exp.isoformat(), "days": (exp - asof).days,
        "n_strikes_compared": int(len(band)),
        "iv_mae_volpts": round(float(band["iv_err"].abs().mean()) * 100, 2),
        "iv_bias_volpts": round(float(band["iv_err"].mean()) * 100, 2),
        "atm_iv_model": round(float(implied_vol(F, F, tau, sig_vs, p)) * 100, 2),
        "atm_iv_real": round(float(band.iloc[(band["mny"] - 1).abs().argmin()]["iv_real"]) * 100, 2),
        "collar_cap_model_pct": round((kc_model / S - 1) * 100, 2),
        "collar_cap_real_pct": round((kc_real / S - 1) * 100, 2),
    }
    band[["kind", "K", "mny", "iv_real", "iv_model", "iv_err"]].round(4).to_csv(
        RESULTS / "tables" / "posthoc_real_chain_iv.csv", index=False)
    (RESULTS / "runs").mkdir(exist_ok=True, parents=True)
    import json
    (RESULTS / "runs" / "posthoc_real_chain.json").write_text(json.dumps(out, indent=2))
    for k, v in out.items():
        print(f"{k:24} {v}")


if __name__ == "__main__":
    main()
