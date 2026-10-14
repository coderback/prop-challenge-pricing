# Paper 2 contract map: results (2026-10-13)

- Pre-registration: a102df4, pushed before the run. Run: `research/run_K.py`; logs in `data/logs/run_K_*.log`;
  tables in `data/checks/` (`K1_map.csv`, `K2_rules.csv`, `K3_*.csv`, `K_robustness.csv`, `X1_claim_exclusion.csv`).
- Rules as read at source on the same day: `research/RULES_alpha_swing_2026-10-13.md`.
- All values are expected payouts per purchase of a $10k Alpha Swing evaluation within 36 months (V). EV = V − fee.
- These are **model values if the firm pays every valid request**. The behaviour that creates them is on Alpha's
  published list of triggers for restrictions and for removing profits. Nothing here is a recommendation to buy.

## Verdicts
| | Hypothesis (FTG regime, evaluation set) | Estimate (95% interval) | Verdict | Robust? |
|---|---|---|---|---|
| H1 | Coin-flip buyer: V above $40 and below $147 | V = $103 ($100 to $106) | **SUPPORTED** | No: $148 ($143 to $152) in the STD regime |
| H2 | Sizing gain exceeds the gain from a Sharpe of 0.3 | $70 against $182; D = −$112 (−$117 to −$107) | **REFUTED** | Yes, every row |
| H3 | A Sharpe of 0.3 leaves V below $147 | V = $285 ($281 to $290) | **REFUTED** | Yes, every row |

**The thesis the plan was built on is wrong for this contract.** Value rises steadily with skill, and a
research-grade edge would be worth more than getting the sizing right. What survives is narrower: without skill
the fee decides the sign, sizing still triples the value, and the programme found no edge to bring.

