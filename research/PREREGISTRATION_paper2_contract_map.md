# Pre-registration: Paper 2 analysis plan, the Alpha Swing contract map (written 2026-10-13, before any K run)

**Paper question:** what is a prop-firm challenge worth to a buyer, and how much of that value comes from skill
rather than from sizing and the fee?

**Prior work this plan answers to:**
- Lim (SSRN 7178078) prices a stylised two-step contract with normal daily increments, closes-only monitoring
  and no consistency rule. He already reports that value sits on a sizing ridge near 2% daily volatility and that
  "risk sizing matters at least as much" as skill. He lists as limitations: normal returns, daily-close
  monitoring, and no consistency rules, payout caps or discretionary denials.
- Villahermosa (SSRN 7445798) finds positive value for a no-edge buyer at a discounted fee on a futures firm.
- S2 (9aa7382) found the same sign pattern on Alpha Swing with one simplified funded model.

**What is new here:** the same questions on (1) a named firm's full rule set, re-verified at source on
2026-10-13, including the rules Lim omits; (2) real intraday paths of an executable trade at measured broker
costs; (3) a skill axis that the 24-test programme can be placed on. This is a contract valuation. It tests no
market edge and is outside the Benjamini–Hochberg family (m stays 24).

## 1. Book and data (unchanged from S2)
- SPX500_USD, OANDA M30 bars, development sample 2005-01-01 → 2024-09-30. The hold-out stays locked.
- One trade every London weekday that has both a 14:30 and a 20:30 London bar: enter at the 14:30 bar open,
  exit at the 20:30 bar open, stop 1 × ATR(14, D1) of the previous broker day. Intraday, so no swap.
- Costs: ACG median spread by hour × 1.5, price-proportional.
- **Both sides are simulated for every trade day:** net result R and worst intraday mark L, in units of the
  stop distance, for the long and for the short. v_d = stop distance / entry price.

## 2. Skill model
- A buyer takes the better side of the day (the one with the higher net R) with probability p, independently
  each day. p = 0.5 is the **coin-flip buyer** (no skill).
- For a target net annualised Sharpe ratio S, p(S) solves SR(p) = S on the full development sample, where
  SR(p) = m/s × √A, m = p·mean(R_b) + (1−p)·mean(R_w), s² = p·mean(R_b²) + (1−p)·mean(R_w²) − m², with R_b and
  R_w the better and worse side's net R and A the number of trades per year.
- **Skill grid:** coin flip, and S ∈ {0, 0.15, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0}. S = 0.3 is the reference for a
  research-grade edge: the best validated net Sharpe in the programme (R3 0.29, U1 futures 0.25).
- This vehicle is generous to skill: the edge is applied at full size every day at negligible cost.

## 3. Contract: Alpha Swing $10k as written (help centre and T&C, fetched 2026-10-13)
**Evaluation**
- Step 1 +10%, step 2 +5% on a fresh balance, reached at a day's close; at least 3 trading days per step.
- Static floor 90% of initial. Daily floor 95% of the day's opening balance. Both are checked on the day's
  worst intraday mark.
- No time limit in the contract ("There are no time limits applicable to the Evaluations"). Analysis horizon:
  pass within 504 trading days of purchase; the whole window is 756 trading days.
- No lot cap in the evaluation. Index leverage 1:10, so the applied risk is min(r, 10 · v_d).
- Administration gaps as in S1–S3: 2 idle trading days after step 1, 3 before the funded account starts.
- Inactivity (30 days) cannot bind on a daily book; the run asserts this.

**Funded (Qualified) account, two regimes**
- **STD (as written):** 2.5-lot cap. One lot is one index unit, so the applied risk is min(r_f, λ · v_d) with
  λ = 2.5 × P_ref / 10,000. P_ref is the US500 median close over the year the ACG costs were measured (the
  reference the cost tables already use).
