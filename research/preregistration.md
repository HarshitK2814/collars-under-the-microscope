# Pre-registration — Collars Under the Microscope

Frozen 2026-09-27, before any test-period (2020–2023) or recent-period (2024+) strategy result was computed.
The file's SHA-256 prefix (`qcore.splits.file_hash`) unlocks the test period; any edit changes the hash and re-locks it.
What had been seen before freezing is listed in `experiment_log.md` (development and validation results; the fund's
2026-06-30 N-PORT strikes; the structural leg counts of all 28 N-PORT filings).

## 1. Frozen inputs

| Item | Value | Source |
|---|---|---|
| Surface | c = 0.81633, a = −0.27601, b = −0.01130 | `configs/surface.yaml`, fitted on 2011–2016 |
| Half-spread | h = 0.464 vol pt on every leg at each open; no cost at expiry (cash settlement) | same |
| Fixed-moneyness strikes | K1 = 0.95·S, K2 = 0.80·S, rounded to 5 points | 497K band; N-PORT |
| Call strike | zero net premium at mid, rounded to 5 points | 497K "substantially offsets" |
| Vol-unit strikes (RQ2) | z1 = 0.60225, z2 = 2.84555 ATM standard deviations below the forward | `configs/strategy.yaml`, fitted on 2011–2016 |
| Reset | 16:00 close of quarter-end + φ trading days, φ = 0…62; φ = 0 is the fund's disclosed calendar | 497K hedge periods |
| Expiry | the next reset day (PM-settled) | N-PORT: quarter-end expiries |
| Equity sleeve / hedge ratio | S&P 500 total return / 1.0 | reconstruction |
| Ladder | three tranches φ, φ+21, φ+42, 1/3 notional each, no cross-rebalancing; 21 distinct ladders | spec |
| Beta-matched benchmark | ex-ante collar delta per unit NAV at each reset close in S&P TR, rest in 3-month T-bills, from the next day | spec §6 |
| Bootstrap | stationary, mean block 63 trading days, 2,000 draws, seed 0, all series resampled jointly | `collars.analysis` |
| Code | `scripts/run.py analyse` and `robust`, as of this freeze | — |

## 2. Test window

Test: 2020-01-01 → 2023-12-31 (includes COVID and 2022). Recent: 2024-01 → latest available close, reported
separately, never used for any decision. Each phase is evaluated on the same calendar window, anchored at the last
close before it; positions opened before the window are carried in.

## 3. Hypotheses and decision rules

**H1 (primary, RQ1).** Ratio = sd across the 63 phases of annualised return (single tranche) ÷ sd across the 21 ladders.
*Supported* if all three hold: (a) the point ratio ≥ 2; (b) the 95% bootstrap CI lower bound > 1; (c) ladder(0,21,42)
minus phase 0 annualised return is **not** significantly negative (two-sided bootstrap p ≥ 0.05, or the difference is positive).
*Partially supported* if (b) and (c) hold but (a) fails. *Not supported* otherwise.
Also reported, not tested: return range, IQR, max-drawdown range across phases, and the fund phase's rank.

**H2 (RQ2).** Stability = max − min over VIX-tercile regimes (tercile of VIX at the reset vs its own history since 1990) of
HE = 1 − var(collar daily return) / var(S&P TR daily return); regimes with < 20 days in a phase are skipped.
*Supported* if the mean over phases of (stability_vol − stability_fixed) < 0 **and** vol-unit strikes are more stable in
≥ 2/3 of phases. This is a descriptive comparison over dependent phases; no p-value is claimed.

**H3 (RQ3), phase 0.** Collar vs beta-matched benchmark.
*The collar adds value* if the Sharpe difference is > 0 with bootstrap p < 0.05, **or** the monthly CVaR95 is reduced
(> 0) while the return forgone is ≤ 0. *Expensive low-beta* (Israelov–Klein) if the Sharpe-difference CI contains 0
and CVaR95 is not reduced. Otherwise *mixed*. Also reported: the share of the 63 phases with a CVaR reduction.

## 4. Pre-registered secondary outputs

* Per-leg Greek attribution for phase 0 (delta, gamma+theta = VRP channel, vega, residual). Prediction (spec):
  the long 95% put pays VRP (negative), the short 80% put earns it (positive).
* Ablations for phase 0: no short put, no short call, no long put.
* Benchmarks with Sharpe CIs: S&P TR, beta-matched, CLLZ, PPUT, BXM, JHEQX NAV (tracking only: it includes stock
  selection and fees).
* Pricer checks: tracking error to CLLZ/BXM/PUT/PPUT on test; model vs the fund's actual call strike for every test
  quarter in N-PORT (given the fund's put strikes), reported as the mean absolute cap error.
* Robustness (`run.py robust`): h ∈ {0.25, 0.5, 1.0} vol pt; m1 ∈ {0.93, 0.945, 0.95, 0.97} × m2 ∈ {0.75, 0.80, 0.85};
  hedge ratio 0.87; excluding 2020 (window 2021–2023).

## 5. What would count against the project

* Test-period CLLZ tracking error > 2%/yr: all results are reported as indicative only.
* A mean absolute N-PORT cap error > 1 percentage point: the pricer's call wing is not trusted.
* Any bug fix after the test run is logged with before/after numbers; no parameter is re-fitted on test data.