| Robustness row (FTG unless stated) | V coin | V coin at 1%/1% | V at S = 0.3 | D |
|---|---|---|---|---|
| Primary | $103 | $33 | $285 | −$112 |
| 1. STD regime, its own selected policy | $148 | $35 | $405 | −$144 |
| 2. Block bootstrap of days (21-day blocks) | $110 | $34 | $296 | −$110 |
| 3. Purchases 2005-02 → 2014-02 | $115 | $39 | $310 | −$120 |
| 3. Purchases 2017-01 → 2021-11 | $96 | $31 | $280 | −$118 |
| 4. Payout checks every 21 days (S2's convention) | $94 | $29 | $270 | −$112 |
| 5. 60-month window | $123 | $44 | $395 | −$194 |
| 6. Cost stress × 1.0 | $115 | $39 | $284 | −$94 |
| 6. Cost stress × 2.0 | $92 | $27 | $285 | −$129 |

## Gates (all passed before any result was read)
- **G1:** 11 unit tests, including path-by-path agreement with `r2.evalsim` on synthetic paths.
- **G2:** with S2's settings, seeds and purchase days, the new simulator reproduces `S2_results.csv` with zero
  difference in every column.
- **G3:** 2,178 real-book cases against `r2.evalsim`: 0 mismatches (outcome, pass day, payouts).

## Inputs
- 4,879 trade days. The coin flip nets −0.0069R a trade (the spread), a net Sharpe of −0.21. S2 printed −0.0035R
  for one seed; the difference is seed noise (standard error 0.007R).
- Hit rate on the better side for each net Sharpe: 0 → 50.9%, 0.15 → 51.5%, 0.3 → 52.1%, 0.5 → 53.0%,
  1.0 → 55.0%, 2.0 → 59.1%.
- P_ref 6,951.7, so the 2.5-lot cap is 1.74× leverage. Median stop/price 1.21%. At the median day the lot cap
  allows 2.11% funded risk (STD) and 1.00% (FTG).

## K1: the map
**Selected policy and value by skill**

| Skill (net Sharpe) | FTG: r, r_f | P(pass) | P(any payout) | V | STD: r, r_f | P(pass) | V |
|---|---|---|---|---|---|---|---|
| Coin flip (−0.21) | 3.5%, 1% | 0.247 | 0.155 | $103 | 4%, 2.5% | 0.245 | $148 |
| 0 | 3%, 1% | 0.291 | 0.207 | $159 | 2.5%, 2.5% | 0.294 | $225 |
| 0.15 | 2.5%, 1% | 0.334 | 0.254 | $215 | 2%, 2.5% | 0.346 | $304 |
| 0.3 | 2.5%, 1% | 0.375 | 0.303 | $285 | 2%, 2.5% | 0.396 | $405 |
| 0.5 | 2%, 1% | 0.466 | 0.398 | $413 | 2%, 2.5% | 0.466 | $580 |
| 1.0 | 2%, 1% | 0.636 | 0.602 | $886 | 1.5%, 2.5% | 0.693 | $1,318 |
| 2.0 | 2%, 1% | 0.867 | 0.864 | $2,307 | 1.5%, 2.5% | 0.932 | $3,838 |

**The coin flip along the sizing grid (FTG, funded risk 1%)**

| r | 0.5% | 1% | 1.5% | 2% | 3% | 3.5% | 4.5% | 5% | 6% | 8% |
|---|---|---|---|---|---|---|---|---|---|---|
| P(pass) | 0.002 | 0.094 | 0.197 | 0.234 | 0.247 | 0.247 | 0.244 | 0.193 | 0.108 | 0.073 |
| V | $1 | $33 | $74 | $93 | $102 | $103 | $103 | $81 | $46 | $31 |

**Reading it:**
1. **A coin flip sized on the plateau is worth about 1.0% of the account** (1.5% in the STD regime). About 25%
   of purchases pass, and about 15% ever receive a payout. A paid buyer receives a median of $537.
2. **The sizing ridge is a plateau with a cliff.** Value is flat from 3% to 4.5% risk a trade (1.5% to 2.3% daily
   volatility). At 5% one stop-out breaches the daily floor, and half the accounts die that way. Below 5% the
   daily floor never binds on a trade with a hard stop.
3. **Conventional sizing forfeits two-thirds.** At 1% a trade the coin flip is worth $33, and at 0.5% nothing.
4. **Skill pays, roughly in a straight line:** about $40 of value per 0.1 of Sharpe at the low end. A Sharpe of
   0.3 is worth 2.8 times the coin flip. With skill the best evaluation risk falls to 2–2.5%.
5. **Funded risk belongs at the cap.** At 0.5% funded risk the coin flip is worth $56, against $103 at 1%.

## K4: fee and break-evens
- **Break-even skill at the $10k list fee is about zero:** a net Sharpe of −0.05 (FTG). At $40 it is below the
  coin flip. In the STD regime the coin flip itself breaks even at list.
- **Skill equivalent of sizing:** moving the coin flip from 1%/1% to the selected policy adds $70, the same as
  raising its net Sharpe from −0.21 to +0.04.
- **Skill equivalent of the $107 promo discount:** a net Sharpe of 0.14.
- **Denial break-even for the coin flip:** at $40 the EV is zero if 61% of payouts are refused.

**Account size (FTG; the rules scale with size, and the 2% Max Risk Rule from $50k changes nothing).** The
coin-flip value is 1.03% of the account. Prices from the checkout page on 2026-10-13.

| Account | List fee | % of account | Coin-flip EV at list | Best code | Coin-flip EV with code | Refusal rate at which the coded EV is zero |
|---|---|---|---|---|---|---|
| $5,000 | $70 | 1.40% | −$18 | $56 | −$4 | none |
| $10,000 | $147 | 1.47% | −$44 | $40 | +$63 | 61% (at $40) |
| $25,000 | $247 | 0.99% | +$11 | $197.60 | +$60 | 23% |
| $50,000 | $357 | 0.71% | +$159 | $285.60 | +$230 | 45% |
| $100,000 | $577 | 0.58% | +$454 | $461.60 | +$570 | 55% |
| $200,000 | $1,097 | 0.55% | +$965 | $877.60 | +$1,185 | 57% |

The fee per dollar of account more than halves from $10k to $100k while the contract's value per dollar does
not change. On paper the product is priced above its no-skill value at the two small sizes and below it from
$25k up. **This assumes stops never slip; see the slippage table at the end, which moves the
break-even size up.** The last column is the caveat in one number: the surplus exists only if the firm pays, and it is gone if the
firm refuses that share of payouts.

## K2: what each rule costs (leave one out, policy fixed)
Change in V when one rule is removed, at the selected policy:

| Rule removed | Coin, FTG ($103) | S = 0.3, FTG ($285) | S = 1.0, FTG ($886) |
|---|---|---|---|
| Step 2 (one step only) | +$78 | +$150 | +$258 |
| Trading costs | +$40 | +$100 | +$205 |
| 20% of the split (100% to the trader) | +$26 | +$71 | +$221 |
| Best Day Rule | +$12 | +$18 | +$23 |
| Intraday monitoring (floors at the close only) | +$10 | +$19 | +$31 |
| Funded lot and position caps | +$6 | +$18 | +$69 |
| No fee refund (refund at $147) | +$23 | +$45 | +$88 |
| Daily floor; Max Risk Rule; evaluation leverage cap; 3-day minimum; 2% minimum; payout lock | $0 to +$2 | $0 to +$2 | $0 to +$17 |
| **Added instead:** step maturities of 30 and 60 days | −$52 | −$225 | −$795 |
| **Instead of on demand:** payout checks every 21 days | −$9 | −$15 | −$24 |
| Bare contract (all frictions off, two steps kept) | +$81 | +$179 | +$391 |

**Reading it:**
1. **The absence of a time limit is the most valuable term in the contract.** Classic 30/60-day maturities would
   halve the coin flip's value and remove about 80–90% of a skilled buyer's.
2. **Costs matter even when tiny.** A spread of 0.007R a trade takes 28% of the coin flip's value.
3. **The rules Lim's model omits are small here.** Best Day Rule, intraday monitoring, lot caps and the Max Risk
   Rule cost the coin flip about $28 in total, taken one at a time.
4. **The daily floor costs nothing** to a book with a hard stop sized under 5%.
5. **For a skilled buyer in the STD regime, taking payouts as early as possible is not optimal.** Removing the
   Best Day Rule *lowers* V at S = 1.0 (−$153), and monthly checks *raise* it (+$59), because early payouts
   strip the buffer above the floor. So the skilled rows are lower bounds, which strengthens the refutation of
   H2 and H3.

## K3: bridge to Lim's model
- **(i) Lim's tables reproduced.** With his contract and normal increments, all 15 cells of his Tables 2 and 3
  come back within 0.004 (the largest difference; the tolerance was 0.01).
- **(ii) Real paths through his classic contract** give nearly the same funding probabilities at 2% daily
  volatility (0.180 against his 0.184 without skill; 0.298 against 0.298 at S = 1). Intraday monitoring costs
  about one point. At 3% volatility real paths fund less often (0.162 against 0.195, and 0.122 monitored
  intraday), because a stop-out then exceeds the daily limit.
- **(iii) Normal increments through Alpha's rules** overstate the FTG value by about 30% ($135 against $102 at
  3% risk) and match the STD value within 5%. The normal model shows a rounded peak near 3%; the real book
  shows the plateau and the cliff.
