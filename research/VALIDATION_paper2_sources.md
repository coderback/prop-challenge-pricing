# Paper 2: validation of outside sources (2026-10-13)

- Plan: amendment 1 to `PREREGISTRATION_paper2_contract_map.md`, commit 5338ffe, pushed before the runs.
- Scripts: `research/validate_lim.py`, `research/validate_rules.py`, `research/fetch_help_centre.py`,
  `research/info_K_bonus.py`. Logs in `data/logs/validate_*.log`; tables in `data/checks/V1_lim_*`, `K_bonus.csv`.
- Purpose: nothing the paper quotes from someone else should rest on an unchecked claim.

## Summary
| Source | What the paper takes from it | Check | Result |
|---|---|---|---|
| Alpha Capital Group's rules and terms | The contract being priced | Every quoted phrase searched for in the raw page text; all 64 rule articles read | **Verified.** 28 of 28 quotes word for word. Four published terms had been missed; none changes a modelled rule |
| Lim (2026), SSRN 7178078 | Comparison model, and the numbers we quote from it | Independent re-implementation from his text, 200,000 paths per stage | **Reproduced, with one definitional difference** (below). Formal verdict under the pre-stated rule: partly reproduced |
| Villahermosa (2026), SSRN 7445798 | Prior claims only | Arithmetic from his own reported inputs | **Internally consistent; not verifiable.** No code or data are released |
| Darmanin (2026), arXiv 2607.20093 | A reporting convention only | Status and availability | **Not validated, and not relied on** for any number |
| Industry funnel figures (FPFX, Topstep, FTMO) | Possible seller's-side comparison | Search for primary sources | **Second-hand so far.** Not to be cited until each primary source has been read |
| Our own simulator | Every result | Three independent cross-checks | **Agrees** with an older simulator path by path, with S2 exactly, and with Lim's tables by two routes |

## V2: Alpha's rules
- **Verbatim:** all 28 phrases quoted in the rule record appear word for word in the raw text of their source
  pages, fetched directly. A further 16 phrases added on this reading were checked the same way; three needed a
  capital letter corrected.
- **Coverage:** all 64 articles in six collections (plans, trading rules, general, evaluation, qualified analyst,
  trading terms) were saved and read. Page hashes: `research/SOURCES_alpha_2026-10-13.json`.
- **Missed by the first reading** (details and wording in `RULES_alpha_swing_2026-10-13.md`):
  1. A discretionary bonus of 0.25% of the account on the fourth payout.
  2. A scaling plan (Swing is eligible; closed to accounts in the restricted group).
  3. Allocation caps: $400,000 a household and $300,000 an asset across funded accounts.
  4. A review of every passed evaluation before the funded account is issued.
- **Effect on results:** none of the four changes a modelled rule.
  - The bonus would add $0.85 to the coin flip's $103, $3.13 at a Sharpe of 0.3 and $10.74 at 1.0, which is
    0.3% to 1.2% of V at every skill level in both regimes. It is reported beside V because it is discretionary.
  - The scaling plan makes the skilled values in the standard regime lower bounds.
  - The re-run for the bonus reproduced every selected K1 value to the cent.
- **Confirmed:** the evaluation fee is not refundable (a third-party site says otherwise; the firm's own page
  is used); indices carry no commission, so the spread is the whole cost of the book.
- **Fees confirmed at a second primary source:** the firm's home page carries a machine-readable plan table
  (51 plans; raw page saved, SHA-256 `009d42b9…2696e`). Its six Swing prices are exactly the list fees the
  author read at checkout ($70, $147, $247, $357, $577, $1,097), and its Swing targets and limits match the
  rule record. The same table prices the Pro, One and Direct plans, which is the input K8 needs; what its
  three price fields mean for those plans still has to be confirmed at checkout.
- **Still a matter of reading:** "maintain the same level of risk" does not say what the risk is compared with.
  Keeping the same risk in both stages costs about $1 of $148 in the standard regime.

