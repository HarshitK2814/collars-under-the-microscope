# PROJECT 2 — Collars Under the Microscope: Reset Timing Luck, Strike Rules, and the Cost of Predictable Hedging

*Labels:* **[SEC]** explicit · **[Reconstruction]** our implementation choice · **[Extension]** our research addition.

## 1. Institutional Inspiration

| | |
|---|---|
| Institution | J.P. Morgan Asset Management |
| Strategy | JPMorgan Hedged Equity Fund: S&P 500-like equity portfolio + systematic **Put/Spread Collar** |
| Asset class | US large-cap equity + S&P 500 index options |
| SEC filing | Form 497K (summary prospectus dated 2025-11-01), JPMorgan Trust I, CIK 1217286, acc. **0001193125-25-261069**, filed **2025-11-03** |
| URL | https://www.sec.gov/Archives/edgar/data/1217286/000119312525261069/d92395d497k.htm |
| Section | "What are the Fund's main investment strategies?" |
| Amendment | 497K supplement acc. 0001193125-26-079407 (filed 2026-02-27): derivatives paragraph replaced |
| Validation source | Fund Form **N-PORT-P** holdings (option positions); verify fields in Week 1 |
| Index-provider methodology (not SEC) | Cboe CLLZ: https://cdn.cboe.com/api/global/us_indices/governance/Cboe_Zero-Cost_Put_Spread_Collar_Indices_Methodology.pdf |

## 2. Why This Methodology Matters

The JPMorgan Hedged Equity complex runs one of the largest **systematic, calendar-driven** index-option overlays in the market. Market commentary widely attributes quarter-end SPX flows and dealer-gamma effects to its resets; treat that commentary as secondary sources only. The overlay is interesting quantitatively because it is:

* **Fully rule-based at the level of structure:** long put, short lower put, short call, fixed reset calendar.
* **A bundle of three separately priced risk premia:** it buys downside convexity in the 95–80% band, sells convexity beyond −20% and sells upside convexity.
* **Path-dependent:** the outcome depends heavily on *where* the index sits relative to strikes when the calendar says "reset".

This makes it a good vehicle for learning option pricing, surfaces, Greeks and the variance risk premium on a strategy that actually exists.

## 3. What the SEC Actually Says

**Explicit [SEC]**
* Hedge via a Put/Spread Collar: buy a higher-strike put, write a lower-strike put, and simultaneously sell a call.
* The put spread is generally maintained to protect against market declines of **5% to 20%**.
* Upside is generally capped at **3.5–5.5%**, with flexibility based on conditions.
* Options are systematically reset **at least quarterly**.
* Uses exchange-traded options on the S&P 500 Index or S&P 500 ETFs; the call premium offsets the cost of the put spread.
* Equity sleeve: research-based stock selection (not our focus).

**Reconstruction [Reconstruction]**
* Long put strike $K_1 = 0.95\,S_0$ and short put $K_2 = 0.80\,S_0$, from the "5% to 20%" protection band.
* Call strike $K_c$ solved so that the collar costs zero at mid prices. The implied cap is then *measured*, not assumed, and checked against the 3.5–5.5% disclosure.
* Expiry at the next calendar quarter-end (≈ 3 months); resets on the last trading day of each quarter. **"At least quarterly" and the exact reset timing are not fully specified**, so the reset day is a parameter we study.
* Equity sleeve = S&P 500 total return. This isolates the overlay.

**Extension [Extension]:** timing-luck measurement, laddering, volatility-scaled strikes, a VRP decomposition, and a beta-matched evaluation.

**Unknown:** the exact strike choice within the ranges, execution method and time, contract mix (SPX vs ETF options), partial resets, and the equity model.

## 4. Research Question

> **RQ1 (timing luck).** For a JHEQX-style quarterly collar, how much of long-run performance and drawdown is explained by the *arbitrary choice of reset day*? Does a **laddered** implementation (three monthly-staggered tranches of 3-month collars) reduce that dispersion without lowering expected return?
>
> **RQ2 (strike rule).** Does setting strikes in **volatility units** (fixed standardised moneyness) instead of fixed percentage moneyness give more stable hedge effectiveness across volatility regimes?
>
> **RQ3 (value of the collar).** Relative to a **beta-matched** static S&P 500 + T-bill portfolio, does the collar improve tail risk per unit of return given up, or does it just deliver a lower-beta equity exposure expensively (Israelov & Klein 2016)?

