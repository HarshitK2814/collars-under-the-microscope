# P2 evidence for v2 (put-spread collars)

Checked 2026-11-09 by web search; search-result summaries were read, full papers were NOT all opened (stated per row). Fund filing language (497K, supplement) was verified verbatim in v1 (`research/sources/sec_excerpts.json`).

## Sources

| # | Source | Type | What it says (as far as read) | Link |
|---|---|---|---|---|
| S1 | Braun, Hoffstein, Israelov, Nze Ndong (2023), "The Hidden Cost in Costless Put-Spread Collars: Rebalance Timing Luck" | Practitioner paper (Newfound / Mathematica) | **Prior art for our headline.** Same three-month put-spread collar, differing only in rebalance date; reported tracking error between implementations above 400 bp/yr and a roughly 40% wealth gap over 15 years (from slides/summaries; full text not read). Recommends tranching. | [Newfound](https://blog.thinknewfound.com/2023/01/the-hidden-cost-in-costless-put-spread-collars-rebalance-timing-luck/), [CXO](https://cxoadvisory.com/equity-options/sensitivity-of-put-spread-collar-performance-to-rebalancing-schedule) |
| S2 | Newfound, "Rebalance Timing Luck" research page (Hoffstein, Sibears, Faber) | Practitioner | Equal-weighting N staggered sub-portfolios cuts timing luck by about 1/N (theory behind our ladder). | [page](https://www.thinknewfound.com/rebalance-timing-luck) |
| S3 | Simplify, "Improving Hedged Equity: Short-Dated Ladder" | Fund-sponsor blog (commercial interest) | Laddered monthly collars were never best or worst in any year versus annual/quarterly/monthly resets. | [blog](https://simplify.us/blog/improving-hedged-equity-short-dated-ladder) |
| S4 | Cboe Insights, "Benchmark Indices Series: Hedging Downside Exposure with PPUT, CLL and CLLZ" | Index-provider note | CLLZ: long S&P exposure, monthly 2.5%-5% put spread, short monthly OTM call funding it; launched 2015. Our v1 pricer is checked against CLLZ. | [Cboe](https://www.cboe.com/insights/posts/benchmark-indices-series-hedging-downside-exposure-with-pput-cll-and-cllz-indices) |
| S5 | Cboe, "A hypothetical look at 35 years of indexes that buy SPX options" (Indexology) | Index-provider note | Context for index-style option strategies and their cost drag (summary only). | [Indexology](https://www.indexologyblog.com/2021/07/27/a-hypothetical-look-at-35-years-of-indexes-that-buy-spx-options/) |
| S6 | Bosun Options Solutions PM piece (CAIA host) | Practitioner | Because options expire, price-move timing is critical; advises overlapping tranches. | [CAIA](https://caia.org/node/7256) |
| S7 | SpotGamma / Hypercall / Substack explainers on the "JPM collar" | Vendor and blogger posts | Claim the quarter-end reset pins or moves the market via dealer hedging. Causal claims are the authors' interpretation, not established. We treat them only as a hypothesis for the Hawkes test (H3). | [SpotGamma](https://spotgamma.com/jpm-collar-explained/), [Hypercall](https://docs.hypercall.xyz/insights/jpm-collar-q1-2026) |
| S8 | JHEQX 497K and 2026-02-27 supplement (v1) | SEC filing | Hedge periods are calendar quarters; strikes about 5% and 20% below, call set for zero cost; sister funds run offset calendars. | `research/sources/sec_excerpts.json` |
| S9 | Press coverage of 2022 (JPM funds, law.com / Bloomberg syndication) | News | Sister funds with different reset dates differed by several points in 2022 (one about -18%, flagship about -12%). | [law.com](https://law.com/dailybusinessreview/2021/11/22/jpmorgans-options-whale-gets-etf-copycat-as-hedging-booms) |

**Gaps (stated, not hidden).** No Reddit or Quant StackExchange thread surfaced in search; no forum claim is used. The Cboe CLLZ methodology PDF is already in `data/raw/cllz_methodology.pdf` (v1). Full text of S1 was not retrieved, so its exact method and numbers are not compared line by line.

## Honest consequence for novelty
Reset-day timing luck in costless put-spread collars is **already published (S1)**. Our contribution is narrower: a free-data replication on one named fund family (63 phases, the fund's own N-PORT strikes, sister-fund calendars) and the v2 tests below. README must say so.

## What industry does that v1 does not

1. Tranching/laddering as the standard answer (S1-S3, S6): v1 already tests ladders; v2 audits whether ladder/phase choices survive selection (DSR/PBO).
2. Dealer-hedging claim about reset days (S7): untested; v2 H3 tests a clustering version using only past data.
3. Vol input: v1 uses VIX-family; practitioners also use model forecasts. v2 H1 tests GJR-GARCH vs VIX3M.
4. Execution: SPX options are paid at a bid-ask; v1 used one fitted half-spread. v2 uses the measured half-spread of a real chain and stresses it.

## v2 decisions

| # | Decision | Tag | Feeds |
|---|---|---|---|
| D1 | State S1 as prior art in README; reframe as replication plus extensions | **fix** | README |
| D2 | H3 tests the dealer/clustering story with past-only events | **copy** (S7 as hypothesis) | prereg H3 |
| D3 | Haircut stress on every option trade: v1 h, real-chain half-spread, 2x, 3x | **fix** | pricing_checks |
| D4 | Ladder/phase family audited with DSR/PBO | **fix** | prereg H2 |
| D5 | Historical surface stays VIX-term-structure based (free data has no historical chains); SVI fitted only to the one real Cboe snapshot, as a cross-check | **copy** | pricing_checks |
