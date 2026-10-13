# Experiment log

Every run and every look at data that could influence a design choice, in order. Test (2020–23) and recent
(2024+) periods are locked by `qcore.splits` until `research/preregistration.md` is committed.

## 2026-09-27 — Week-1 SEC and N-PORT checks

**SEC quotes.** 14 quotes from the 497K (0001193125-25-261069) and the 2026-02-27 supplement (0001193125-26-079407)
verified verbatim (`scripts/extract_sec_quotes.py`). Finding: the hedge periods are calendar quarters (spec corrected).

**Disclosure of a locked-period look.** Before the lock was applied to N-PORT data, one *recent*-period quarter was
viewed by hand: period 2026-06-30 (acc. 0002071691-26-021121), strikes 0.9466 / 0.7980 / 1.0515 × the 2026-03-31
close. This is recorded here so that any later choice it could have influenced is visible. No parameters were fitted to it.

**N-PORT history.** 28 NPORT-P filings for series S000043249 (periods 2019-09-30 → 2026-06-30), parsed to
`data/interim/nport_options.parquet` (`collars.data.nport`). Structural facts across all 28 (no strikes or values read):
every period has exactly 3 option legs with a single expiry, i.e. one collar per quarter and no second, intra-quarter
collar outstanding at the quarter-end snapshot.

**Unlocked strikes (validation, 2 quarters)** — `scripts/nport_strikes.py --period development,validation`,
table in `results/tables/nport_strikes_development_validation.csv`. Moneyness against the S&P 500 close on the
prior quarter's last trading day:

| Period | K1 (long put) | K2 (short put) | Kc (short call) | Cap | Notional ÷ assets |
|---|---|---|---|---|---|
| 2019-09-30 | 0.9450 | 0.7954 | 1.0334 | 3.34% | 0.98 |
| 2019-12-31 | 0.9457 | 0.7979 | 1.0313 | 3.13% | 0.91 |

Observations (n = 2, so not conclusions):
1. K1 sits at ≈0.945, not 0.95; the gap (≈15 index points) is larger than strike-grid rounding (5 points).
   Possibilities: a 94.5% rule, or strikes set from a different price than the 16:00 close. **Decide K1 at pre-registration**,
   with 0.95 as the spec's rule and 0.945 as a sensitivity, not by fitting to these two points.
2. Both caps are below the 3.5–5.5% band from the 2025 prospectus. Check the band stated in the 2019 prospectus
   before calling this a disclosure deviation.
3. Hedge notional ≈ 0.9–1.0 × assets supports hedge ratio 1.0 as the baseline.

**2019 prospectus check.** The 497K dated 2019-11-01 (acc. 0001193125-19-281595) states only the 5–20% band; no
cap range and no calendar hedge-period wording (verified by `extract_sec_quotes.py`, S4). The 2019 caps are therefore
not a disclosure deviation.

## 2026-09-27 — Tier-B surface calibration (development only)

`scripts/calibrate.py`: Nelder–Mead on (c, a, b, h), objective = sum of monthly-return MSE vs CLLZ, BXM, PUT, PPUT,
2011-01..2016-12 (third-Friday rolls, open as the SOQ/11:00 proxy). 196 evaluations.

* Before any fit, all four indices were over-predicted by 1–3.5%/yr with fills at mid for the VWAP-traded indices.
  The zero-option engine check matched S&P TR within 0.2% over six years, so the gap was execution cost, not an
  engine bug. Decision (before fitting): one common half-spread h for all legs.
* **Frozen:** c = 0.8163 (ATM / variance-swap vol), a = −0.2760 (skew), b = −0.0113 (curvature), h = 0.464 vol pt.
* Development tracking (annualised TE / bias): CLLZ 1.39% / +0.56%, BXM 1.46% / +0.52%, PUT 1.43% / −0.74%, PPUT 1.04% / −0.23%.
* **Validation (2017–19, out of sample):** CLLZ 1.28% / −1.53%, BXM 1.08% / +0.34%, PUT 0.99% / +1.37%, PPUT 0.69% / −0.40%.
  All under the spec's 2%/yr "indicative only" threshold.
* **N-PORT out-of-sample check (validation quarters):** given the fund's actual put strikes, the frozen surface's
  zero-cost call is 3042.7 vs actual 3040 (Q3 2019) and 3075.8 vs 3070 (Q4 2019): cap 3.43% vs 3.34%, 3.33% vs 3.13%.
* Vol-unit strikes (`run.py fit-strikes`, development): z1 = 0.6023, z2 = 2.8456 ATM standard deviations.

## 2026-09-27 — Development and validation runs

`run.py analyse --period development,validation` (2,000 bootstrap draws, mean block 63 days).
Costs: h = 0.464 vol pt per leg at each open (≈17–18 bp of index per reset); expiry is cash settlement (no cost).

| | Development 2011–16 | Validation 2017–19 |
|---|---|---|
| Phase ann. return range | 4.51% – 7.71% | 4.97% – 10.90% |
| TL = sd across 63 phases | 0.82% | 1.70% |
| sd across 21 ladders | 0.53% | 0.46% |
| **H1 ratio** (95% CI) | **1.54** (1.38, 3.16) | **3.67** (1.82, 6.82) |
| Ladder(0,21,42) − phase 0 | −0.64% (p 0.38) | −1.16% (p 0.20) |
| Fund's phase 0 rank of 63 | 14 | 21 |
| Max-DD range across phases | −12.4% … −6.3% | −12.5% … −5.2% |
| RQ2 share of phases where vol-unit strikes are more stable | 76% | 68% |
| RQ3 phase 0: Sharpe diff vs beta-matched (CI) | +0.11 (−0.20, 0.38) | +0.21 (−0.17, 0.65) |
| RQ3 phase 0: CVaR95 reduction (monthly) | −0.44 pp (worse) | +0.38 pp |
| Mean cap (all resets) | 2.9% | 3.0% |
| Phase 0 vs JHEQX NAV, monthly corr / TE | 0.978 / 1.44% (from 2014-05) | 0.978 / 1.35% |

