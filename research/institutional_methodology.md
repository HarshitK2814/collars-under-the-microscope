# Institutional Methodology — JPMorgan Hedged Equity Fund (Put/Spread Collar overlay)

Quotes below were extracted programmatically on 2026-09-27 by `scripts/extract_sec_quotes.py`, which asserts
that each one appears word for word in the filing text. They are stored in `research/sources/sec_excerpts.json`.
Everything outside quotation marks is our interpretation, labelled as such.

## Sources

| # | Filing | Registrant (CIK) | Accession | Filed | URL |
|---|---|---|---|---|---|
| S1 | Form 497K summary prospectus dated 2025-11-01, **JPMorgan Hedged Equity Fund** (Class R5/R6) | JPMorgan Trust I (1217286) | 0001193125-25-261069 | 2025-11-03 | https://www.sec.gov/Archives/edgar/data/1217286/000119312525261069/d92395d497k.htm |
| S2 | Form 497K supplement dated 2026-02-27, effective 2026-03-01 (U.S. equity funds) | JPMorgan Trust I (1217286) | 0001193125-26-079407 | 2026-02-27 | https://www.sec.gov/Archives/edgar/data/1217286/000119312526079407/d27473d497k.htm |
| S4 | Form 497K summary prospectus dated 2019-11-01, **JPMorgan Hedged Equity Fund** (Class R5/R6) | JPMorgan Trust I (1217286) | 0001193125-19-281595 | 2019-11-01 | https://www.sec.gov/Archives/edgar/data/1217286/000119312519281595/d804276d497k.htm |
| S3 | Form NPORT-P, **JPMorgan Hedged Equity Fund**, period ending 2026-06-30 | JPMorgan Trust I (1217286) | 0002071691-26-021121 | 2026-08-28 | https://www.sec.gov/Archives/edgar/data/1217286/000207169126021121/primary_doc.xml |
| S5 | Form N-CSR, FY ended 2020-06-30, Hedged Equity Fund commentary and holdings | JPMorgan Trust I (1217286) | 0001193125-20-236339 | 2020-08-31 | https://www.sec.gov/Archives/edgar/data/1217286/000119312520236339/d899071dncsr.htm |
| S6 | Form 497K, **Hedged Equity 2 Fund** (Feb–Apr… calendar) | JPMorgan Trust IV (1659326) | 0001193125-25-260252 | 2025-10-31 | https://www.sec.gov/Archives/edgar/data/1659326/000119312525260252/d67952d497k.htm |
| S7 | Form 497K, **Hedged Equity 3 Fund** (Mar–May… calendar) | JPMorgan Trust IV (1659326) | 0001193125-22-270546 | 2022-10-27 | https://www.sec.gov/Archives/edgar/data/1659326/000119312522270546/d394073d497k.htm |

**Sister funds — the manager's own ladder (S6, S7).** Two more funds run the same Put/Spread Collar on staggered calendars:
> Hedged Equity 2: "The quarterly hedge periods are based on returns from the first business day of February through the last business day of April; …"

> Hedged Equity 3: "The quarterly hedge periods are based on returns from the first business day of March through the last business day of May; …"

So the three funds reset one month apart — a live three-tranche monthly ladder of the identical overlay. See `research/posthoc_validation.md`.

**Exercise style and expiry (S5, holdings line).** The FY2020 annual report lists a purchased put as
> "S&P 500 Index 9/30/2020 at USD 2,930.00, European Style"

confirming European exercise (justifying Black-76 European pricing) and a quarter-end expiry; 2930 ÷ the 2020-06-30 close (3100.29) = 0.945, matching the N-PORT strikes. The same report states the fund
> "captured 120% of the Benchmark's total return with about 50% of the Benchmark's volatility …"

## Layer A — Explicitly disclosed (verbatim)

**Structure (S1):**
> "The Fund will also systematically purchase and sell exchange traded put options and sell exchange traded call options, employing an option overlay known as a “Put/Spread Collar” strategy."

> "The Fund constructs a Put/Spread Collar by buying a put option on the S&P 500 Index at a higher strike price and writing (or selling) a put option on the same index at a relatively lower strike price, resulting in what is known as a put option spread, while simultaneously selling a S&P 500 Index call option."

> "The options may be based on the S&P 500 Index or on exchange-traded funds (ETFs) that replicate the S&P 500 Index (S&P 500 ETFs)."

**Strike band and cap (S1):**
> "The put option spread is generally maintained at a level intended to protect the Fund from a decrease in the market of 5% to 20%, with potential upside generally capped at 3.5-5.5%."

> "The upside cap could be more or less depending on market conditions."