- **Net:** Lim's pass probabilities are sound at the ridge. The differences between his contract value and
  ours come from the rules (no time limit, on-demand payouts, three years of funded trading), not the paths.

## X1: claim-exclusion table (post hoc reporting frame, rule fixed in the plan)
The break-even Sharpe at the list fee is S* = −0.05, so the pre-registered threshold is effectively zero.

| Threshold | Refuted | Inconclusive | Lower bound above threshold |
|---|---|---|---|
| S* = −0.05 | 3 (M1, P1, R2) | 20 | 1 (M1r) |
| 0.3 | 5 (M1, M2, P1, R1, R2) | 19 | 0 |
| 0.5 | 12 | 12 | 0 |

- Median minimum detectable Sharpe: 0.77. Four point estimates exceed 0.3: A2b 0.36, A4 0.31, B3 0.62, M1r 0.65.
- **M1r is not evidence of an edge.** Its sign was chosen after seeing M1, and on untouched 2017–24 data it fell
  to a Sharpe of 0.10 (batch R).
- **The honest reading:** the programme confirmed nothing and can rule out a Sharpe of 0.5 for half its tests,
  but it cannot rule out 0.3 for 19 of 24. "No edge was found" is supported; "no edge exists" is not.

## Exploratory (outside the plan)
1. **Horizon.** Over the first 12 months sizing and a Sharpe of 0.3 are worth about the same ($48 against $40).
   By 24 months skill leads ($66 against $118), and by 36 months it is worth 2.6 times as much ($70 against
   $182). Skill compounds through a funded account that survives; sizing mostly decides whether there is one.
2. **Sizing and skill multiply.** V at 1%/1% and at the selected policy: coin $33 and $103; S = 0.3 $149 and $285.
3. **Larger accounts.** With the 2% Max Risk Rule that applies from $50k, the FTG values are unchanged to the cent.
4. **The coin flip's funded account** is worth $418 once reached; 63% of funded accounts are paid at least once.

## What this corrects in earlier work
- **S2:** "negative at $147 in every case" holds for the $10k account in the FTG regime (−$44). It is about zero
  in the STD regime, and positive on paper from $25k up, where the fee is a smaller share of the account.
- **S2's EV at $40** was +$34 to +$36 with funded risk at 0.66% and monthly payout checks. With the rules as
  written (on-demand payouts, funded risk at the 1% cap) it is +$63.
- **The positioning memo's thesis** ("value comes from the contract, not from skill") is refuted by H2 and H3.

## Notes on interpretation and limits
- **Reading of the plan:** the STD row uses the STD regime's own selected policy. Rows 2 and 4–6 keep the FTG
  policies fixed, as written.
- The STD regime's funded risk sits at the top of its grid (2.5%), so its optimum may lie slightly higher.
- K3 (iii)'s Gaussian book trades every day at the median stop/price; the real book trades on 95% of days and
  its lot cap moves with volatility. Part of the 30% gap comes from that.
- **Not modelled:** payout denial, the gambling policy, the "same level of risk" clause, the FTG being temporary.
- **One book, one instrument, one history.** Skill is a hit rate applied at full size every day at almost no
  cost, which no real strategy in the programme resembles.
- **Variance:** about 75% of coin-flip purchases fail and 85% are never paid.
- The simulator pays every valid request at the first eligible close. For skilled buyers that is not the best
  payout policy (K2, point 5).

## Amendment 1: validation of outside sources (2026-10-13; full record in `VALIDATION_paper2_sources.md`)
- **Rules:** all 28 quoted phrases match Alpha's pages word for word, and all 64 rule articles were read. Four
  published terms had been missed (fourth-payout bonus, scaling plan, allocation caps, review on passing). None
  changes a modelled rule.
- **The bonus** (0.25% of the account on the fourth payout, discretionary) would add $0.85 to the coin flip's
  $103, $3.13 at a Sharpe of 0.3 and $10.74 at 1.0: between 0.3% and 1.2% of V everywhere. It is reported beside
  V, not inside it. The re-run reproduced every selected K1 value to the cent.
