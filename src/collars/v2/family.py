"""H2 family: 63 phases x {fixed, vol-unit strikes} single collars + 21 three-tranche ladders per rule = 168 columns."""

from __future__ import annotations

import pandas as pd

from collars.strategy import CollarSpec, ladders, run_phases


def family_navs(market, p, specs: dict[str, CollarSpec], start: str, end: str) -> tuple[pd.DataFrame, dict]:
    cols, rolls_all = {}, {}
    for name, spec in specs.items():
        navs, rolls = run_phases(market, spec, p, start, end)
        for ph in navs.columns:
            cols[f"{name}_phase{ph}"] = navs[ph]
        lad = ladders(navs)
        for phi in lad.columns:
            cols[f"{name}_ladder{phi}"] = lad[phi]
        rolls_all[name] = rolls
    return pd.DataFrame(cols), rolls_all


def family_returns(navs: pd.DataFrame) -> pd.DataFrame:
    return navs.pct_change().dropna(how="all").dropna(axis=1)
