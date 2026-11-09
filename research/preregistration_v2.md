# Pre-registration v2: Collars Under the Microscope (P2)
Frozen 2026-11-09, before any v2 hypothesis test was run. v1 pre-registration (hash 02978b50f111), its results and its
configs are unchanged. Related published work exists (see research/evidence_v2.md S1: Braun et al. 2023); v2 is a
replication-plus-extensions study, not a first finding.

## Evidence ranking
1. Forward paper tracking from 2026-11 (only unseen data). 2. Development 2011-2016 and validation 2017-2019.
3. 2020-2026 is a seen period (v1 reported it): descriptive only, every table carrying it is labelled
`seen period (v1 reported it)`.

## Timing and costs (apply to everything)
Strikes, fills and the signal at a reset are set at the 16:00 close of the reset day from data up to that close (v1 rule).
Legs expire at the next reset. Every option trade pays a bid-ask haircut (v1: h = surface.yaml half-spread in vol points,
on all legs at the reset). Expiry settlement is cash at intrinsic, no spread. Costs beyond the spread (commissions, market
impact) are omitted and stated as omitted; capacity is a descriptive comparison only. Any Sharpe has a 95% stationary-
bootstrap CI and a reset/day count. Nothing here is investment advice.

## Primary hypotheses
- **H1 (vol input).** Forecast at close t the realised variance of S&P 500 daily log returns over t+1..t+63 trading days.
  Candidate A: (VIX3M/100)^2. Candidate B: mean of the 63-step-ahead GJR-GARCH(1,1,1)-t variance forecast (arch; parameters
  refit every 63 days on all data from 1990 up to the block start, expanding; min 750 obs). Each candidate is multiplied by
  one scale k = mean(realised)/mean(forecast) fitted on development forecast dates whose 63-day label ends by 2016-12-31.
  Evaluate on validation forecast dates whose label ends by 2019-12-31, loss QLIKE = RV/F - ln(RV/F) - 1. Supported
  (GARCH is the better pricer input) if mean(QLIKE_A - QLIKE_B) > 0 with a 95% stationary-bootstrap CI (mean block 63,
  2000 draws, seed 0) excluding 0. Reported either way; the same comparison on the seen period is descriptive.
- **H2 (selection overfit across the family).** Family = 63 reset phases x {fixed 95/80 strikes, vol-unit strikes}
  = 126 single collars, plus the 21 three-tranche ladders (phases phi, phi+21, phi+42) for each strike rule = 42, total 168,
  daily net returns on 2011-01..2019-12. Supported ("choosing the best phase/ladder in sample is overfit") if CSCV PBO
  (16 blocks) > 0.5 AND the deflated Sharpe of the best in-sample member (n_trials 168, sr_var = variance of the 168
  daily Sharpes) < 0.90. Trials are highly dependent, so 168 is conservative; stated.
- **H3 (clustering around resets).** Events: S&P 500 daily return < -2.5 x lagged EWMA sigma (com 60), known at that close.
  Exponential-kernel Hawkes (qcore), refit each January on events strictly before it (first fit once 20 events exist),
  intensity at each reset close d0 uses events strictly before d0. Unit: each (phase, reset) pair with d0 >= 2011-01 and
  expiry <= 2019-12-31 (phases 0..62). y = collar quarterly return minus the beta-matched benchmark quarterly return (v1
  function). Aggregate by d0 date, OLS y ~ intensity + 63-day realised S&P vol at d0, Newey-West 63 lags.
  Supported if the intensity coefficient is positive with NW t > 2. This asks whether reset-day crash clustering
  explains why identical collars differ; descriptive add-on: both-sided events (|r| > 2.5 sigma).

## Descriptive (no hypothesis)
- D1 haircut stress: phase 0 and the 3-tranche ladder (0, 21, 42), fixed strikes, with h in {0, v1, measured real-chain
  half-spread, 2x and 3x measured}; annualised return and cost drag; the std across all 63 phases at v1 h and 2x measured h.
- D2 QuantLib (AnalyticEuropeanEngine) price and Greek cross-check of the Black-76 pricer on a random grid.
- D3 raw SVI fitted to the single real Cboe SPX chain snapshot (2026-12-31 expiry) vs the frozen VIX-based surface.
  The historical surface stays VIX-term-structure based: free data have no historical chains.
- D4 adaptive conformal intervals (alpha 0.1, gamma 0.02, window 8 quarters) on the pricer's call-cap error vs
  disclosed N-PORT strikes for the fund and its two sister funds (all seen period); coverage with a binomial CI.
  Disclosed option values at the period end are expiry-day intrinsic values, so strikes (not values) are the pricer test.
- D5 capacity: fund contracts per leg vs open interest at the nearest listed strikes in the one real chain snapshot.

## Forward test
From 2026-11 scripts/v2/forward.py logs daily returns of the phase-0 collar, the 3-tranche ladder and the JHEQX fund
(price return, dividends not included: stated). Earliest read: 2027-11 (12 months).

## What would change our conclusions
A bug found after freezing is fixed, logged in experiment_log_v2.md, and both numbers reported.