- **Lim's model**, re-implemented from his text alone: Tables 2, 3 and 4 and the Student-t check reproduce in
  full (96 cells plus two), Table 5 on all ten quantities, Table 6 on seven of nine cells. Formal verdict under
  the pre-stated rule: partly reproduced. The two misses come from a definition: his "refundable" average is the
  population mean of the fair fee. At the posted $500 fee the buyer's expected receipts are $212, not $221.
- **Villahermosa and Darmanin** cannot be re-run (no code or data). Villahermosa's arithmetic is internally
  consistent. Neither supplies a number this paper depends on.

## Amendment 2: horizon grid (K5) and other books (K6), 2026-10-13
Plan a9134c0, pushed before the runs. Script `research/run_K_ext.py`; logs `data/logs/run_K_ext_k5.log`, `_k6.log`;
tables `data/checks/K5_horizon.csv`, `K5_D.csv`, `K6_books.csv`. FTG regime; every policy re-selected in its own cell.

| | Hypothesis | Estimate (95% interval) | Verdict |
|---|---|---|---|
| H4 | Classic clock, 12-month window: sizing is worth more than a Sharpe of 0.3 (D > 0) | D = +$3.5 (+1.9 to +5.2) | **SUPPORTED**, by a small margin |
| H5 | No clock, 60-month window: D < 0 | D = −$245 (−252 to −238) | **SUPPORTED** |
| H6 | Under each clock, D falls as the window lengthens | All six steps fall | **SUPPORTED** |
| H7 | At every window, D is larger with the clock than without | +$1.3 (−0.3 to +2.8) at 12 months; +$35, +$83, +$172 at 24, 36, 60 | **INCONCLUSIVE** (the 12-month cell) |
| H8 | The coin flip is worth $75 to $130 on every other book | NAS100 $131, EUR/USD $95, USD/JPY $58 | **REFUTED** |
| H9 | Skill beats sizing (D < 0) on every other book | −$107, −$73, −$108 | **SUPPORTED** |

**K5: value per $10k purchase by contract clock and value window**

| Clock | Window | Coin flip, best size | Coin flip at 1%/1% | S = 0.3 | S = 1.0 | D | S = 1.0 at 1%/1% |
|---|---|---|---|---|---|---|---|
| None | 12 months | $58 (4.5%) | $3 | $111 | $239 | +$2 | $39 |
| None | 24 months | $87 (4%) | $19 | $204 | $544 | −$48 | $300 |
| None | 36 months | $105 (3.5%) | $40 | $288 | $876 | −$117 | $689 |
| None | 60 months | $123 (3.5%) | $71 | $419 | $1,555 | −$245 | $1,509 |
| Classic 30/60 days | 12 months | $43 (4.5%) | $0 | $82 | $174 | +$4 | $0 |
| Classic 30/60 days | 24 months | $64 (4.5%) | $0 | $141 | $345 | −$13 | $0 |
| Classic 30/60 days | 36 months | $76 (4.5%) | $0 | $187 | $499 | −$34 | $0 |
| Classic 30/60 days | 60 months | $87 (4.5%) | $0 | $247 | $771 | −$73 | $1 |

**Reading K5:**
1. **The length of the window, more than the evaluation clock, sets the exchange rate between sizing and
   skill.** Over one year they are level under either clock. From two years on, a Sharpe of 0.3 is worth more
   than sizing even with the classic time limits. "The clock decides" would have been the wrong thesis.
2. **What the clock does is make caution fatal.** With the classic limits a buyer sizing at 1% is worth nothing
   at any skill level. Without them, a cautious buyer with a Sharpe of 1.0 is worth $689 over 36 months, 6.5
   times the best-sized coin flip.
3. **The clock's cost once the buyer re-sizes for it** is 28% of the coin flip's 36-month value, 35% at a Sharpe
   of 0.3 and 43% at 1.0. K2's row n held the policy fixed and so overstated it (50% and more).
4. **The penalty for conventional sizing shrinks with the window.** At 1%/1% the coin flip forfeits 96% of its
   value over 12 months, 79% over 24, 62% over 36 and 42% over 60. At 36 months 20% of such buyers are still in
   the evaluation; at 12 months, 70%. On a contract with no clock, small size mostly costs time.
5. **The best size falls with the window and with skill:** from 4.5% to 3.5% for the coin flip, and from 3.5%
   to 1.5% at a Sharpe of 1.0.
6. **Lim's sentence, on our data.** D measures skill from the coin flip (net Sharpe −0.21), a step of 0.51.
   Measured from a net Sharpe of zero, a step of 0.3, sizing is worth more than skill at every window under the
   classic clock (+$31, +$39, +$38, +$26), and at 12 and 24 months without it (+$38, +$11), but not at 36 or 60
   (−$45, −$167). So his "sizing matters at least as much" holds under his contract's clock; it stops holding
   once the clock is gone and the buyer stays three years.
