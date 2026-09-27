# P2 status: Collars Under the Microscope (NEXT, not started)

- Spec: `research/specification.md` (RQ1 reset-timing luck and laddering; RQ2 volatility-unit strikes).
- Free-data plan: see `README.md` (Cboe VIX-term/SKEW and strategy indices, Yahoo S&P 500, FRED rates, fund NAV + N-PORT).
- Main constraint: no free option chains, so the Tier-B parametric vol surface is the main pricer, validated against Cboe CLLZ.

## Start here (reuse the P1 discipline)
1. Scaffold like P1: `src/`, `scripts/run.py`, `research/` (institutional_methodology, research_question, experiment_log,
   preregistration), `results/`, git repo, and a `qcore` test-period lock (`PREREG_HASH`).
2. Week-1 job: verify the SEC filing quotes word for word and record the accession numbers.
3. Download the free data, build the Black-76 + Tier-B surface, and check tracking error against CLLZ before any research run.
4. Freeze the pre-registration before opening the test period.
5. When results exist: set `status: live` for p2 in the programme website config (`website/site.yaml`) and add a metrics function in the website builder.