- **FTG (Focused Trader Group):** any position ≤ 1% of initial and a 1.25-lot cap: min(r_f, 1%, (λ/2) · v_d).
  The book meets the published triggers ("a swing trading account primarily for ... frequent intraday
  strategies", "taking full risk on evaluation"), so **FTG is the primary regime** and STD the upper case.
- **Max Risk Rule:** the account closes if the open loss on the position reaches 3% of initial.
- Floors as in the evaluation.
- **Payout (On-Demand):** requested at the first close where profit ≥ 2% of initial and the best day since the
  last payout is ≤ 40% of that profit. Pays 80% of the profit. The account is locked for 2 trading days and
  restarts at the initial balance. No fee refund.
- Fee: $147 list, $40 with the promo code (as recorded on 2026-09-24).

**Not modelled, stated as caveats:** payout denial under the gambling policy or the "maintain the same level of
risk" clause; FTG being temporary; the FTG cooling-off rule (cannot bind with one trade a day); the news rule.

**Changes from S2's funded model:** S2 checked payouts every 21 days and used fixed funded risk (0.66%, 1.75%).
The help centre states no minimum interval, and the lot cap is a notional cap, so both are replaced. S2's
convention is kept as a robustness row, and S2's published table must be reproduced exactly (gate G2).

## 4. Decision variables, paths and estimators
- Evaluation risk r ∈ {0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 6, 8}% of initial. Funded intended risk
  r_f ∈ {0.5, 1, 1.5, 2, 2.5}%. Sizes are fixed fractions of the initial balance.
- **Outcome:** V = mean payouts per purchase within the 756-day window (USD, and % of account). EV = V − fee.
- **Primary estimator (historical order):** each path draws a purchase day uniformly from the business days on
  which a full window fits (from 2005-02-01), then one uniform per day; it takes the better side when u < p.
  The same purchase days and uniforms are used in every cell (common random numbers).
- **Two independent path sets of 50,000:** a selection set (seed 20261013) picks the best (r, r_f) for each
  skill level and regime; every reported number comes from the evaluation set (seed 20261014).
- **Inference:** 95% normal confidence intervals across paths, paired by path for differences. These are
  Monte Carlo intervals conditional on the 2005–2024 history. History dependence is covered by section 9.
- A new vectorised simulator is used (`propcontract/contract.py`). It must pass the gates in section 10 before
  any result is read.

## 5. K1: the map
For every skill level, r and regime, at the selected r_f: P(step 1), P(pass), median months to pass, breach
types, P(at least one payout), V with its interval, and V at 12, 24 and 36 months.

**Confirmatory hypotheses (FTG regime, evaluation set):**
- **H1 (the fee decides the sign without skill):** for the coin-flip buyer at the selected policy,
  V > $40 and V < $147.
- **H2 (sizing is worth more than a research-grade edge):** D > 0, where
  D = [V(coin, selected) − V(coin, r = 1%, r_f = 1%)] − [V(S = 0.3, selected) − V(coin, selected)].
  The first bracket is the gain from conventional to contract-optimal sizing with no skill. The second is the
  gain from no skill to S = 0.3, each at its own best sizing.
- **H3 (a research-grade edge does not rescue the list fee):** V(S = 0.3, selected) < $147.

**Verdicts:** SUPPORTED if the 95% interval excludes the boundary in the stated direction; REFUTED if it
excludes it in the opposite direction; otherwise INCONCLUSIVE. For H1 both parts must hold. A verdict is called
**robust** only if every row of section 9 has the same sign. My rough arithmetic before running puts H2 and H3
near the boundary, so either outcome is plausible, and each will be reported as found:
- H2 supported: Lim's sizing result extends to a named contract on real paths.
- H2 refuted: the contract rewards small skill more than the stylised model implies; the paper says so.

## 6. K2: what each rule costs (leave one out)
At the selected policy for the coin flip, S = 0.3 and S = 1.0, in both regimes, policy held fixed, the change
in P(pass), P(at least one payout) and V when one rule is removed:
a. no daily floor; b. floors checked at the close only; c. one step (no step 2); d. no minimum trading days;
e. no evaluation leverage cap; f. no funded lot or position caps; g. no Max Risk Rule; h. no Best Day Rule;
i. no 2% minimum (any positive profit); j. payout checks every 21 funded days instead of on demand;
k. no payout lock; l. 100% split (arithmetic); m. fee refunded with the first payout (arithmetic);
n. step maturities of 30 and 60 trading days (the classic contract); o. no trading costs.
Also the **bare contract**: a, b, d–k and o together. Holding the policy fixed understates what an adapting
buyer would gain; this is stated.

## 7. K3: bridge to Lim's model
- **(i) Replication of Lim's tables** with his contract and normal increments (N × L), 200,000 paths:
  Table 2 rows 2–4 at 2% daily volatility for S = 0 and 2 (0.453/0.744, 0.310/0.550, 0.298/0.532) and
  Table 3 for S ∈ {0, 1, 2} × volatility ∈ {1, 2, 3}%. Agreement means within ±0.01.
- **(ii) Real paths through Lim's contract** (R × L): the same Table 3 cells with r = volatility / sd(R),
  monitored at the close and, separately, intraday.
- **(iii) Normal increments through Alpha's rules** (N × A): a Gaussian book with the same mean and standard
  deviation of R as the real book, for the coin flip, S = 0.3 and S = 1.0, over the r grid in both regimes.
- Reading: (ii) against (i) shows what real paths change; (iii) against K1 shows what real paths change under
  the real rules; K1 against (ii) shows what the real rules change.

## 8. K4: fee and break-evens (derived from K1, no new simulation)
- Break-even fee by skill level: V at the selected policy, in USD and % of account.
- Break-even Sharpe at $40 and at $147 (linear interpolation in S; the coin flip sits at its own net Sharpe).
- **Skill equivalent of sizing:** the S at which V(S) − V(coin) equals the first bracket of H2.
- **Skill equivalent of the promo code:** the S at which V(S) − V(coin) = $107.
- **Denial break-even:** the payout-denial probability q* = 1 − fee / V at which EV is zero.
- V as % of account against Alpha's fee by account size, where the rules scale (the Max Risk Rule is 2% from
  $50k, so only the FTG regime carries over). The fee schedule is read from the checkout page and dated.