7. **Against K1.** With no evaluation cut-off and purchases to 2019, the coin flip's 36-month value is $105
   against K1's $103, and $40 against $33 at 1%/1%.

**K6: the same contract on other books (FTG, 36 months)**

| Book | Cost of a random trade | Its net Sharpe | Best size | P(pass) | Coin flip | At 1%/1% | S = 0.3 | Costs set to zero |
|---|---|---|---|---|---|---|---|---|
| NAS100 | −0.0050R | −0.15 | 3% | 0.263 | $131 ($128 to $134) | $51 | $317 | $165 |
| US500 (K1) | −0.0069R | −0.21 | 3.5% | 0.247 | $103 ($100 to $106) | $33 | $285 | $143 |
| EUR/USD | −0.0049R | −0.21 | 4.5% | 0.257 | $95 ($93 to $98) | $10 | $253 | $149 |
| USD/JPY | −0.0075R | −0.35 | 4.5% | 0.225 | $58 ($56 to $60) | $3 | $221 | $135 |

**Reading K6:**
1. **"About 1% of the account" is the US500 figure, not a constant.** Across four liquid instruments the
   no-skill value runs from 0.58% to 1.31% of the account. The paper must say so.
2. **The differences are trading cost.** The value lines up with the net Sharpe of a random trade: −0.15 gives
   $131, −0.21 gives $95 to $103, −0.35 gives $58. That is K1's slope of about $40 per 0.1 of Sharpe, so cost
   behaves as negative skill. With costs set to zero the four books sit between $135 and $165.
3. **Skill beats sizing on every book,** so H2's refutation is not specific to US500.
4. **Conventional sizing is worse on currencies:** $10 and $3 at 1%/1%, because an afternoon currency trade
   moves less per unit of risk and takes longer to reach the target.
5. **At list fees:** the $10k fee (1.47%) is above the no-skill value on every book. The $100k fee (0.58%) is
   below it on three and level with it on USD/JPY.

## Amendment 3: the buyer's best policy (K7), 2026-10-13
Plan bb03b76, pushed before any K7 code ran. Solver `propcontract/optimal.py`; script `research/run_K7.py`; logs
`data/logs/run_K7_*.log`; tables `data/checks/K7_classes.csv`, `K7_paths.npz`; policies in `data/r2cache/K7_policies/`.

**Gates (all passed before a result was read)**
- **G4:** a one-size policy table reproduces the fixed-size simulator path by path (`tests/test_rK_optimal.py`).
  After the simulator was extended to take policies, its original gates were re-run: G2 exact, G3 2,178 cases
  with no mismatch.
- **G5:** solver $111.54 for K1's fixed policy against $110.47 (se 0.70) simulated on independent days.
- **G6:** solver $127.18 for the free policy against $127.24 (se 0.74) simulated; $127.07 on a half-step grid.

**Policy classes on K1's evaluation paths (real US500 history; value per $10k purchase)**

| Regime | Skill | A: fixed sizes (K1) | B: A with free payout timing | C: free sizing, earliest payout | D: both free | D over A |
|---|---|---|---|---|---|---|
| FTG | Coin flip | $103 | $103 | $120 | $120 | +16% |
| FTG | S = 0.3 | $285 | $285 | $306 | $306 | +7% |
| FTG | S = 1.0 | $886 | $896 | $976 | $982 | +11% |
| STD | Coin flip | $148 | $148 | $171 | $171 | +16% |
| STD | S = 0.3 | $405 | $441 | $460 | $483 | +19% |
| STD | S = 1.0 | $1,318 | $1,607 | $1,618 | $1,881 | +43% |

| | Hypothesis | Estimate (95% interval) | Verdict |
|---|---|---|---|
| H10 | Coin flip, FTG: the best policy beats the fixed one by more than 10% | V_D − 1.10 · V_A = +$6.4 (+4.1 to +8.7); gain 16.2% | **SUPPORTED** |
| H11 | Average evaluation risk under D falls with skill: coin > 0.3 > 1.0 | 4.18%, 1.56%, 1.67% | **REFUTED** (the second step rises by 0.10 points) |
| H12 | The solver's value is within 10% of the realised value (coin flip, FTG) | Ratio 1.061 (1.037 to 1.086) | **SUPPORTED** |
| H13 | Free payout timing adds under 2% for the coin flip and over 5% at S = 1.0 in the STD regime | 0.0% and 22.0% | **SUPPORTED** |

**Reading K7:**
1. **A no-skill buyer who adapts is worth about a sixth more:** $120 against $103 in the FTG (1.20% of the
   account), with 28.6% passing against 24.7% and 18.2% paid against 15.5%. All of it comes from sizing.
2. **What that policy looks like.** It starts near 4.75% a trade, shrinks the trade to just reach the target as
   the target nears (1% at $10,900, 0.25% at $10,990), and near the floor it stakes everything it has left. Once
   funded it trades at the 1% cap and takes each payout at the first allowed close.
3. **That is the conduct the firm's gambling policy names.** On a typical path the largest size is about ten
   times the smallest, and 32 times on one path in ten. So the published discretion is aimed at a prize worth
   about 16% of the no-skill value. The other 84% is available at a constant size.