> "The premiums received from writing index call options are intended to provide income which substantially offsets the cost of the put option spread,"

**Reset calendar (S1):**
> "The Fund typically holds options for three month periods (each, an “hedge period”) for the purpose of seeking to provide more predictable returns in any market cycle during the applicable hedge period."

> "The quarterly hedge periods are based on returns from the first business day of January through the last business day of March; the first business day of April through the last business day of June; the first business day of July through the last business day of September; and the first business day of October through the last business day of December."

> "The options are systematically reset on at [page break] least a quarterly basis to better capitalize on current market conditions and opportunities while seeking to provide predictable returns in all market cycles."
*(A page number, "2", falls inside this sentence in the filing text; the script checks the two halves separately.)*

> "The Put/Spread Collar strategy is an actively managed process and is designed to provide a continuous market hedge for the portfolio."

> "Options positions are marked to market daily."

**Futures as a substitute (S2, replacing the derivatives paragraph from 2026-03-01):**
> "In addition to the use of the Put/Spread Collar strategy described above, the Fund may use derivatives, primarily futures contracts, to gain exposure to indexes or certain securities within indexes, to more effectively gain targeted equity exposure from its cash positions, and to hedge the Fund’s portfolio if it is unable to purchase or write the necessary options for its overlay strategy."

**How the disclosure changed (S4, 2019):**
> "The put option spread is generally maintained at a level whereby the Fund is protected from a decrease in the market of five to twenty percent."

The 2019 (and 2018) prospectus has **no stated cap range** and **no calendar hedge-period sentence** (the script
checks that "capped at" and "hedge period" are absent). The 3.5–5.5% cap band and the calendar-quarter wording
were added later. So the 2019 caps of 3.1–3.3% (below) are not a disclosure deviation.

## Layer A′ — Reported holdings (S3, N-PORT for the quarter ending 2026-06-30)

| Leg | Written/Purchased | Strike | Expiry | Contracts | Strike ÷ S&P 500 close 2026-03-31 (6528.52) |
|---|---|---|---|---|---|
| Put | Purchased | 6180 | 2026-06-30 | 27,069 | 0.9466 |
| Put | Written | 5210 | 2026-06-30 | 27,069 | 0.7980 |
| Call | Written | 6865 | 2026-06-30 | 27,069 | 1.0515 |

Fund total assets: $20.27bn. Contracts × 100 × 6528.52 ≈ $17.7bn of index notional, about 87% of total assets (our arithmetic).

**What this confirms (our interpretation):** one expiry per leg at the quarter-end; strikes set from the
quarter-start level at almost exactly 95% / 80%; a cap of 5.15%, inside the disclosed 3.5–5.5% range; equal
contract counts on all three legs. The S&P 500 close used is Yahoo `^GSPC`; the exact strike-setting time is not disclosed.

## Layer B — Our reconstruction (not disclosed)

| Choice | Value | Why |
|---|---|---|
| Long put strike | 0.95 × S at reset | "5% to 20%" band; confirmed by S3 (0.9466) |
| Short put strike | 0.80 × S at reset | same; confirmed by S3 (0.7980) |
| Short call strike | solved for zero net premium at mid | "substantially offsets"; the cap is *measured* and compared with 3.5–5.5% |
| Reset day (baseline) | last business day of each calendar quarter, expiry at the next quarter-end | the hedge-period quote; confirmed by S3's 2026-06-30 expiry |
| Instrument | SPX index options (European, cash-settled) | "typically constructs … utilizing index options" |
| Equity sleeve | S&P 500 total return | isolates the overlay; the fund's stock selection is not modelled |
| Hedge ratio | 1.0 contract-notional per unit of equity | S3 shows ~0.87 of total assets; 0.87 is a sensitivity |

## Correction to the specification

The specification (Section 3) said the exact reset timing was "not fully specified". **S1 does specify it**: hedge
periods run from the first to the last business day of each calendar quarter. This changes the framing of RQ1:

* The fund's own calendar is phase φ = 0. It is not an unknown we must guess.
* RQ1 becomes: **how much of the fund-like collar's outcome is due to its choice of the calendar-quarter
  phase, compared with the 62 other possible phases?** The ladder question is unchanged.
* The spec's point about predictability is strengthened: the reset dates are public and fixed.

## Unknowns

Execution time and method on the reset day; whether strikes are rounded to listed increments (S3's strikes are
multiples of 5); SPX vs ETF-option mix over time; the "at least quarterly" clause (intra-quarter resets would
appear as extra expiries in N-PORT); how the call strike is chosen when the zero-cost cap falls outside 3.5–5.5%.
