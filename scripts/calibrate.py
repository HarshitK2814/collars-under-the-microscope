"""Fit the Tier-B surface (c, a, b) and half-spread h on the DEVELOPMENT period only, then freeze them.

Objective: sum over CLLZ, BXM, PUT, PPUT of the mean squared error of monthly (roll-to-roll) returns,
model vs actual index. Writes configs/surface.yaml and results/tables/calibration_*.csv.

    python scripts/calibrate.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qcore.splits import Splits  # noqa: E402

from collars.config import RESULTS, ROOT, load  # noqa: E402
from collars.data.load import load as load_market  # noqa: E402
from collars.indices import INDICES, replicate, tracking  # noqa: E402
from collars.surface import SurfaceParams  # noqa: E402

BOUNDS = {"c": (0.6, 1.1), "a": (-0.4, 0.1), "b": (-0.05, 0.2), "h": (0.0, 0.03)}


def main() -> None:
    splits = Splits.from_dict(load("splits"))
    lo, hi = splits.development
    market = load_market()
    market = market.loc[: splits.bounds("development")[1] + pd.Timedelta(days=40)]  # next roll only

    def objective(x):
        p = SurfaceParams(*x)
        for v, (a, b) in zip(x, BOUNDS.values()):
            if not a <= v <= b:
                return 1e3
        try:
            return float(sum(((d := replicate(market, n, p, lo, hi))["model"] - d["actual"]).pow(2).mean()
                             for n in INDICES)) * 1e4
        except ValueError:
            return 1e3

    x0 = np.array([0.90, -0.10, 0.02, 0.005])
    before = tracking(market, SurfaceParams(*x0), lo, hi)
    res = minimize(objective, x0, method="Nelder-Mead",
                   options={"xatol": 1e-4, "fatol": 1e-4, "maxiter": 400, "disp": True})
    p = SurfaceParams(*res.x)
    after = tracking(market, p, lo, hi)
    print("start", x0, "\n", before.round(4))
    print("fitted", np.round(res.x, 5), "obj", res.fun, "\n", after.round(4))

    cfg = {"c": round(float(p.c), 5), "a": round(float(p.a), 5), "b": round(float(p.b), 5),
           "h": round(float(p.h), 5),
           "fitted_on": f"development {lo}..{hi}", "fitted_at": datetime.now().isoformat(timespec="seconds"),
           "objective": "sum of monthly MSE vs CLLZ, BXM, PUT, PPUT", "objective_value": round(float(res.fun), 5)}
    (ROOT / "configs" / "surface.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    before.to_csv(RESULTS / "tables" / "calibration_dev_before.csv")
    after.to_csv(RESULTS / "tables" / "calibration_dev_after.csv")


if __name__ == "__main__":
    main()