4. **With skill the best policy is cautious, but not monotonically.** A skilled buyer starts near 2% to 2.5%,
   cuts size as the floor nears and never stakes the remainder. Average risk falls from 4.2% without skill to
   1.6% at a Sharpe of 0.3, then edges up to 1.7% at 1.0, because a stronger edge is worth reaching the funded
   stage sooner. H11 as written is therefore refuted.
5. **Waiting pays only with skill.** For the coin flip the earliest payout is exactly optimal. At a Sharpe of
   1.0 in the STD regime, free timing alone adds 22% and the full policy 43%: the buyer lets profit build a
   buffer above the floor before withdrawing. This is K2's point 5, now measured. In the FTG the 1% cap leaves
   little to protect and timing adds 1%.
6. **Independent days are a fair model.** The solver's value exceeds what its policy earns on the real history
   by 6%, the same order as the block bootstrap's 7%.
7. **Lower bounds.** In the STD regime 7.5% of funded accounts at a Sharpe of 1.0 reach the solver's +$3,000
   profit cap, so those values would be higher without it, and higher again with the scaling plan.

**Deviation from the plan:** the plan asked for the share of funded *days* at the profit cap. The run recorded
the share of funded *accounts* that ever reached it (zero in every cell except S = 0.3 and 1.0 in the STD regime).

## Amendment 4: the firm's plan menu (K8), 2026-10-13
Plan ec0deb4, pushed before any K8 code ran. Script `research/run_K8.py`; logs `data/logs/run_K8*.log`; tables
`data/checks/K8_plans.csv`, `K8_paths.npz`. Rules from the saved help-centre pages; list fees from the checkout
(`FEES_alpha_2026-10-13.json`). Book Z2 on US500, K1's conventions.

**Gates:** new unit tests for the trailing limit, the retained buffer and the cash-out closure pass; G2 and G3
re-run after the simulator was extended (exact; 2,178 cases, no mismatch); the Swing row reproduces K1's four
selected values to the cent.

**The menu at $10k, coin-flip buyer (value per purchase; list fee; FTG regime unless stated)**

| Plan | Structure | List fee | P(pass) | P(paid) | V, FTG | V, standard | EV at list, FTG | V per $1 of fee | V at S = 0.3 |
|---|---|---|---|---|---|---|---|---|---|
| Pro 8% | 8% then 5%; 8% static | $57 | 0.226 | 0.134 | $91 | $115 | +$34 | 1.60 | $259 |
| Pro 10% | 10% then 5%; 10% static | $77 | 0.245 | 0.153 | $109 | $154 | +$32 | 1.42 | $303 |
| Pro 10%, bi-weekly | as above, payouts every two weeks | $87 | 0.247 | 0.192 | $122 | $164 | +$35 | 1.40 | $323 |
| Pro 6% | 6% then 6%; 6% static | $47 | 0.181 | 0.100 | $62 | $71 | +$15 | 1.31 | $182 |
| Direct | no evaluation; 5% trailing | $97 | n/a | 0.128 | $91 | (one regime) | −$6 | 0.93 | $247 |
| Swing | 10% then 5%; 10% static | $147 | 0.247 | 0.155 | $103 | $148 | −$44 | 0.70 | $285 |
| One 12% | 12%; 8% trailing | $107 | 0.234 | 0.131 | $70 | $71 | −$37 | 0.66 | $159 |
| One 10% | 10%; 6% trailing | $87 | 0.212 | 0.106 | $46 | $46 | −$41 | 0.53 | $106 |
| One 6% | 6%; 4% trailing | $67 | 0.237 | 0.115 | $33 | $33 | −$34 | 0.49 | $71 |

| | Hypothesis (coin flip, FTG, $10k) | Estimate (95% interval) | Verdict |
|---|---|---|---|
| H14 | Pro 10% is worth at least as much as Swing | +$6.0 (+4.4 to +7.7) | **SUPPORTED** |
| H15 | Pro 10% is worth more than its $77 fee | EV +$32 (+29 to +35) | **SUPPORTED** |
| H16 | Swing has the lowest value per dollar of fee among plans with an evaluation | Swing 0.70; One 6% 0.49, One 10% 0.53, One 12% 0.66 | **REFUTED**: the One plans are lower |
| H17 | One 10% is worth less than Pro 10% | −$63 (−66 to −61) | **SUPPORTED** |
| H18 | Direct is worth less than its $97 fee | EV −$6.5 (−8.9 to −4.0) | **SUPPORTED** |

**Coin-flip EV at list by account size (FTG; the rules scale with the account)**

