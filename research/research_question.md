# Research question

A large US mutual fund discloses, in its SEC summary prospectus, a systematic S&P 500 **put-spread collar**:
buy a put about 5% below the market, sell a put about 20% below, and sell a call that pays for the put spread,
reset every calendar quarter (`institutional_methodology.md`). Its N-PORT filings confirm that it does this.

Because the reset calendar is public and fixed, the fund's result in any quarter depends on *where the index
happens to be on the last business day of the quarter*. The same rule run on another day of the quarter would
have set different strikes and earned different returns. That is **reset-timing luck** (Hoffstein, Faber & Braun 2020,
applied here to an option overlay, where strikes are path-dependent).

**RQ1 — timing luck.** Across the 63 possible reset phases (quarter-end + 0…62 trading days), how dispersed are
long-run returns and drawdowns of the collar? Does a three-tranche ladder (phases φ, φ+21, φ+42, each 1/3 notional)
cut that dispersion without costing return?

**RQ2 — strike rule.** Do strikes set in volatility units (a fixed number of ATM standard deviations) give more stable
hedge effectiveness across low / mid / high VIX regimes than fixed percentage strikes?

**RQ3 — value of the hedge.** Compared with a beta-matched S&P 500 + T-bill portfolio (same ex-ante delta at each
reset), does the collar buy tail-risk reduction for the return it gives up, or is it an expensive way to hold
less equity (Israelov & Klein 2016)?

**Primary hypothesis H1.** The cross-phase sd of annualised returns for the single-tranche collar is at least 2×
that of the laddered collar, with no significant difference in mean return (ladder(0,21,42) vs the fund's phase 0).

**Data constraint.** No free SPX option chains, so options are priced with a parametric "Tier-B" surface built from
Cboe VIX-family indices, calibrated on 2011–2016 to four Cboe strategy indices and then frozen. Every result carries
that caveat. Two independent checks of the pricer: tracking error to the Cboe indices out of sample, and the fund's
actual call strikes from N-PORT.