## V1: Lim's model, re-implemented from his text
| Target | Tolerance set beforehand | Result |
|---|---|---|
| Table 2, six simulated cells | ±0.01 | 6 of 6; largest difference 0.002 |
| Table 3, 45 cells | ±0.01 | 45 of 45; largest difference 0.002 |
| Anchors at zero skill, 2% volatility | ±5%, ±0.02 | Expected payouts $7,273 (his "roughly $7,300"), P(payout) 0.561 (0.56), fair fee $1,483 ($1,502) |
| Table 4, fair fee, 45 cells | larger of 5% and $5 | 45 of 45; largest difference 2.2% where his value is $100 or more |
| Table 5, ten quantities | ±10%, ±0.7 points, ±0.15 | 10 of 10. Non-refundable value $203.04 ($203); no time limit $369.89 ($369); funding rates 7.52% and 10.48% (7.5%, 10.5%) |
| Table 6, nine cells | larger of 10% and $10 | **7 of 9.** Low-cost cells: $392 against $441 and $498 against $557 |
| Student-t check | ±0.01 | 0.273 and 0.503 (0.273, 0.503) |

- **Formal verdict: PARTLY REPRODUCED**, because Table 6 needed 8 of 9. The day-250 sweep convention makes no
  difference to the verdict.
- **Why the two cells miss (post hoc diagnosis, no new simulation).** We defined the value of the refundable
  contract as expected payouts plus the expected refund of the posted $500 fee. Lim's "average value,
  refundable" is instead the **population mean of the fair fee** of his Table 4. Under his definition all nine
  cells of Table 6 come back within 0.3% (for example $555.7 against $557 and $220.3 against $221).
- **What that means for his headline.** At the posted fee the buyer's expected receipts are $212, not $221, so
  the implied gross margin is 58%, not 56%, and the refund is worth about $9, not $18. His "no cost drag" value
  of $1,098 matches our non-refundable figure ($1,095). None of this changes his conclusions.
- **Net:** his model, his pass probabilities, his fair-fee table and his no-time-limit variant are all
  reproducible from the paper alone. The paper can quote them, with the one definition stated.

## Villahermosa
- Every figure that can be recomputed from his own inputs agrees: the 44.4% ceiling, the three phase ceilings,
  green-day rate squared (34.6%), expected value at three fees (+0.0716, +0.0516, −0.0184 L) and the four
  seller break-even pass rates.
- His empirical inputs cannot be checked: one-minute futures data under licence, no code, evaluation rules read
  off a dashboard on two accounts, and his own two implementations differ on levels (35.6% and 27.8% pass).
- **Use in the paper:** quoted as his reported claims, with those limits stated. No number of ours depends on his.

## Darmanin
- arXiv v1 only (22 July 2026); the comments field reads "Initial draft ... not externally peer reviewed". No
  code or data are linked, and the paper itself says it has no untouched hold-out.
- **Use in the paper:** the REFUTED / INCONCLUSIVE reporting convention only.

## Industry figures
- FPFX Tech: **read at its trade-press source on 2026-11-08** (Chmiel, "Exclusive: Only 7% of 300,000 Prop
  Trading Accounts Achieved Payouts", Finance Magnates, 18 Sep 2024; raw page in
  data/sources/seller_side_2026-11-08/, SHA-256 b6c12a49...3163f). Verbatim: "over 300,000 accounts belonging to
  100,000 traders from 10 different prop trading companies"; "14% of traders passed the challenge and obtained a
  funded account"; "about 45% achieved a payout (7% of all traders)"; "the average payout being 4% of the plan
  size". **The 7% is per trader, not per account** (the headline says accounts; the body says traders). No
  period is given, and 4% may be per payout or per paid trader. The $100 average fee is NOT in this article; it
  is in the 18 Mar 2025 Finance Magnates piece on The Funded Trader, which the draft had cited and which does
  not contain the ten-firm detail. The paper now cites the 2024 article and reads the figures as about 0.3% of
  an account per trader and about 0.1% per account bought.