| Plan | $5k | $10k | $25k | $50k | $100k | $200k |
|---|---|---|---|---|---|---|
| Pro 10% | +$22 | +$32 | +$96 | +$279 | +$644 | +$1,286 |
| Pro 8% | +$8 | +$34 | +$50 | +$158 | +$382 | +$821 |
| Pro 6% | +$4 | +$15 | +$37 | +$91 | +$220 | +$436 |
| Swing | −$18 | −$44 | +$11 | +$159 | +$454 | +$965 |
| Direct | −$22 | −$6 | +$29 | +$196 | +$448 | +$913 |
| One 12% | −$22 | −$37 | −$41 | +$5 | +$117 | not sold |
| One 10% | −$24 | −$41 | −$72 | −$48 | −$18 | −$30 |
| One 6% | −$21 | −$34 | −$75 | −$72 | −$67 | +$12 |

**Reading K8:**
1. **The price list does not follow contract value.** The same no-skill buyer gets back between $0.49 and $1.60
   per dollar of list fee depending on which plan is bought. The dispersion across plans is larger than anything
   sizing or adaptive play produces within one plan.
2. **Every two-step Pro plan is worth more than its list fee to a disciplined no-skill buyer, at every size,**
   in the restricted regime and before any discount. That is a stronger form of "fair on paper" than Swing
   gave: on Pro 10% the written contract returns $1.42 per dollar of fee at $10k and about $2.40 at $100k.
3. **Swing is Pro 10% at nearly twice the price.** The targets and limits are identical. Swing's buyer pays $70
   more at $10k for weekend holds and a looser news rule, and gets half the lot cap, which is why its value is
   $6 lower for an intraday book.
4. **One step with a trailing limit is the poor contract.** The One plans pass about as often as the two-step
   plans but are worth roughly half as much (42% to 64%), because each payout ratchets the floor up and the cushion
   never rebuilds. H16 failed for this reason: I expected Swing to be the worst value and the One plans are.
5. **The instant account is close to fair and thinly paid:** $91 of value against $97, with 12.8% of buyers
   ever paid. Its fee falls with size like the others, so it is positive on paper from $25k.
6. **Bi-weekly payouts are worth more than on-demand ones on Pro 10%** ($122 against $109), because they carry
   no best-day rule; the option costs $10.
7. **With a small edge every plan is worth more than its fee,** but by very different margins: a Sharpe of 0.3
   is worth $303 on Pro 10% ($77) and $71 on One 6% ($67).
8. **The restricted regime changes little on One and Direct:** their selected funded risk is at or below 1% in
   either regime.

**Limits specific to K8**
- The 5-minute news window on Pro, One and Direct is not modelled. The book enters at 14:30 and exits at 20:30
  London, away from scheduled releases, but a stop triggered inside a window would be a close inside it.
- The profit left in on the One plans was chosen from 0%, 2% and 4%; for the coin flip the selection took 0% on
  all three.
- One book, one instrument. K6's range across instruments applies to every row.
- The bi-weekly minimum is a flat $100, so its row is exact at $10k only.
- These are model values if the firm pays every valid request. Nothing here is a recommendation to buy.

## Amendment 5: real strategies through the contract (K9), 2026-10-13
Plan c87a97f, pushed before any K9 code ran. Script `research/run_K9.py`; log `data/logs/run_K9.log`; table
`data/checks/K9_real_books.csv`. Swing rules, FTG regime, policy selected on early purchases and held for late ones.
**None of these books is a confirmed edge, and A1b and M1r were chosen after seeing the early years.**

| Book | Purchases | Net Sharpe | P(pass) | Median months to pass | P(any payout) | V (95% interval) | Idealised buyer at the same Sharpe |
|---|---|---|---|---|---|---|---|
| A1b (0.75% a trade, up to 3 open) | Early | 0.80 | 0.587 | 11.7 | 0.566 | $468 ($163 to $779) | $729 |
| | Late | 0.49 | 0.429 | 12.1 | 0.283 | $155 ($10 to $320) | $397 |
| A2b (3%, up to 5 open) | Early | 0.34 | 0.010 | 2.7 | 0.000 | $0 | $338 |
| | Late | 0.49 | 0.001 | 3.0 | 0.001 | $0 | $395 |
| M1r (1.5%, up to 12 open) | Early | 0.58 | 0.155 | 7.1 | 0.026 | $6 ($0 to $18) | $524 |
| | Late | 0.10 | 0.039 | 11.2 | 0.000 | $0 | $187 |
| R3 = A2b + M1r (1%) | Early | 0.67 | 0.376 | 14.7 | 0.169 | $40 ($6 to $87) | $606 |
| | Late | 0.32 | 0.308 | 13.6 | 0.089 | $17 ($0 to $43) | $292 |
| W3 = all three (0.75%) | Early | 1.03 | 0.721 | 9.4 | 0.707 | $648 ($311 to $985) | $994 |
| | Late | 0.58 | 0.322 | 7.6 | 0.258 | $80 ($19 to $148) | $471 |

Early = purchases 2005-02 to 2014-02 (2,351 days); late = 2017-01 to 2021-11 (1,266 days). Intervals from a
stationary bootstrap of the purchase days, because neighbouring purchases share most of their path.

