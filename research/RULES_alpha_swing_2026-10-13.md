# Alpha Swing rule set as read at source on 2026-10-13 (the contract priced in Paper 2)

Every row was fetched on 2026-10-13 from Alpha Capital Group's help centre (`help.alphacapitalgroup.uk`) or its
Terms and Conditions (`alphacapitalgroup.uk/terms-and-conditions`). "Page date" is the date shown on the article.

**Verified verbatim on 2026-10-13 (plan amendment 1, V2).** The first reading went through a summarising reader.
The pages were then fetched directly and all 28 quoted phrases were found word for word in the raw page text
(`research/validate_rules.py`). All 64 articles in the help centre's rule-bearing collections were also saved
and read (`research/fetch_help_centre.py`). Page hashes are in `research/SOURCES_alpha_2026-10-13.json`; the raw
pages are kept locally. That reading found four published terms this record had missed, listed in the last
section. None changes a modelled rule.

## Evaluation
| Rule | As written | Source (page date) | In the model |
|---|---|---|---|
| Targets | "Phase 1 profit target: 10%", "Phase 2 profit target: 5%" | [Alpha Swing](https://help.alphacapitalgroup.uk/en/articles/9789907-alpha-swing) (24 Jul 2026) | +10%, then +5% on a fresh balance, at a close |
| Overall loss | "Max Drawdown (static): 10%" | Alpha Swing | Floor at 90% of initial, on the worst intraday mark |
| Daily loss | "Max Daily Drawdown (balance-based): 5%"; reference is the balance at 00:00 GMT+3; "breaches are always applied based on open trades (unrealised losses)" | [Daily Risk Limits](https://help.alphacapitalgroup.uk/en/articles/6934210-what-are-the-daily-risk-limits-and-how-do-they-work) (24 Jul 2026) | Floor at 95% of the day's opening balance, on the worst intraday mark |
| Minimum days | "Minimum trading days (for each phase): 3" | Alpha Swing | 3 days with a trade per step |
| Time limit | "There are no time limits applicable to the Evaluations" | T&C §8.2.1 | None; analysis horizon 504 trading days |
| Position size | "There is no maximum virtual position size exposure during the evaluation stage" | T&C Schedule 2 §3.4(a) | No lot cap |
| Leverage | FX 1:30, metals 1:9, indices 1:10, oil 1:10 | Alpha Swing | Notional ≤ 10 × initial |
| Inactivity | More than 30 consecutive days without trading deactivates the account; "All accounts, at all stages" | [Inactivity](https://help.alphacapitalgroup.uk/en/articles/8420080-inactivity) (6 Jul 2026) | Cannot bind on a daily book (checked) |
| Refund | The T&C set out no refund of the evaluation fee on passing | T&C §11, §16 | No refund |

## Qualified (funded) account
| Rule | As written | Source (page date) | In the model |
|---|---|---|---|
| Lot cap | Swing: $5k 1.25, $10k 2.5, $25k 5, $50k 10, $100k 20, $200k 40, $300k 60 lots; "the total combined lots/position size allowed at any one time"; first violation: the fee earned on the excess is not withdrawable; second: account deactivated | [Lot size limit](https://help.alphacapitalgroup.uk/en/articles/6934289-what-is-the-lot-size-limit-on-qualified-analyst-accounts) (21 Jul 2026); Alpha Swing | STD regime: notional ≤ 2.5 lots × price |
| Max Risk Rule | "applies to Qualified Accounts only"; accounts bought after 21/07/2026; 3% for $5k–$25k, 2% for $50k–$200k; per asset, on "floating/unrealised losses"; breach closes the account | [Max Risk Rule](https://help.alphacapitalgroup.uk/en/articles/15888623-what-is-the-max-risk-rule-and-how-does-it-work) (25 Aug 2026) | Account closed when the open loss reaches 3% of initial |
| Payout type | "Swing accounts are only available with the On-Demand payout type" | T&C Schedule 3; Alpha Swing | On demand |
| Minimum profit | "a minimum of 2% of gross profits on the account balance" | [On-Demand performance fee](https://help.alphacapitalgroup.uk/en/articles/10102634-performance-fee-on-demand) (22 Jul 2026); T&C Schedule 3 | Profit ≥ 2% of initial |
| Best Day Rule | 40% for Swing: "no single trading day should contribute more than a set percentage of the total generated profits"; a withdrawal resets the score | On-Demand performance fee; T&C Schedule 3 | Best day since the last payout ≤ 40% of the profit |
| Request timing | No minimum interval is stated. All trades must be closed. "processed and paid within 2 business days"; "You can resume trading once your account balance has been reset" | [How do I get paid](https://help.alphacapitalgroup.uk/en/articles/6933755-how-do-i-get-paid-performance-fees) (7 Jul 2026) | Requested at the first eligible close; 2 trading days locked; balance back to initial |
| Split | "an 80% share of the profits" (90% with a paid add-on) | [What do Qualified Analysts earn](https://help.alphacapitalgroup.uk/en/articles/7060937-what-do-qualified-analysts-earn-from-account-profits) (21 Jul 2026) | 80% |
| Floors | Same static and daily limits as the evaluation | Alpha Swing; Daily Risk Limits | Same |

## Focused Trader Group (FTG)
Source: [Focused Trader Group](https://help.alphacapitalgroup.uk/en/articles/9691161-focused-trader-group) (7 Sep 2026);
T&C Schedule 2 §3.5.
- "a temporary group into which Qualified Analyst accounts may be moved".
- **Triggers that fit the book priced here:** "Using a swing trading account primarily for scalping or frequent
  intraday strategies, without any swing trading activity"; "Excessive max lot / max margin usage"; account
  rolling, described as taking full risk on evaluation or qualified accounts to pass or fail.
- **Restrictions on Swing:** lot caps halved ($10k: 1.25 lots); leverage 1:5 on indices; "the maximum allowable
  risk for any single position is 1% of your initial balance"; after a loss of 1% or more on a symbol, no new
  trade on it until the next trading day; no EAs.
- **In the model:** funded risk = min(intended, 1%, 1.25 lots). The primary regime.

## Discretion (not modelled)
- Gambling policy ([article](https://help.alphacapitalgroup.uk/en/articles/7060909-what-is-alpha-capital-group-s-policy-against-gambling-in-trading),
  6 Jul 2026), on Qualified accounts: "A significant change in lot size compared to the overall average on the
  account"; "all or nothing" strategies; consequence "the removal of profits" and possibly closure.
- T&C Schedule 2 §3.2: Qualified Analysts must "maintain the same level of risk".
- T&C Schedule 2 §2.6: the fee "will not be paid where we ascertain, in our sole discretion" that trades breached
  the rules.

## Fee
List prices for Alpha Swing, read off the checkout page by the author on 2026-10-13:

| Account | $5,000 | $10,000 | $25,000 | $50,000 | $100,000 | $200,000 |
|---|---|---|---|---|---|---|
| List fee | $70 | $147 | $247 | $357 | $577 | $1,097 |
| List fee as % of account | 1.40% | 1.47% | 0.99% | 0.71% | 0.58% | 0.55% |
| With code ALPHA20 | $56.00 | $117.60 | $197.60 | $285.60 | $461.60 | $877.60 |
| Best coded fee as % of account | 1.12% | 0.40% | 0.79% | 0.57% | 0.46% | 0.44% |

- Codes tried at checkout by the author on 2026-10-13: ALPHA20 takes 20% off every Swing size; 10KFOR40 still
  brings the $10k to $40 (the best coded fee in that column); FUNDED40 is live but limited to Alpha Direct.
- Codes come and go, so the paper reports the list fee as the base case and coded fees as dated examples.
- The fee per dollar of account falls by more than half from $10k to $100k, while every limit in the contract
  scales with the account. The exception is the Max Risk Rule: 3% up to $25k, 2% from $50k.

## Found on the direct reading of 2026-10-13 (amendment 1, V2)
**Published terms the record had missed**

| Term | As written | Source (page date) | Effect on the model |
|---|---|---|---|
| Fourth-payout bonus | "on the fourth performance fee request, a discretionary bonus of 0.25% of the initial account size is applied"; "only applicable to the fourth performance fee payment" | [Performance fee bonus](https://help.alphacapitalgroup.uk/en/articles/8420537-what-is-the-performance-fee-bonus) (7 Jul 2026) | Not in V, because it is discretionary. Priced separately (`research/info_K_bonus.py`) as 0.25% × P(four or more payouts): $0.85 for the coin flip, $3.13 at a Sharpe of 0.3, $10.74 at 1.0 (FTG), which is 0.3% to 1.2% of V at every skill level |
| Scaling plan | Swing is eligible. At a 10% gain the trader "can request scaling"; the balance and the drawdown allowance grow by 10% of the initial balance; "accounts under the Focused Trader Group need to be moved back to normal leverage before they can participate" | [Scaling plan](https://help.alphacapitalgroup.uk/en/articles/6933852-how-does-the-scaling-plan-work) (24 Jul 2026) | Not modelled. It cannot help a buyer who takes each payout at 2%, and it is closed to the FTG. For a skilled buyer in the STD regime the reported values are lower bounds |
| Allocation caps | "a maximum allocation of $400,000 per household"; "a $300,000 limit per strategy; we define 'strategy' as the assets themselves"; evaluation accounts "have no maximum allocation" | [How many accounts](https://help.alphacapitalgroup.uk/en/articles/8804535-how-many-accounts-can-i-have-what-is-the-maximum-allocation-per-strategy) (6 Jul 2026) | No effect on one purchase. It caps funded capital on one asset at $300k, which bounds any repeat-purchase argument |
| Review on passing | "All passed evaluations are subject to review, and traders found guilty of policy ignorance or abuse will not advance to the Qualified phase"; credentials within "a maximum of 2 working days" | [Prohibited strategies](https://help.alphacapitalgroup.uk/en/articles/6934275-what-are-prohibited-trading-strategies); [After passing](https://help.alphacapitalgroup.uk/en/articles/7060904-what-happens-once-the-evaluation-process-is-passed) (23 Jul 2026) | Discretion applies at the pass as well as at each payout. Not modelled; the 3-day gap before funding already covers the delay |

**Confirmations and fuller wording**
- **No refund:** "All our evaluation plans are non-refundable"
  ([article](https://help.alphacapitalgroup.uk/en/articles/8420592-is-it-possible-to-receive-a-refund-for-the-evaluation-fees-once-i-have-completed-my-evaluation),
  6 Jul 2026). A third-party comparison site says fees are refunded on the fourth payout; the firm's own page
  says otherwise, and the firm's page is the one used.
- **No commission on indices:** "Indices are commission-free across both account types"
  ([article](https://help.alphacapitalgroup.uk/en/articles/8420066-are-there-commission-fees), 6 Jul 2026). So
  the spread is the whole trading cost of the US500 book.
- **"Same level of risk", in full** (T&C Schedule 2 §3.2): "A Qualified Analyst is required to maintain the same
  level of risk on a Qualified Analyst Account (i.e. if a Qualified Analyst had a $100k exposure, they will need
  to maintain a $100k exposure on their Qualified Analyst Account), a breach of the risk will result in instant
  termination of the Services". The help centre adds: "You are required to maintain the same level of risk in
  accordance with your selected evaluation plan"
  ([article](https://help.alphacapitalgroup.uk/en/articles/6933909-are-there-any-profit-targets-on-a-qualified-analyst-account),
  6 Jul 2026). The clause does not say what the risk is compared with. A buyer who keeps the same risk in both
  stages loses almost nothing in the STD regime (2.5% in both: $147 against $148 at the selected policy); in the
  FTG the firm's own 1% cap forces the change.
- **Trading day:** "a day on which you open and close a trade on the same day"
  ([article](https://help.alphacapitalgroup.uk/en/articles/6933908-if-i-pass-before-the-minimum-trading-days-what-is-required-for-the-remaining-days),
  6 Jul 2026). The intraday book qualifies.
- **Max Risk Rule cool-down:** a trade re-opened on the same asset in the same direction within 10 minutes has
  its loss added to the previous one. It cannot bind with one trade a day.
- **News rule on Swing:** a trade opened within 2 minutes of a release must last more than 2 minutes. Not modelled.
- **Payout review:** "the profits from invalid trades or the entire profits from that payout window (depending
  on the type of breach) will be removed, and the remaining payout will be postponed" (How do I get paid).
- **Static floor on equity:** "If the balance or equity drops below $90,000, the account is breached"
  ([Maximum total loss](https://help.alphacapitalgroup.uk/en/articles/6934220-what-is-the-maximum-total-loss),
  24 Jul 2026), as modelled.

## Details recorded for the first time on this reading
These were not in the spec's rule table of 24–29 September. The page dates show they are not new rules.
- The Max Risk Rule threshold depends on account size (3% up to $25k, 2% from $50k).
- The Focused Trader Group halves the Swing lot caps and sets index leverage to 1:5.
- The On-Demand article and the payout article state no minimum interval between requests.