Validation robustness grid (`run.py robust --period validation`): H1 ratio 3.0–3.7 across m1 ∈ {0.93, 0.945, 0.95, 0.97},
m2 ∈ {0.75, 0.80, 0.85}, h ∈ {0.25, 0.5, 1.0} vol pt and hedge ratio 0.87.

Notes: in validation, 32 phase×regime cells had < 20 days (few high-VIX days in 2017), so RQ2 stability uses the
regimes that have data. H1's 2× threshold was set in the specification before any run; development (1.54) is below it
and validation (3.67) above it. Neither is a result for the claim; the test period decides.

## 2026-09-27 — Pre-registration frozen

`research/preregistration.md` hash `02978b50f111`; SHA-256 of the pre-registration, configs and code in
`research/sources/prereg_freeze_sha256.txt`. Not committed to git at this point (commits only on request); the hash file is the record.
Test period opened next with `PREREG_HASH=02978b50f111`.

## 2026-09-27 — Test period (2020–2023), run once under PREREG_HASH=02978b50f111

Commands: `run.py track --period test`, `run.py analyse --period test`, `nport_strikes.py --period test`,
`run.py robust --period test`. No code or parameter was changed after the freeze.

* **Pricer:** test tracking error CLLZ 3.70%/yr (bias −0.95%), BXM 2.65%, PUT 1.81%, PPUT 3.04%. **CLLZ is above the
  pre-registered 2%/yr threshold, so the test results are labelled indicative.** Recent period (2024+): 0.6–1.5%/yr.
* **N-PORT:** 16 test quarters, mean absolute cap error 0.38 pp (bias +0.18 pp), below the 1 pp threshold.
  All 28 quarters: MAE 0.34 pp, correlation 0.92.
* **H1:** ratio 1.73, CI (1.39, 3.05); ladder(0,21,42) − phase 0 = −1.45%/yr, CI (−4.08%, +1.17%), p 0.285.
  (a) fails, (b) and (c) hold → **partially supported**. Phase returns 3.35% … 10.68%/yr (phase 0: 7.42%, rank 21 of 63);
  ladders 5.41% … 8.40%. Max-DD range: singles −19.8% … −12.5%, ladders 1.9 pp wide.
* **H2:** vol-unit strikes more stable in 16% of phases (mean stability +5.8 pp worse) → **not supported** (reverses
  development 76% and validation 68%).
* **H3 (phase 0):** Sharpe 0.56 vs 0.51 beta-matched, difference +0.05, CI (−0.37, +0.40), p 0.76; monthly CVaR95 5.59% vs
  4.30% (not reduced); return forgone −0.55%/yr → **expensive low-beta** (Israelov–Klein). 6% of phases reduce CVaR.
* **Attribution (phase 0, % of index/yr):** gamma+theta long put −2.30, short put +1.22, short call +1.58.
* **Robustness:** ratio 1.25–2.13 across the grid (≥ 2 only for m1 = 0.93 with m2 ≤ 0.80); h has no effect on the ratio;
  excluding 2020 → 1.56.
* **JHEQX tracking:** monthly correlation 0.989, TE 1.36%/yr; model 7.42%/yr vs fund NAV 8.38%/yr.

## Recent period (2024-01 → 2026-09-25), reported separately

Ratio 1.61, CI (1.31, 3.29); phase returns 9.90% … 15.37%/yr; ladder − phase 0 +0.78% (p 0.61). Vol-unit strikes
more stable in 87% of phases. Phase 0 Sharpe 0.74 vs 1.05 beta-matched (difference −0.31, CI −0.70, +0.10);
CVaR95 5.56% vs 2.47%. JHEQX monthly correlation 0.977.

## 2026-09-28 — Post-hoc external validation (real option quotes + sister funds)

Prompted by "is this how industry specialists work, and can the free-data pricer be trusted?" Nothing here changed a
pre-registered result. Full write-up: `research/posthoc_validation.md`.

* **Real option chain (WRDS-free).** Cboe's free delayed SPX chain (current snapshot only) vs the frozen surface,
  2026-09-25, 97-day expiry: over 388 strikes in the 80–105% band, implied-vol MAE **0.71 vol pt**, bias +0.04;
  zero-cost collar cap 4.75% (model) vs 4.38% (real chain). Downside skew matched closely; call wing slightly rich.
  `scripts/validate_real_chain.py`.
* **Sister funds.** Hedged Equity 2 (S000070948) and 3 (S000070949) in JPMorgan Trust IV run the same collar on
  hedge-period calendars offset by one and two months (497K, verbatim) — a live 3-tranche monthly ladder. Parsed
  their N-PORT (22 quarters each; same 3-leg structure, put strikes 0.947/0.798). Common window 2021-03 → 2026-09:
  fund NAVs differ by 0.98 pp/yr across the three calendars (model 0.75 pp), a real-world instance of RQ1's timing
  luck; our reconstruction tracks each at 0.985–0.987 monthly correlation. `scripts/sister_funds.py`.
* **Annual report (N-CSR FY2020).** Added S5 verbatim quotes: a holdings line "S&P 500 Index 9/30/2020 at USD
  2,930.00, European Style" (confirms European exercise, quarter-end expiry, K1 = 0.945×S — a third source beyond
  N-PORT), and the fund's own "120% of the Benchmark's total return with about 50% of the Benchmark's volatility".
  19 quotes across five filings now verified verbatim by `scripts/extract_sec_quotes.py`.