**Primary hypothesis (H1):** The cross-phase standard deviation of annualised returns for the single-tranche collar is at least 2× that of the laddered collar, with no significant difference in mean return.

## 5. End-to-End Workflow

```
SPX, SPX TR, dividends yield, T-bill/OIS curve
  + implied vol data (Tier A: EOD option chains; Tier B: VIX-family term structure + skew model)
  ↓ Cleaning: remove crossed/zero-bid quotes, stale strikes; forward from put–call parity (Tier A)
  ↓ Surface: per-expiry SVI fit (Tier A) or parametric surface (Tier B) with no-arbitrage checks
  ↓ Reset engine: at reset date t0, compute K1, K2 and solve Kc for zero cost
  ↓ Daily mark-to-market of the 3 legs; Greeks
  ↓ Execution: fills at mid ± half-spread (in vol points); costs recorded per leg
  ↓ Strategy variants: phase φ = 0…62, ladder, vol-scaled strikes
  ↓ Benchmarks: SPX TR; beta-matched SPX/T-bills; Cboe CLL/CLLZ/PPUT; JHEQX NAV (tracking)
  ↓ P&L attribution (Δ, Γ, ν, Θ, residual)
  ↓ Risk: CVaR, drawdown, up/down capture, skew
  ↓ Statistical validation (bootstrap of paths, Sharpe/CVaR differences)
  ↓ Recent/live: quarterly paper resets, compared with the fund's actual reported strikes (N-PORT)
```

**Bar convention:** strikes are computed from the **15:45 ET or 16:00 close** of reset day t0, using the surface built from that same bar's quotes (Tier A EOD quotes at 15:45 avoid the close-auction mismatch). Tier B uses end-of-day VIX-family closes. **Mark-to-market uses the same-day close; no future quotes are used.**

## 6. Mathematical Formulation

**Forward and pricing (Black-76 on the forward).** $r$ and $q$ are the risk-free rate and dividend yield, and $\tau$ is time to expiry:
$$
F_{t}=S_t e^{(r_t-q_t)\tau},\qquad
P(K,\tau)=e^{-r\tau}\big[K\Phi(-d_2)-F\Phi(-d_1)\big],\quad
C(K,\tau)=e^{-r\tau}\big[F\Phi(d_1)-K\Phi(d_2)\big]
$$
$$
d_{1,2}=\frac{\ln(F/K)\pm\tfrac12\sigma^2(k,\tau)\tau}{\sigma(k,\tau)\sqrt\tau},\qquad k=\ln(K/F)
$$

