# Experiment log v2 (append-only)

Development = 2011-2016, validation = 2017-2019. 2020-2026 is a seen period (v1 reported it).

| ID | Date | Period | What changed | Why | Result |
|---|---|---|---|---|---|
| EXP-V2-000 | 2026-11-09 | - | Evidence file read; prereg v2 written and frozen before any v2 test. qcore vendor diff vs root checked: only `Splits.forward` differs (root superset), so P2 added to tools/vendor_sync.py and synced | plan 09 | Hash recorded in the freeze commit message |
| EXP-V2-001 | 2026-11-09 | dev 2011-16 fit, val 2017-19 eval, seen 2020+ | H1 GJR-GARCH(1,1,1)-t vs VIX3M vs VIX forecasting next-63d realised variance; scales fitted on dev (label end <= 2016-12-31); run with PREREG_HASH=11f656cd0a6f | prereg H1 | H1 NOT SUPPORTED. Validation QLIKE: VIX3M 0.327, VIX 0.382, GARCH 0.409; VIX3M minus GARCH -0.083 [-0.127, -0.043]. Seen period: -0.011 [-0.086, 0.063] (indistinguishable). Files: results/v2/tables/h1_vol.json |
| EXP-V2-002 | 2026-11-09 | 2011-2019 | H2 168-member family (63 phases x {fixed, vol strikes} + 42 ladders), CSCV 16 blocks, DSR n_trials 168 | prereg H2 | H2 NOT SUPPORTED. PBO 0.384, DSR of best (vol_phase50, Sharpe 1.12 [0.50, 1.72]) 0.993. v1 baseline phase 0 ranks 14 of 168. Files: h2_family.json, h2_family_sharpe.csv |
| EXP-V2-003 | 2026-11-09 | 2011-2019 | H3 Hawkes intensity at reset (past events only, yearly refit) vs collar-minus-beta-matched quarterly return, 63 phases, NW 63 lags | prereg H3 | H3 NOT SUPPORTED. Intensity coef 0.040, t 0.68 (136 down events 1990-2019); both-sided events t 0.85. Files: h3_hawkes.json |
| EXP-V2-004 | 2026-11-09 | dev+val and seen | D1/D2/D3/D5 pricing checks. First run used 2x/3x of the measured chain spread; the chain spread (0.039 vol pts) is far below v1 h (0.464), so the stress grid was changed to 2x/4x v1 h BEFORE reading results, rerun | descriptive | QuantLib max abs error < 1e-13. See pricing_checks.json, haircut_stress.csv |
| EXP-V2-005 | 2026-11-09 | seen | D4 ACI conformal on call-cap error vs N-PORT (3 funds), alpha 0.1, window 8 | descriptive | Pooled coverage 0.896 over 48 scored quarters. conformal_nport.json |
| EXP-V2-006 | 2026-11-09 | forward | forward.py --refresh re-downloaded Cboe/FRED/Yahoo; market panel now ends 2026-11-09 (VIX of the last day carried forward as stale). Hypothesis scripts H1-H3 and pricing checks ran BEFORE this refresh; their dev/val numbers cannot change (data only appended) but seen-period rows end 2026-09-25 | operations | 6 forward days logged |
