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
- FPFX Tech (7% of 300,000 accounts paid, average payout 4% of plan size, average fee $100): reported by
  Finance Magnates; the original report was not found.
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

## What is still unchecked
1. The specific claims attached to citations (other than the one above) have not been checked against each
   paper's text. Chague et al.'s figures in particular are from memory, because SSRN blocks the abstract page.
2. The 24 tests have had one internal audit (2026-09-26) and no outside one.
3. Costs come from one broker's account in 2026, applied to 2005–2024 in proportion to price.
4. Nobody outside the project has re-run anything. A public repository with a one-command reproduction is the fix.