- Topstep (16.8% of 2025 evaluations passed, about a third of funded participants paid): on the firm's own site
  according to search excerpts; the page itself has not been read.
- FTMO (2023 revenue $203.9m, operating costs $100.3m): reported by TradeInformer from the firm's statements;
  the filing has not been read.
- **Use in the paper:** only after each primary source is read, and then as "the firm reports".

## Citations (2026-10-13; `research/validate_citations.py`, raw Crossref and arXiv records)
Every citation in Paper 1, the literature review, the pre-registrations of the 24 tests and the references
Paper 2 is likely to reuse was looked up. **All 71 exist, and authors, titles and venues match how we cite them.**

| Group | Checked | Peer-reviewed journal or proceedings | Not peer reviewed |
|---|---|---|---|
| Paper 1 bibliography | 7 | 3 | 4: Andrews (SSRN), Zhang (arXiv), Araci (arXiv, a master's thesis), Gerner et al. (conference paper) |
| Literature review | 25 | 16 | 9: a New York Fed blog post, two NBER and three SSRN working papers, three arXiv preprints |
| Sources of the 24 tests and earlier rounds | 26 | 24 | 2: Brandt et al. (SSRN working paper), Brunnermeier et al. (edited annual volume) |
| Method and background references | 10 | 9 | 1: Dubins and Savage (a book) |
| Prop-firm papers | 3 | 0 | 3: Lim, Villahermosa (SSRN), Darmanin (arXiv) |
| **Total** | **71** | **52** | **19** |

**Paper 1:** all seven references are correct as printed (Goyal, Welch and Zafirov: RFS 37(11), 3490–3557; Meese
and Rogoff: JIE 14(1–2), 3–24; Andrews's initials J.-P.). Gerner et al. is not indexed by Crossref and was not
machine-checked. No change is needed before posting.

**Corrections to make wherever these are cited again**
1. Lopez-Lira and Tang is now published: *Journal of Financial Economics* 184, 104335 (2026). The review cites
   it as a 2023–25 working paper.
2. Liu and Tsyvinski (cited as NBER w24877) is published: *Review of Financial Studies* 34(6), 2689–2727 (2021).
3. Olszweski and Zhou is 2013, not 2014: *Journal of Derivatives & Hedge Funds* 19(4), 311–320.
4. Brandt, Kishore, Santa-Clara and Venkatachalam is an SSRN working paper (first posted 2006), not a journal
   article.
5. Schmeling, Schrimpf and Todorov is published online in *Management Science* (2026), with no volume yet.
6. Lee and Wang is *Review of Asset Pricing Studies* 15(3–4), 247–287 (2025).

The pre-registrations are dated records and are left as written; the corrections apply to the papers.

**What this check does and does not show**
- It shows each work exists, who wrote it, where it appeared and whether that venue referees.
- It does not show that each work says what we say it says. One claim was checked against the source today: the
  New York Fed post states that the 02:00–03:00 window "that previously generated roughly 3.7 percent per annum
  has averaged close to zero since 2021" and that imbalance dispersion fell "from 6.5 percent to 2.9 percent".
  Our wording on who absorbs the imbalances is a gloss and should be tightened if used.
- Peer review is not a guarantee. Twenty-four of the 26 test sources are refereed, and their effects still
  failed at our costs or out of sample. The three papers closest to Paper 2 are all unrefereed, which is why
  Lim's was re-implemented before being relied on.
- **Rule for the papers:** a refereed article is cited as evidence; an unrefereed one is labelled a working
  paper and relied on only where we have reproduced it; every number attributed to a source is checked against
  that source's text at the time of writing.

## Lim (2026b), *Phantom Generosity* (SSRN 7184138), read in full 2026-11-08
- PDF saved by the author at docs/ssrn-7184138.pdf (15 pages, version of 26 July 2026). Not found during the
  October review. Same author, same Brownian engine and benchmark population (net Sharpe mean -1.59, volatility
  mixture), 31 contracts at 21 named firms at the $100k size, list fees of 25-26 July 2026, 300-day evaluation
  cap, 250-day funded horizon, daily-close monitoring, consistency rules and payout caps not priced.
- Alpha in his sample: Pro 8% $527 (value -$246) and One 6% $397 (-$188). **Both fees equal our checkout
  record** (`FEES_alpha_2026-10-13.json`), an independent check of it. On our engine the disciplined coin flip
  has EV +$382 (Pro 8%) and -$67 (One 6%) at $100k: opposite sign on Pro 8% and opposite ranking. Not reconciled
  by a run; the paper says so.
- His findings that overlap ours: fee explains little of value; within-firm cheaper often better; one-step
  trailing contracts pass most and are worth least. He calls endogenising the buyer's volatility policy "the
  natural next step" (our K7). Replication package "available from the author", not public.
- **Use in the paper:** cited as Lim (2026b), reported as he states it; no number of ours depends on it.

## References added 2026-11-08 (Crossref records read; ESMA at EUR-Lex)
- Barber, Lee, Liu & Odean (2014), JFM 18, 1-24, doi:10.1016/j.finmar.2013.05.006
- Brown, Harlow & Starks (1996), JF 51(1), 85-110, doi:10.1111/j.1540-6261.1996.tb05203.x
- Browne (1999), Adv. Appl. Prob. 31(2), 551-577, doi:10.1239/aap/1029955147
- Carpenter (2000), JF 55(5), 2311-2331, doi:10.1111/0022-1082.00288
- Gabaix & Laibson (2006), QJE 121(2), 505-540, doi:10.1162/qjec.2006.121.2.505
- Grossman & Zhou (1993), Math. Finance 3(3), 241-276, doi:10.1111/j.1467-9965.1993.tb00044.x
- ESMA Decision (EU) 2018/796, OJ L 136, 1.6.2018, pp. 50-80 (CELEX 32018X0601(02)): Annex II standard warning
  "Between 74-89 % of retail investor accounts lose money when trading CFDs"; Annex II A(4) requires a
  provider-specific loss percentage; recital 35 lists the national studies. No longer in force since 31 Oct 2018.
- All 31 Paper 2 references are refereed except Lim (2026a, b), Villahermosa, Darmanin (working papers),
  Chmiel (trade press), Dubins & Savage (book) and ESMA (a regulatory decision).

## Rules re-read on 2026-11-08 (`research/recheck_rules.py`, log `data/logs/recheck_rules_2026-11-08.log`)
- 64 articles on both dates, none added or removed; all 28 quoted phrases still verbatim; the terms differ only
  in site navigation.
- 15 articles differ in body text. One change touches a priced rule: the Max Risk Rule (and the same text in
  Alpha Direct) now says trading costs count toward the threshold, and same-direction trades on one asset
  opened within 10 minutes of the previous one closing form one chain. Neither binds: the books open a trade
  on each asset at most once a day, and Direct's selected funded risk is 0.9% against its 1% threshold.
- Wording only: payout examples now say "above its initial balance"; scaling is "10% of the initial account
  balance"; the gambling policy's news-window clause now names Direct; daily reset 00:00 GMT+3 -> GMT+2 (the
  clock change); evaluation start date; IP rule; platform names.
- Fees were not re-read (they need the checkout in a browser).

## What is still unchecked
1. The specific claims attached to citations (other than the one above) have not been checked against each
   paper's text. Chague et al.'s figures in particular are from memory, because SSRN blocks the abstract page.
2. The 24 tests have had one internal audit (2026-09-26) and no outside one.
3. Costs come from one broker's account in 2026, applied to 2005–2024 in proportion to price.
4. Nobody outside the project has re-run anything. A public repository with a one-command reproduction is the fix.
