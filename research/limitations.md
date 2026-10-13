# Limitations

1. **No real option quotes (Tier B).** Prices come from a four-parameter surface on VIX-family indices. It tracked the
   Cboe indices within 0.6–1.5%/yr outside 2020–23 but 1.8–3.7%/yr in the test period, above the pre-registered 2%
   threshold for CLLZ. Test results are therefore labelled indicative. The surface has one skew and one curvature
   number for all dates and tenors; real skew moves with the market.
2. **Hypothetical expiries.** Phase φ ≠ 0 assumes an SPX option expiring exactly on the next reset day. Daily SPX
   expiries exist only since 2022; earlier, a phase would have used the nearest weekly or monthly expiry. Phase 0
   (quarter-end) always had listed expiries.
3. **Costs.** One effective half-spread (0.46 vol pt) fitted to 1-month Cboe indices is applied to 3-month options.
   No market impact. The ratio in H1 is insensitive to h (0.25–1.0 vol pt), but return levels are not.
4. **Strike-setting time.** Strikes use the 16:00 close. The fund's long put sits at ~0.945 × the close, not 0.95,
   which suggests a different reference price or rule; 0.945 is in the robustness grid.
5. **Equity sleeve.** The S&P 500 total return stands in for the fund's stock selection; the fund NAV also carries fees.
   The JHEQX comparison is for tracking only.
6. **Short samples.** The test window has 16 quarterly resets; Sharpe CIs are wide (about ±1). Timing-luck dispersion is
   measured on overlapping phases of the same path, so the 63 phases are not 63 independent experiments; the
   bootstrap resamples days jointly across all phases to respect that.
7. **RQ2's regime measure** uses expanding VIX terciles since 1990; in calm periods some regimes have few days and are
   skipped. The comparison is descriptive.
8. **Beta-matched benchmark** uses the model delta at each reset. A delta from a different surface would shift it.
9. **Look-ahead that did happen:** the fund's 2026-06-30 N-PORT strikes were viewed before the lock was applied to
   N-PORT data (logged). No parameter was fitted to them.
10. **Not live trading.** No real options were traded; this is a research reconstruction, not investment advice.
