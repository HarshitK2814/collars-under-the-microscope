"""Shared helpers for the v2 scripts: market, frozen surface, v2 splits, prereg lock, JSON output, Sharpe with CI."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from qcore.bootstrap import bootstrap_stat, percentile_ci
from qcore.splits import Splits, file_hash, guard

ROOT = Path(__file__).resolve().parents[3]
PREREG = ROOT / "research" / "preregistration_v2.md"
TABLES = ROOT / "results" / "v2" / "tables"
RUNS = ROOT / "results" / "v2" / "runs"
RAW_CHAIN = ROOT / "data" / "raw" / "cboe_spx_chain.json"
SEEN = "seen period (v1 reported it)"
os.environ.setdefault("PREREG_HASH", "11f656cd0a6f")
TABLES.mkdir(parents=True, exist_ok=True)
RUNS.mkdir(parents=True, exist_ok=True)


def splits() -> Splits:
    return Splits.from_dict(yaml.safe_load((ROOT / "configs" / "splits_v2.yaml").read_text()))


def unlock(period: str) -> None:
    guard(period, PREREG)


def market() -> pd.DataFrame:
    from collars.data.load import load
    return load()


def surface():
    from collars.surface import SurfaceParams
    return SurfaceParams.from_dict(yaml.safe_load((ROOT / "configs" / "surface.yaml").read_text()))


def strategy_cfg() -> dict:
    return yaml.safe_load((ROOT / "configs" / "strategy.yaml").read_text())


def specs():
    from collars.strategy import CollarSpec
    c = strategy_cfg()
    return {"fixed": CollarSpec(m1=c["m1"], m2=c["m2"]),
            "vol": CollarSpec(m1=c["m1"], m2=c["m2"], strikes="vol", z1=c["z1"], z2=c["z2"])}


def dump(name: str, obj) -> None:
    def conv(o):
        if isinstance(o, (np.floating, np.integer)):
            return o.item()
        if isinstance(o, (pd.Timestamp,)):
            return str(o.date())
        return str(o)
    (TABLES / name).write_text(json.dumps(obj, indent=2, default=conv))


def load(name: str):
    return json.loads((TABLES / name).read_text())


def rf_daily(m: pd.DataFrame) -> pd.Series:
    return (m["r"].shift() * m.index.to_series().diff().dt.days / 365).fillna(0.0)


def sharpe_ci(r: pd.Series, rf: pd.Series | float = 0.0, n_boot: int = 1000, seed: int = 0) -> dict:
    """Annualised Sharpe of daily excess returns with a 95% stationary-bootstrap CI (mean block 21)."""
    ex = (r - rf).dropna()
    f = lambda s: float(s.mean() / s.std(ddof=1) * np.sqrt(252))
    lo, hi = percentile_ci(bootstrap_stat(ex, f, n_boot=n_boot, mean_block=21, seed=seed))
    return {"sharpe": f(ex), "lo": lo, "hi": hi, "n_days": int(len(ex))}
