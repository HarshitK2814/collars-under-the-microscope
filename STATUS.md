# P2 status: Collars Under the Microscope — COMPLETE (2026-09-27)

Headline (locked test 2020–23, indicative because CLLZ tracking error was 3.7%/yr > the 2% threshold):
- Timing luck: the same disclosed rule returned 3.4%–10.7%/yr depending only on the reset day (fund's calendar ranked 21/63).
- H1 partially supported: ladder dispersion ratio 1.73 [1.39, 3.05], ladder − fund −1.45%/yr (p 0.285); robust 1.25–2.13.
- H2 not supported: vol-unit strikes more stable in 16% of phases (76% / 68% in-sample).
- H3 expensive low-beta: Sharpe 0.56 vs 0.51 beta-matched (diff +0.05 [−0.37, 0.40]); CVaR95 5.6% vs 4.3%.
- Pricer: fund's N-PORT caps matched to 0.34 pp over 28 quarters; phase-0 collar vs JHEQX NAV monthly correlation 0.989.
- Post-hoc validation (2026-09-28): frozen surface vs a REAL Cboe SPX chain (free delayed quotes, no WRDS) = 0.71 vol-pt
  error over 388 strikes; manager's sister funds (Hedged Equity 2 & 3) run the same collar on 1-/2-month-offset calendars
  (a live ladder), NAVs 0.98 pp/yr apart, tracked at 0.985–0.987. See `research/posthoc_validation.md`.

## Where things are
- Write-ups: `README.md`, `research/results.md`, `research/limitations.md`, `research/experiment_log.md`,
  `research/preregistration.md` (hash `02978b50f111`; code/config hashes in `research/sources/prereg_freeze_sha256.txt`).
- Figures: `results/figures/`; tables: `results/tables/`; run summaries: `results/runs/summary_*.json`.
- Website: p2 is `status: live` in `website/site.yaml`, with `p2_metrics` + `templates/project_live_p2.html`.
- Résumé text: `../resume/projects_section.md` (P2 first, then P1).

## Not done / optional next
- Published on GitHub (public), 2026-10-13. Committed `research/preregistration.md` first (`prereg: freeze`), then the rest.
- Optional: launch video (no company or personal names), interactive explorer, paper.md.
- Optional: real SPX option chains (WRDS/OptionMetrics) for a Tier-A replication, the most valuable next step.