**Collar at reset $t_0$** (fixed-moneyness rule, $m_1=0.95$, $m_2=0.80$):
$$
K_1=m_1S_{t_0},\quad K_2=m_2S_{t_0},\quad K_c:\ C(K_c)=P(K_1)-P(K_2)\ \ (\text{solve by Brent's method on }K_c>F)
$$
Implied cap: $\text{cap}=K_c/S_{t_0}-1$. **Check:** its time-series distribution should mostly lie in 3.5–5.5%. If not, that measures how far the reconstruction deviates from the disclosure.

**Value of hedged unit** (one index unit, dividends reinvested in the equity sleeve):
$$
V_t=S^{TR}_t/S^{TR}_{t_0}\cdot S_{t_0}+P_t(K_1)-P_t(K_2)-C_t(K_c)
$$
**Payoff at expiry $T$:**
$$
\Pi_T=(K_1-S_T)^+-(K_2-S_T)^+-(S_T-K_c)^+
$$

**Vol-scaled strike rule (RQ2).** $\sigma_{ATM}$ is the ATM implied vol for $\tau$:
$$
K_j=F_{t_0}\exp\!\big(-z_j\,\sigma_{ATM,t_0}\sqrt{\tau}\big),\quad j\in\{1,2\}
$$
$z_1, z_2$ are **calibrated on the development period only**, so that the average moneyness equals 0.95 and 0.80. This makes the comparison with fixed-moneyness fair on average.

**Phase (timing-luck) family.** A reset calendar offset by φ trading days from quarter-end gives strategy value $V^{(\varphi)}_t$, $\varphi=0,\dots,62$. Timing-luck dispersion:
$$
\mathrm{TL}=\operatorname{sd}_{\varphi}\big(\bar R^{(\varphi)}\big),\qquad \bar R^{(\varphi)}=\text{annualised return of phase }\varphi
$$
**Ladder:** three tranches with phases 0, 21, 42 days, each holding 1/3 notional of a 3-month collar:
$$
V^{L}_t=\tfrac13\sum_{j\in\{0,21,42\}}V^{(\varphi_j)}_t
$$

**Beta-matched benchmark (no look-ahead).** At each reset the overlay's **ex-ante** delta is
$$
\beta^{ex}_{t_0}=1+\Delta_P(K_1)-\Delta_P(K_2)-\Delta_C(K_c)
$$
using $\Delta_P<0$ conventions. Then $B_t = \beta^{ex}_{t_0}\cdot$ SPX-TR $+(1-\beta^{ex}_{t_0})\cdot$ T-bill, held to the next reset.

**P&L attribution (daily).** For each leg:
$$
dV\approx\Delta\,dS+\tfrac12\Gamma\,dS^2+\nu\,d\sigma+\Theta\,dt+\varepsilon
$$
Aggregate over legs and quarters. The *volatility risk premium* channel is the sign of $\sum \tfrac12\Gamma S^2(\sigma_{real}^2-\sigma_{impl}^2)dt$ for each leg.

**Costs.** Half-spread expressed in implied-vol points $h$ (baseline 0.5 vol pt for SPX 3-month OTM; sensitivity 0.25/1.0):
$$
\text{cost per leg}=|\nu|\cdot h\cdot n_{\text{contracts}}
$$
Charged at each open and close. Tier A replaces this with actual quoted half-spreads.

**Tail metrics.** $\mathrm{CVaR}_{95}$ of monthly returns, max drawdown. *Protection efficiency:*
$$
\mathrm{PE}=\frac{\mathrm{CVaR}_{95}(B)-\mathrm{CVaR}_{95}(V)}{\max\{\bar R_B-\bar R_V,\ \epsilon\}}
$$
(CVaR taken as a positive loss number; reported with the numerator and denominator separately to avoid a misleading ratio.)

## 7. Data Requirements

| Need | Tier A (real options) | Tier B (free) | Notes |
|---|---|---|---|
| SPX EOD option chains | OptionMetrics IvyDB (WRDS, many universities) or Cboe DataShop purchase (SPX EOD subset) | — | Tier A is strongly preferred. **Decide by end of Week 2.** |
| Implied vol term structure | From chains | Cboe **VIX9D, VIX, VIX3M, VIX6M, VIX1Y** daily history (free, cboe.com) | VIX-family indices are **variance-swap** vols, not ATM vols; convert with a skew adjustment (below) |
| Skew | From chains | Cboe **SKEW** index (free) + a calibrated parametric slope | Crude; **validated against Cboe strategy indices** |
| Strategy benchmarks | — | Cboe **CLL, CLLZ, PPUT, BXM, PUT** daily history (free) | Doubles as a test of the Tier B pricer: re-price CLLZ's rules and measure tracking error |
| Underlying | — | S&P 500 price and TR (free, e.g. FRED SP500 for recent years; Yahoo ^GSPC/^SP500TR) | |
| Rates / dividends | — | FRED T-bill (DTB3), SOFR; dividend yield implied from futures or trailing | |
| Fund data | — | JHEQX daily NAV (Yahoo), **N-PORT-P** filings on EDGAR | NAV includes stock selection and fees; used for *tracking*, not as ground truth |
| Fallback project data | — | Cboe CFE **VIX futures** daily settlements per contract (free) | If Tier A unavailable and Tier B tracking error to CLLZ is poor: pivot to a VIX-futures hedge-overlay variant (candidate C6) |

**Tier B surface.** For maturity τ, estimate an ATM vol $\sigma_{ATM}(\tau)=\text{VIX}_\tau - \kappa_\tau$, where $\kappa_\tau$ captures the variance-swap-over-ATM premium. Use a quadratic smile in $k/\sqrt\tau$:
$$
\sigma(k,\tau)=\sigma_{ATM}(\tau)+a_\tau\,\frac{k}{\sqrt\tau}+b_\tau\Big(\frac{k}{\sqrt\tau}\Big)^2
$$
Calibrate $(\kappa,a,b)$ **on the development period** so the model reproduces CLLZ/PPUT/CLL monthly returns, then **freeze** them. Report tracking error to these indices on the validation and test periods. **Honest status:** this is an approximation. Any Tier-B result must carry this caveat.

**Period.** Tier B: 2011–latest (VIX3M/VIX6M availability; confirm start dates). Tier A: 1996–latest (OptionMetrics). JHEQX NAV: 2013–latest.

## 8. Feature Engineering

* Forward $F$: Tier A from put–call parity on the two strikes nearest ATM; Tier B from $S e^{(r-q)\tau}$.
* $\sigma_{ATM}(\tau)$ for τ = 3 months, interpolated in total variance $\sigma^2\tau$ (linear in τ) between the bracketing expiries or VIX tenors.
* SVI (Tier A) per expiry: $w(k)=a+b\{\rho(k-m)+\sqrt{(k-m)^2+s^2}\}$, fitted by weighted least squares on OTM mids. Check the butterfly condition (the density must be non-negative) and calendar monotonicity of total variance.
* Realised vol: 21-day and 63-day close-to-close; Yang–Zhang if you have OHLC.
* Vol regime state for reporting: VIX tercile, computed with an expanding window up to t (no look-ahead).
* Missing quotes: skip strikes with zero bid. If the target strike is missing, use the nearest listed strike (Tier A); this is a real-world constraint.

## 9. Model Architecture

* **Pricing:** Black-76 + SVI (Tier A) / parametric surface (Tier B). A stochastic-vol model (Heston) is **not** needed for the research question. Add it only as an appendix for dynamics (e.g. vega–spot correlation).
* **Strategy engine:** a deterministic, event-driven backtester with daily MTM.
* **No ML.** The questions are about design choices of a rule-based overlay.

## 10. Portfolio Construction

* Notional hedge ratio 1.0 (the fund hedges the equity sleeve). Sensitivity 0.8.
* Ladder: 3 tranches × 1/3 notional. Alternative: 12 weekly tranches (appendix).
* No leverage. Cash from net premia goes to T-bills.
* Roll rule: close legs at the next reset (no early exercise; SPX options are European).
* Constraint check: implied cap must lie within [3.5%, 5.5%]. If outside, record a "disclosure-inconsistent" flag. Never silently re-solve.

## 11. Risk Management

Daily and monthly returns; vol; Sharpe (CI); Sortino; max DD; monthly CVaR 95/99; skewness and kurtosis; **up- and down-capture ratios** vs SPX; realised beta; **gamma exposure profile** at each reset (for the market-impact discussion); stress episodes: Aug 2015, Feb 2018 (Volmageddon), Q4 2018, Feb–Mar 2020, 2022, Apr 2025 tariff shock, latest.

## 12. Backtesting Methodology

* Splits (Tier B): development 2011–2016 · validation 2017–2019 · **test 2020–2023** (includes COVID and 2022) · recent 2024–latest. Tier A adds 1996–2010 to development.
* **Everything estimated** (Tier B surface parameters, $z_j$ for vol-scaled strikes, spread parameter) is fitted on development only.
* Timing-luck experiments run all 63 phases. **No phase may be "selected".** Report the full distribution.
* Costs as in Section 6. Report gross and net.
* Survivorship is not an issue (index). Stale quotes are an issue (Tier A): use 15:45 snapshots where available.

## 13. Benchmark Strategies

1. SPX total return (buy-and-hold).
2. **Beta-matched SPX + T-bills** (Section 6). *The key, non-weak benchmark.*
3. Cboe **CLLZ** (monthly 2.5%/5% put spread, zero cost) and **CLL** (95–110 collar).
4. **PPUT** (5% OTM monthly protective put).
5. Actual **JHEQX** NAV total return (tracking comparison only; includes stock selection and fees).

## 14. Ablation Study

Full collar vs: without the short lower put (a classic collar, "full protection") · without the short call (a put spread only, net debit) · without the long put (short-vol only: short put + short call) · monthly vs quarterly reset · fixed vs vol-scaled strikes · single tranche vs ladder.

## 15. Robustness Testing

Moneyness grid (m1 ∈ {0.93, 0.95, 0.97}, m2 ∈ {0.75, 0.80, 0.85}) · reset frequency · hedge ratio · spread assumptions (0.25/0.5/1 vol pt) · Tier A vs Tier B pricer (on the overlap) · subperiods by VIX regime · excluding 2020 · starting-date bootstrap.

## 16. Statistical Validation

| Test | Why |
|---|---|
| Distribution across 63 phases (not a p-value) | The phases *are* the object of RQ1; report the range, IQR and sd |
| F-test / Levene on the variance of phase returns (single vs ladder) + bootstrap CI of the sd ratio | H1 is a *dispersion* claim |
| Stationary bootstrap (block ≈ one quarter) for the Sharpe and CVaR differences vs the beta-matched benchmark | Path-dependent, overlapping, non-normal returns |
| Ledoit–Wolf Sharpe-difference test | Collar vs beta-matched benchmark |
| Regression of collar excess returns on SPX excess returns and ΔVIX | Separates delta exposure from vol exposure |
| Diebold–Mariano on hedge error (loss = squared tracking error of reconstruction vs CLLZ) | Compares Tier B pricer variants as forecasts of index returns |

## 17. Research Extension [Extension]

1. **Timing-luck quantification + laddering** (RQ1). Hoffstein, Faber & Braun (2020) introduced "rebalance timing luck" for smart-beta rebalancing. We apply the concept to an *option overlay*, where path dependence is sharper (strikes are set at the reset).
2. **Vol-unit strikes** (RQ2).
3. **VRP decomposition:** which leg earns or pays the variance risk premium? Hypothesis: the short call and short 80% put *earn* VRP, and the long 95% put *pays* skew premium.
4. **Recent-period test:** the 2025 tariff-shock drawdown and the rebound give a natural out-of-sample stress. Paper resets continue quarterly.
5. **(Optional) N-PORT forensic validation:** compare our reconstructed $K_1, K_2, K_c$ with actual reported fund positions per quarter. That gives a measured deviation between "disclosed rule" and "actual implementation".

## 18. Expected Research Contribution

An open, reproducible measurement of **how much reset-date choice matters for a real, disclosed, large systematic collar**, and whether laddering or vol-scaled strikes remove it, judged against the correct beta-matched benchmark. Novelty confidence: **extension of existing literature** (timing luck applied to option overlays; Israelov–Klein's benchmark critique applied to the put-spread-collar variant).

## 19. Failure Modes

* Tier-B surface error dominates the signal (monitor CLLZ tracking error; if > ~2%/yr, results are only indicative).
* Discrete strikes and liquidity: real strikes are listed at 5/25-point increments. Rounding matters at the tails.
* Early assignment is not an issue for SPX (European), but **is** for ETF (SPY) options if the fund uses them.
* A regime where the collar is always "wrong": a sharp V-shaped rally right after a crash, with the cap binding at the bottom.
* Overinterpreting a single crash (2020) as evidence: report the results with and without it.

## 20. Resume Version

**Collars Under the Microscope: Timing Luck and Strike Design in a Systematic Put-Spread Collar** *(inspired by the JPMorgan Hedged Equity Fund's SEC-disclosed overlay)*
* Rebuilt an SEC-disclosed S&P 500 put-spread collar (95/80 put spread financed by a short call, quarterly reset) with an SVI implied-volatility surface, daily Greeks, and delta–gamma–vega–theta P&L attribution over `[years]`.
* Quantified reset-date "timing luck" across 63 reset phases: annualised return range `[x]` bp and max-DD range `[y]`. A 3-tranche ladder cut dispersion by `[z]%` (bootstrap CI `[a, b]`).
* Compared against a beta-matched S&P 500/T-bill benchmark and Cboe collar indices: tail-loss reduction (CVaR95) of `[c]` for `[d]` bp/yr of forgone return, net of `[h]` vol-point spreads.

---

### Phase 6 — Recent Research Connection

| | |
|---|---|
| A. Historical methodology | Put/spread collar, 5–20% protection band, 3.5–5.5% cap, quarterly reset (497K 2025) |
| B. Recent research | Cboe CLLZ index methodology (zero-cost put-spread collar, monthly). Israelov & Klein (2016, *J. Alternative Investments*, AQR): collars vs beta-matched equity. Israelov (2019, "Pathetic Protection", *JAI*): protective puts rarely beat beta-matched alternatives. Industry commentary (2025–26) on quarter-end collar flows and dealer gamma: **secondary sources, cite only as motivation** |
| C. What changed | The literature moved from "do puts protect?" to "protection per unit of forgone return vs beta-matched". Market-structure attention to the calendar predictability of large overlays |
| D. Our implementation | Beta-matched evaluation, ladder, vol-scaled strikes |
| E. Gap | Timing luck in large *calendar-driven* option overlays, and laddering as a remedy, quantified on a disclosed structure |

### Prior-art table

| Paper / Institution | Method | Dataset | Main finding | How we differ |
|---|---|---|---|---|
| Whaley (2002, *J. Derivatives*) | BXM buy-write index | SPX options | Buy-write had equity-like return at lower vol | Different structure (collar); timing luck |
| Israelov & Klein (2016, *JAI*), AQR | Collar vs beta-matched portfolio | SPX options | Collars underperform beta-matched equity on risk-adjusted terms | Put-*spread* collar; reset-phase distribution |
| Israelov (2019, *JAI*) | Protective puts | SPX options | Protection expensive vs beta reduction | We test vol-unit strikes and laddering |
| Hoffstein, Faber & Braun (2020, SSRN) | Rebalance timing luck | Smart-beta portfolios | Large dispersion from rebalance-date choice | Applied to an option overlay |
| Cboe CLLZ methodology | Zero-cost put-spread collar, monthly | SPX | Benchmark index | Quarterly, JHEQX-like strikes; used to validate our pricer |
| Carr & Wu (2009, *RFS*) | Variance risk premium | Index options | VRP strongly negative for index | Leg-level VRP attribution in the collar |
| Gatheral & Jacquier (2014, *Quant. Finance*) | Arbitrage-free SVI | — | Surface parametrisation | Our Tier-A surface |

### Pre-registration

| Item | Value |
|---|---|
| Primary metric | sd across phases of annualised net return (single vs ladder); secondary: CVaR95 and Sharpe vs beta-matched benchmark |
| Benchmark | Beta-matched SPX/T-bill |
| Period | Test 2020-01 → 2023-12; recent 2024 → latest reported separately |
| Test | Bootstrap CI of the sd ratio; Ledoit–Wolf |
| Robustness | Moneyness grid, spreads, Tier A vs B |
| Failure | H1 fails if the sd-ratio CI includes 1 or the ladder mean return is lower with p < 0.05 |

### "Unusual result" candidates
* The **short 80% put** may contribute most of the long-run *positive* P&L (it harvests crash-skew premium), making the "hedged" fund partly a skew seller.
* The ladder could reduce dispersion but **increase** average cap binding, trading timing luck for a higher expected opportunity cost.

### Paper-trading component
At each quarter-end: record our reconstructed strikes and premia (committed to git before the next open). Mark daily. After the fund's N-PORT is public (~60 days after quarter-end), log the deviation between our strikes and reported strikes. *Simulated; no real options traded.*
