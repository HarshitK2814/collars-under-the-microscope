# P2 — Collars Under the Microscope (not started)

Full spec: `research/specification.md`

## Free-data plan (no paid sources)
- Implied vol: Cboe VIX9D / VIX / VIX3M / VIX6M / VIX1Y and SKEW daily history (free downloads from cboe.com).
- Strategy benchmarks for validating the pricer: Cboe CLLZ, CLL, PPUT, BXM, PUT index history (free).
- Underlying: S&P 500 price and total return (Yahoo `^GSPC`, `^SP500TR`); rates from FRED (DTB3).
- Fund tracking: JHEQX NAV (Yahoo) and the fund's N-PORT-P filings on EDGAR (free).
- Consequence: the "Tier B" parametric surface is the main pricer. Real option chains are not used unless you get
  them free through your university (WRDS/OptionMetrics). Every result carries the Tier-B caveat.
- Fallback if Tier-B tracking error to CLLZ is poor: VIX-futures overlay using free Cboe CFE settlement data.