| | Hypothesis (late purchases) | Result | Verdict |
|---|---|---|---|
| H19 | Every book is worth less than an idealised buyer at the same Sharpe | All five intervals lie below the idealised value | **SUPPORTED** |
| H20 | The best book is worth less than the coin flip ($96 on these purchase days) | A1b $155 ($10 to $320) | **INCONCLUSIVE** |
| H21 | Every book is worth less on late purchases than on early ones | Only W3 clearly (−$567, −912 to −222); A1b −$313 (−653 to +20) | **INCONCLUSIVE** |

**Reading K9:**
1. **The contract pays for a kind of skill the programme did not produce.** K1's "$285 at a Sharpe of 0.3" is
   for an edge that trades one position every day. The one ensemble tested on untouched data, R3, has a Sharpe
   of 0.32 on late purchases and is worth $17, about 6% of the idealised $292.
2. **Two things destroy the value of an event-driven edge.** It trades too rarely to reach the targets (A2b
   trades on about twelve days a year and passes 1% of the time at any size), and once funded, the restricted
   regime caps the risk of all open positions together at 1%, so a book with twelve trades open risks 0.08% on
   each (M1r passes 16% of early purchases and is paid on 3%).
3. **Only the one daily book is worth much, and it is the least trustworthy.** A1b trades every day in up to
   three pairs. It is worth $468 on the years it was chosen on and $155 on later purchases, 39% of the
   idealised value at its Sharpe, with an interval that runs from $10 to $320.
4. **Whether any real book beats a well-sized coin flip is not settled.** The best one's interval contains the
   coin flip's $96. Five overlapping years of late purchases hold too few independent three-year windows.
5. **Adding weaker books to the daily one made it worse on late purchases** ($80 for all three against $155
   for A1b alone): more open positions tighten the funded cap and add event-day losses.
6. **Two of the books would not stay active on their own.** A2b and M1r have spells of 33 and 56 days without
   a trade, beyond the 30-day inactivity rule; the run assumes a token trade keeps the account open.

**Limits specific to K9**
- A daily series cannot hold the detail of the older trade-by-trade simulator: lows of open trades are assumed
  to coincide, payouts are taken at closes even with a position open, and one currency lot is taken at parity.
- The idealised comparison takes K1's value at each book's Sharpe as a constant, with no interval of its own.
- Sharpe ratios here are from each book's daily series on each group of years, flat days included.

## Exploratory, added after the first write-up (2026-10-13; `research/info_K_funded_risk.py`, `info_K_slippage.py`)
**The simulated stop never slips.** In 9,758 simulated trades (both sides of 4,879 days) the worst loss is exactly
1.00R: no 30-minute bar ever opened beyond a stop. So the map assumes every stop-out fills at the stop price.

**Stop slippage (coin flip, FTG, funded risk 1%, evaluation risk 3.5%).** Every stop-out loses 1 + s times the
stop distance:

| Slippage s | Mean result a trade | P(pass) | V per $10k | V as % of account |
|---|---|---|---|---|
| 0 (the map) | −0.0069R | 0.247 | $103 | 1.03% |
| 5% | −0.0099R | 0.234 | $88 | 0.88% |
| 10% | −0.0130R | 0.222 | $75 | 0.75% |
| 25% | −0.0220R | 0.188 | $49 | 0.49% |

- Each 5% of slippage costs about $14. H1's sign holds at 5% and 10%.
- **The account-size result is weaker than the K4 table suggests.** At list fees the coin flip is positive from
  $25k with no slippage, from $50k at 5%, only from $100k at 10% (the $50k is about zero), and at no size at 25%.
- The plateau's right edge is fragile: at 10% slippage, 4.5% evaluation risk breaches the daily limit on 39% of
  purchases; at 25%, 4% does on 58%. Evaluation risk of 3–3.5% keeps a margin.
- In the STD regime, 2.5% funded risk meets the 3% Max Risk Rule once a stop slips 20%: V falls to $43 at 25%
  slippage, against $73 at 2% funded risk. So 2% is the prudent STD setting, at a cost of about $3 without slippage.
- Realistic slippage for this trade is not measured here. One index point is about 1.2% of the stop distance.

**Funded risk (coin flip, FTG, evaluation risk 3%, the live S2 ticket's setting):**

| Funded risk | V | V by 12 months | P(any payout) | Funded accounts lost to the floor | Still open at 36 months |
|---|---|---|---|---|---|
| 0.50% | $56 | $23 | 0.146 | 25% | 75% |
| 0.66% (the ticket) | $75 | $33 | 0.153 | 45% | 55% |
| 0.80% | $88 | $40 | 0.156 | 58% | 42% |
| 0.90% | $96 | $44 | 0.155 | 65% | 35% |
| 1.00% (the FTG cap) | $102 | $48 | 0.155 | 71% | 30% |

- The chance of being paid at all barely moves. Higher funded risk pays sooner and more per paid buyer.
- Part of the gap is the 36-month cut-off: at 0.66% more than half the funded accounts are still open with value
  left. The rest is cost: the spread is a larger share of the variance at lower risk.
- 0.66% came from the spec's allowance for overnight and event gaps (three times the stop). This trade is
  intraday with a stop, so the binding limit is the FTG's 1% cap, not the Max Risk Rule.