## 9. Robustness rows (policies fixed at the primary selection)
1. STD regime.
2. Stationary block bootstrap of trading days (mean block 21 days), 50,000 paths, seed 20261015.
3. Purchases 2005-02 → 2014-02 and purchases 2017-01 → 2021-11 separately (S2's two windows).
4. Payout checks every 21 funded days (S2's convention).
5. A 60-month window (evaluation horizon unchanged).
6. Cost stress × 1.0 and × 2.0.

## 10. Gates before any K result is read
- **G1:** unit tests on synthetic paths with known answers.
- **G2:** with S2's settings, seeds and purchase days, the new simulator reproduces `data/checks/S2_results.csv`
  (pass rates to 4 decimals, payouts to the cent).
- **G3:** path-by-path agreement with `r2.evalsim` (outcome, pass day, payouts) on at least 2,000 cases.
- K3 (i) is a non-blocking check: a mismatch with Lim's tables is reported, not tuned away.

## 11. X1: claim-exclusion table for the 24 tests (a reporting frame, fixed now, compiled later)
- For each test in the Benjamini–Hochberg family: Ŝ = annualised net Sharpe of the pre-registered strategy on
  the sample its decision used, from daily mark-to-market results at unit risk with flat days included; T =
  years in that sample. Taken from the committed results file or log where stated, otherwise recomputed from
  the test's own builder unchanged. The source is recorded per test.
- SE = √((1 + Ŝ²/2) / T) (Lo 2002). U = Ŝ + 1.645 · SE is the one-sided 95% upper bound.
- **REFUTED** at threshold S* if U < S*; **INCONCLUSIVE** otherwise; "consistent with a material edge" if the
  lower bound exceeds S*.
- S* is the break-even Sharpe at the list fee from K4 (FTG), and also 0.3 and 0.5.
- Minimum detectable Sharpe at 80% power, one-sided 5%: 2.49 / √T.
- This re-reports finished tests under a declared rule. It is post hoc and is labelled so.

## 12. Deviations
Any change after the first K run is recorded as a dated amendment with its reason. Analyses outside this plan
are labelled exploratory.

### Amendment 1 (2026-10-13, written and pushed before the runs it describes): validation of outside sources
**Reason:** the paper will quote numbers from Lim (2026) beyond the 15 cells checked in K3 (i), and its rule
table was fetched through a summarising reader. The author asked that every outside source the paper relies on
be validated before drafting. Neither check tests a market edge or changes any K result.

**V1: independent re-implementation of Lim's model** (`research/validate_lim.py`). Written from Sections 4–5
of his paper only; it does not import `propcontract/contract.py`. 200,000 paths per stage, independent across
stages, seed 20261017. Conventions fixed now:
- **Grid:** net Sharpe ∈ {−5, −4, −3, −2, −1, −0.5, 0, 0.5, 1, 2, 3, 4}. The paper says twelve values from −5
  to +4 and tabulates nine; the other three are assumed. Daily volatility ∈ {0.5, 1, 2, 3, 5}%.
- **Step:** normal daily increments with mean S·σ/√252. Each day the daily rule is checked first (an increment
  ≤ −5% fails), then the cumulative barriers (≥ target passes, ≤ −10% fails). Targets 10% and 5%, maturities 30
  and 60 days, steps on independent paths. P(funded) is the product of the two step probabilities.
- **Funded stage:** same loss rules, 250 days. On days 20, 40, …, 240 a positive cumulative profit X is swept:
  the trader receives 80% of it and X returns to zero. No sweep on day 250 (primary). The alternative with a
  final sweep on day 250 is reported beside it, because the paper does not say.
- **Values:** non-refundable value = P(funded) × E[payouts | funded]; refundable value = P × (E + q × $500),
  with q = P(at least one sweep | funded); fair fee F = P·E / (1 − P·q). Account $100,000.
- **Population:** gross Sharpe standard normal, net = gross − k·√252 with k = 0.10; volatility weights
  5/20/30/25/20%; two million draws; linear interpolation in net Sharpe within each volatility column; end rows
  outside the grid.
- **No-time-limit variant:** each step capped at 300 days, unresolved paths counted as failures.
- **Student-t check:** t(4) innovations scaled to unit variance, step one at 2% volatility.

Targets and tolerances:
- a. Table 2 (6 simulated cells) and Table 3 (45 cells): within ±0.01.
- b. Anchors at S = 0 and 2% volatility: E[payouts | funded] $7,300 ± 5%, q = 0.56 ± 0.02, fair fee $1,502 ± 5%.
- c. Table 4 (45 cells): within the larger of 5% of Lim's value and $5.
- d. Table 5: dollar values within ±10%, funding rates within ±0.7 points, break-even Sharpes within ±0.15.
- e. Table 6 (9 cells): within the larger of 10% and $10.
- f. Student-t step-one pass probabilities (0.273 and 0.503): within ±0.01.

**Verdict:** REPRODUCED if (a), (b) and (f) hold in full, at least 41 of the 45 cells of (c) hold, every item
of (d) holds and at least 8 of the 9 cells of (e) hold. Otherwise PARTLY REPRODUCED, with every miss listed.
A miss is reported, not tuned away, and no convention is changed after the first run.

**V2: rule text verbatim** (`research/validate_rules.py`). Each phrase quoted in
`RULES_alpha_swing_2026-10-13.md` is searched for in the raw text of its source page, fetched directly with no
summarising reader. The raw pages are saved locally (not committed) and their SHA-256 hashes recorded. A phrase
not found verbatim is replaced in the rules record by the page's own wording. If a correction changes a
modelled rule, that is flagged and the affected results are re-run before any drafting.

### Amendment 2 (2026-10-13, written and pushed before the runs it describes): horizon grid and other books
**Reason:** the author chose the framing "fair on paper" and asked for a study of journal standard. Two of the
agreed additions use the existing simulator and are fixed here: K5 (how the horizon sets the value of sizing
against skill) and K6 (whether the no-skill value is specific to one US500 trade). The optimal-policy analysis,
the plan menu and the real strategies will be fixed in later amendments, each before its own run. Script:
`research/run_K_ext.py`.

**What is already known, so that it is not presented as a prediction:** with policies fixed at the 36-month
selection, the exploratory table gives D = +$9 at 12 months, −$52 at 24 and −$112 at 36, and robustness row 5
gives −$194 at 60 months; K2 row n shows the classic maturities halving the coin flip's value at a fixed policy.
New in K5: the classic clock across the whole map, policies re-selected in every cell, and no cut-off on the
evaluation.

**K5: the horizon grid (FTG regime)**
- **Contract clock:** none (as written) or the classic step maturities of 30 and 60 trading days.
- **Value window:** payouts requested within 12, 24, 36 and 60 months of purchase (252, 504, 756, 1,260 trading
  days). One simulation with a 1,260-day window gives all four.
- **No evaluation cut-off:** the evaluation may run for the whole window (K1 stopped it at 504 days). Purchase
  days are those on which a 1,260-day window fits, as in robustness row 5. The (no clock, 36 months) cell is
  therefore not K1's number; both are reported and the difference is attributed.
- **Skill:** coin flip, S = 0, 0.3 and 1.0. Sizing grid and funded risks as in K1 (FTG: 0.5% and 1%).
- **Policies:** selected on the selection set (seed 20261013) separately for every clock, window and skill;
  reported on the evaluation set (seed 20261014). The conventional policy is 1% and 1%.
- **Outcome per cell:** P(pass), share of purchases still in evaluation at the end of the window, V with its
  interval, the selected policy, and D = [V(coin, selected) − V(coin, 1%/1%)] − [V(S = 0.3, selected) −
  V(coin, selected)], paired by path.
- **Hypotheses:**
  - **H4:** with the classic clock and a 12-month window, D > 0 (sizing is worth more than a Sharpe of 0.3).
  - **H5:** with no clock and a 60-month window, D < 0.
  - **H6:** under each clock, D falls as the window lengthens (12 → 24 → 36 → 60 months).
  - **H7:** at every window, D is larger with the clock than without it.
- **Verdicts:** as in section 5 for H4 and H5. H6 and H7 are SUPPORTED if every paired difference they name has
  a 95% interval on the stated side of zero, REFUTED if any lies wholly on the other side, otherwise
  INCONCLUSIVE. The two clocks use the same purchase days and uniforms, so H7 is paired by path.
- **Also reported, without a hypothesis:** the same table with the skill gain measured from S = 0 instead of
  from the coin flip, and the value of a skilled buyer at the conventional policy against the coin flip at its
  selected policy, in every cell.

**K6: the same contract on other books (FTG regime, 36 months, K1's conventions)**
- **Books:** the Z2 design unchanged (one trade every London weekday, 14:30 → 20:30, stop 1 × ATR(14) of the
  previous broker day, both sides simulated, ACG median spread by hour × 1.5) on NAS100_USD, EUR_USD and USD_JPY.
  These are the instruments with 30-minute data and measured costs outside US500 that span a second index and
  two currency majors. Indices carry no commission; the standard account carries none on currencies either.
- **Leverage and lots as published:** evaluation leverage 1:10 on indices and 1:30 on currencies. Funded
  exposure is the smaller of the lot cap and the leverage limit: FTG 1.25 lots with 1:5 on indices and 1:15 on
  currencies. One index lot is one index unit; one currency lot is 100,000 units of the base currency. The lot
  cap is converted to leverage at each instrument's reference price. FTG position cap 1%.
- **Skill:** coin flip and S = 0.3, each calibrated on that book's own outcomes. Selection and evaluation sets
  and the sizing grid as in K1; funded risks 0.5% and 1%.
- **Gate:** each book must trade often enough that the 30-day inactivity rule cannot bind (longest gap between
  trade days under 25 calendar days). A book that fails is reported and dropped.
- **Outcome per book:** cost of a coin-flip trade in stop units and its net Sharpe, the selected policy,
  P(pass), V with its interval, V at 1%/1%, V at S = 0.3, D, and the coin flip's V with costs set to zero.
- **Hypotheses:**
  - **H8 ("about 1% of the account" is not specific to US500):** for every book the coin flip's V at its
    selected policy lies between $75 and $130.
  - **H9 (H2's refutation carries over):** D < 0 in every book.
- **Verdicts:** H8 is SUPPORTED if every book's 95% interval lies inside the band, REFUTED if any book's
  interval lies wholly outside it, otherwise INCONCLUSIVE. H9 as H2, book by book; it is SUPPORTED only if D is
  below zero in all three.

### Amendment 3 (2026-10-13, written and pushed before any K7 code was run): the buyer's best policy
**Reason:** K1 prices fixed-size policies. A contract's value is properly its value under the buyer's best
play, and both Lim and Villahermosa list state-dependent sizing as an open limitation. K7 solves for that
policy and measures what it adds. Code: `propcontract/optimal.py`, `research/run_K7.py`.

**The decision problem**
- **Contract:** Alpha Swing $10k exactly as in K1 (both funded regimes), including K1's conventions: payouts
  requested within 756 trading days of purchase, evaluation cut-off at 504 days, 2 idle days after step 1,
  3 before the funded account, 2 locked days after a payout.
- **Objective:** the expected sum of payouts. No discounting, no risk aversion.
- **State:** stage (step 1, step 2, funded), days since purchase, the balance, and in the funded stage the best
  day since the last payout.
- **Choices each day:** the intended risk of the day's trade, from 0.25% to 5% in steps of 0.25% plus 6% and 8%
  in the evaluation; 0.25%, 0.5%, 0.75%, 1% when funded in the FTG; 0.5% to 2.5% in steps of 0.5% when funded
  in the STD regime. In the funded stage, also whether to request a payout at a close where one is allowed.
  The published caps apply to whatever is chosen, as in K1.
- **Model of a day:** each day is an independent draw from the book's own history (every business day of the
  development sample, both sides of every trade, with the stop distance of that day). A buyer of skill p gets
  the better side with probability p. The trade must be taken; only its size is chosen.
- **Not in the state:** the three-day minimum (K2: worth $0.36). It is enforced when the policy is simulated.
- **Solution:** backward induction on a dollar grid ($5 steps for the balance, $10 for the best day; funded
  profit capped at +$3,000). Each day's outcome is split between the two nearest grid points so that its mean
  is exact. The policy is exact for this model and grid. On real paths it is one admissible policy, so its
  realised value is a lower bound on the true optimum there.

**Policy classes, each solved and then simulated on K1's evaluation paths (seed 20261014)**
- A. K1's selected fixed policy (already computed).
- B. A's sizes, with payout timing free.
- C. Sizing free, payout at the first close that allows it.
- D. Sizing and payout timing both free.
- Skill: coin flip, S = 0.3 and S = 1.0. Regimes: FTG (primary) and STD.

**Gates before any K7 result is read**
- **G4:** a policy table holding one size, with the earliest payout, reproduces `contract.evaluate` and
  `contract.fund` path by path.
- **G5:** the solver's value for A's fixed policy equals a simulation of that policy on independent draws
  (200,000 paths) within three standard errors plus 2%.
- **G6:** the solver's value for D equals a simulation of D's policy on independent draws within three standard
  errors plus 2%, and halving the grid steps moves D's value by less than 2% (coin flip, FTG).

**Hypotheses (evaluation paths, 95% intervals paired by path)**
- **H10 (state-dependent play is worth having without skill):** for the coin flip in the FTG, D's realised
  value exceeds A's by more than 10%: V_D − 1.10 · V_A > 0.
- **H11 (bold without skill, timid with it):** the average evaluation risk actually used under D falls with
  skill: coin flip > S = 0.3 > S = 1.0 (FTG). Tested on the two adjacent differences of per-path averages.
- **H12 (independent days are an adequate model):** for the coin flip in the FTG, the solver's value for D is
  within 10% of D's realised value on real paths. Reported as the ratio with its interval; SUPPORTED if the
  interval lies inside 0.90 to 1.10, REFUTED if wholly outside, otherwise INCONCLUSIVE.
- **H13 (waiting pays only with skill):** free payout timing adds less than 2% of V_A for the coin flip
  (V_B − 1.02 · V_A < 0, FTG) and more than 5% for S = 1.0 in the STD regime (V_B − 1.05 · V_A > 0). Both
  parts must hold.
- My expectation before running: H10 near its threshold, H11 and H13 likely, H12 uncertain (the 21-day block
  bootstrap moved the coin flip's value by 7%). Each is reported as found.

**Also reported, without a hypothesis**
- Every class in both regimes for all three skill levels, with P(pass), P(any payout) and payouts per paid buyer.
- A description of D's policy: size against distance to the floor and to the target in each step, and the
  profit at which payouts are taken.
- How far D's sizes move: the ratio of the largest to the smallest size used on a path, because the firm's
  gambling policy names "a significant change in lot size compared to the overall average on the account".
- The share of funded days on which D's profit sits at the +$3,000 cap.

### Amendment 4 (2026-10-13, written and pushed before any K8 code was run): the firm's plan menu
**Reason:** K1 to K7 price one plan. The firm sells eight, at very different fees, under one rulebook. Pricing
all of them the same way shows whether the price list follows contract value, which is the part of the study
that speaks to the firm's side. Rules: the saved help-centre pages (`SOURCES_alpha_2026-10-13.json`). Fees: the
checkout list prices in `FEES_alpha_2026-10-13.json`. Script: `research/run_K8.py`.

**Already seen, so not a prediction:** Alpha Pro 10% has the same targets and loss limits as Swing at about half
the fee ($77 against $147 at $10k), with twice the lot cap. No Pro, One or Direct plan has been priced.

**Plans, per $10k account, as published**
| Plan | Steps and targets | Overall loss | Daily loss | Lots (standard; restricted) | Index leverage | Payout | List fee |
|---|---|---|---|---|---|---|---|
| Swing | 10%, then 5% | 10% static | 5% | 2.5; 1.25 | 1:10; 1:5 | On demand | $147 |
| Pro 10% | 10%, then 5% | 10% static | 5% | 5; 2.5 | 1:20; 1:10 | On demand, or bi-weekly | $77; $87 |
| Pro 8% | 8%, then 5% | 8% static | 4% | 5; 2.5 | 1:20; 1:10 | On demand | $57 |
| Pro 6% | 6%, then 6% | 6% static | 3% | 5; 2.5 | 1:20; 1:10 | On demand | $47 |
| One 6% | 6% | 4% trailing | 3% (4% when funded) | 5; 2.5 | 1:10; 1:10 | On demand | $67 |
| One 10% | 10% | 6% trailing | 4% | 5; 2.5 | 1:10; 1:10 | On demand | $87 |
| One 12% | 12% | 8% trailing | 5% | 5; 2.5 | 1:10; 1:10 | On demand | $107 |
| Direct | none (funded from purchase) | 5% trailing | 3% | 5 | 1:10 | On demand, 90% split | $97 |

**Rules as modelled (additions to K1's)**
- **Trailing loss limit:** the floor is the highest end-of-day balance minus the limit, capped at the initial
  balance; equity at or below it closes the account. A payout does not lower it.
- **On demand (Swing, Pro, One):** as in K1: profit of at least 2%, best day at most 40% of the profit, 80% split,
  2 locked days.
- **Bi-weekly (Pro 10% only here):** every 10 funded trading days, profit of at least $100, no best-day rule.
- **One, after a payout:** the balance returns to the initial balance plus whatever profit the buyer leaves in.
  A buyer who withdraws everything once the floor has reached the initial balance loses the account, as the
  help centre states. The profit left in (0%, 2% or 4%) is part of the policy; a payout needs 2% above it.
- **Direct:** no evaluation. A 3% profit buffer must stay in the account; a payout needs 1% above it; best day at
  most 15% of the profit of the current payout window; 90% split; Max Risk Rule 1%.
- **Max Risk Rule** 3% on the other plans at $10k. **Minimum trading days** 3 a step (1 on One).
- **Restricted regime (FTG):** half the lots, the leverage shown, 1% position cap. The trigger about intraday use
  of a swing account does not apply to Pro, One or Direct, but "an all-or-nothing style approach", "excessive
  max lot / max margin usage" and account rolling do. Both regimes are reported; FTG stays primary. Direct has
  one regime, because its 1% Max Risk Rule already binds below the FTG cap.
- **Not modelled:** the 5-minute news window and the weekend rule of Pro, One and Direct (the book enters at
  14:30 London and is flat by 20:30), and everything K1 lists as not modelled.

**Design**
- Book Z2 on US500, K1's conventions: 36-month window, evaluation cut-off at 504 days, selection set (seed
  20261013) for the policy and evaluation set (seed 20261014) for every reported number, 50,000 paths each.
- Skill: coin flip and S = 0.3. Evaluation risk on K1's grid. Funded risk 0.5% or 1% in the FTG; 0.5% to 2.5% in
  the standard regime; 0.25%, 0.5%, 0.75% or 0.9% on Direct.
- **Outcome per plan and regime:** the selected policy, P(pass), P(any payout), V with its interval, the fee,
  EV = V − fee and V per dollar of fee. Then the same against each plan's fee at every account size, using the
  fact that the rules scale with the account (the $100 bi-weekly minimum and the 2% Max Risk Rule from $50k do
  not; the bi-weekly row is reported at $10k only, and the standard regime is re-run with the 2% rule).

**Hypotheses (coin flip, FTG, $10k, evaluation set, 95% intervals; differences paired by path)**
- **H14 (the cheaper twin is worth at least as much):** V(Pro 10%, on demand) − V(Swing) > 0.
- **H15 (positive at list on the smallest popular size):** V(Pro 10%, on demand) > $77.
- **H16 (the fee list does not follow value):** Swing has the lowest V per dollar of fee among the seven plans
  with an evaluation. SUPPORTED if Swing's ratio is below every other plan's with non-overlapping intervals,
  REFUTED if any plan's ratio is below Swing's with non-overlapping intervals, otherwise INCONCLUSIVE.
- **H17 (one step with a trailing limit is worth less than two steps with a static one):**
  V(One 10%) − V(Pro 10%, on demand) < 0.
- **H18 (the instant account is a losing purchase without skill):** V(Direct) < $97.
- My expectation before running: H14 and H15 likely, H16 likely, H17 and H18 uncertain. Each is reported as found.

**Gates:** unit tests for the trailing limit, the retained buffer and the cash-out closure on paths with known
answers; the original gates G2 and G3 re-run after the simulator is extended; the Swing row must reproduce K1's
selected values to the cent.

### Amendment 5 (2026-10-13, written and pushed before any K9 code was run): real strategies through the contract
**Reason:** K1's skilled buyer is idealised: the edge arrives every day, at full size, almost free. K9 asks what
the contract is worth to the strategies this programme actually produced. Script: `research/run_K9.py`.

**Already known, so not a prediction:** S1 ran A1b through an older simulator (payout checks every 21 days,
funded risk 0.66%) and found mean payouts of about $200 on 2017–21 purchases, concentrated in 2017–18. No
strategy has been run through the contract as written.

**Books: the forward-watchlist candidates, the only strategies the programme carried into a forward test**
- **A1b:** the pre-fix long-USD leg (07:00 → 13:00 London), chosen after the A1 result was seen.
- **A2b:** the month-end reversal after the 16:00 fix (failed discovery, p = 0.10).
- **M1r:** fade the macro surprise (14:30 → 21:00 London), chosen after the M1 result was seen.
- **R3:** A2b + M1r, the ensemble tested on untouched 2017–24 data in batch R.
- **W3:** all three together.
- Each is built by its own committed builder, unchanged, at ACG costs × 1.5, on the development sample.
- **None of these is a confirmed edge.** A1b and M1r were selected after seeing 2005–2016, so their values on
  purchases from those years are in-sample and flatter them.

**From trades to days**
- Each book becomes one series per business day at one unit of risk per trade: the day's change in marked value
  of all open trades, and the worst intraday mark relative to the day's opening value (the sum of each open
  trade's worst mark, floored at zero each, so lows are assumed to coincide).
- Sizing is a fixed fraction of the initial balance per trade, as in K1.
- **Evaluation:** Swing rules as in K1. Total notional may not exceed 30 times the account (currency leverage).
- **Funded, FTG regime:** the risk of all open positions together may not exceed 1% of the initial balance, and
  total notional may not exceed the smaller of 1.25 lots and 15 times the account, as published.
- **Assumed:** a token trade keeps the account active through flat spells (the longest spell is reported);
  payouts are requested at closes even if a position is still open; after a step is passed the book carries on
  mid-trade. These favour the books slightly.

**Design**
- Purchases on every business day on which a 756-day window fits. Two groups, as in robustness row 3:
  2005-02 → 2014-02 ("early", windows inside the years the ideas were selected on) and 2017-01 → 2021-11 ("late").
- Per-trade risk in the evaluation from {0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4, 6, 8, 12, 16}%; funded intended
  risk from {0.1, 0.25, 0.5, 1}%. The policy is selected on the early group and held for the late group.
- **Outcome per book and group:** net annualised Sharpe of the daily series, trades a year, P(pass), median
  months to pass, share still in evaluation at 504 days, P(any payout), V, and the value of K1's idealised
  buyer at the same net Sharpe on the same group of purchase days (interpolated on K1's skill grid, FTG).
- **Intervals:** purchases on neighbouring days share most of their path, so 95% intervals come from a
  stationary bootstrap of the purchase days (mean block 252 days, 5,000 draws).

**Hypotheses**
- **H19 (a real edge is worth less than an idealised one):** for every book, in the late group, V is below the
  idealised value at the same Sharpe. SUPPORTED if every book's interval for the difference lies below zero,
  REFUTED if any lies wholly above, otherwise INCONCLUSIVE.
- **H20 (and less than a well-sized coin flip):** in the late group, the best of the five books is worth less
  than the coin flip's K1 value on the same group of purchase days ($96). Verdict from the interval of the
  best book's V against $96.
- **H21 (decay):** every book is worth less on late purchases than on early ones. Verdict from the difference
  of the two group means with their bootstrap intervals, book by book.
- My expectation before running: H19 likely, H21 likely, H20 uncertain. Each is reported as found.
