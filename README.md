# Fair on Paper: reproduction package

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23374897.svg)](https://doi.org/10.5281/zenodo.23374897)

Code, data, analysis plans and results for the working paper

> Ojebiyi, T. O. (2026). *Fair on Paper: What a Prop-Firm Challenge Is Worth, and Who Pays for It.*

The paper prices a named retail prop firm's published evaluation contract on twenty years of intraday index
prices at measured broker costs. Every hypothesis was fixed and committed before its run. Nothing here is
investment advice or a recommendation to buy any product. All values assume the firm pays every valid request.

## Reproduce it

```
pip install -r requirements.txt
python reproduce.py --quick     # about forty minutes: checks that everything runs (5,000 paths, not the paper's numbers)
python reproduce.py             # about two and a quarter hours: every result, table, figure and the PDF
python reproduce.py --check     # compares the regenerated tables with results/reference
```

`python reproduce.py --list` shows the stages; `--only k1 k4` runs selected ones. Python 3.11 or later. The paper
itself rebuilds in seconds from the shipped results: `python paper/prop_contract/make_exhibits.py`, then
`pdflatex main.tex` twice in `paper/prop_contract`.

## What is here

| Path | Contents |
|---|---|
| `propcontract/contract.py` | The contract simulator: evaluation and funded stages, every published rule that is modelled |
| `propcontract/optimal.py` | The buyer's best state-dependent policy by backward induction |
| `propcontract/book.py` | Standalone builder of the one-trade-a-day book from raw 30-minute bars |
| `propcontract/legacy/` | An older, independently written simulator, kept as a cross-check |
| `research/PREREGISTRATION_paper2_contract_map.md` | The analysis plan and its five dated amendments (21 hypotheses) |
| `research/RESULTS_paper2_contract_map.md` | Every result as first recorded, verdict by verdict |
| `research/VALIDATION_paper2_sources.md` | What was checked about each outside source, and what could not be |
| `research/RULES_alpha_swing_2026-10-13.md` | The firm's rules as read on 13 October 2026, with sources |
| `research/run_K*.py`, `research/info_K_*.py` | The analyses, one script per plan amendment |
| `research/validate_lim.py` | Independent re-implementation of Lim (2026), from his paper's text alone |
| `data/r2cache/` | The day series every result is computed from (see below) |
| `data/derived/` | Reference prices, contract sizes and hourly spread tables; daily series of the real strategies |
| `results/reference/` | The tables and logs of the original runs |
| `paper/prop_contract/` | The paper's source, exhibits and the script that builds them |
| `provenance/` | The commit history of the plan and of each run in the research repository |

## Data

**Shipped.** For each instrument and cost level, one small file holds, for every business day from January
2005 to September 2024, the net result and worst intraday mark of the day's trade in each direction (in units
of the stop distance) and the stop distance as a share of price. These are derived from OANDA 30-minute bid
candles and from spreads I measured on the broker's server. Hourly spread tables, reference prices and contract
sizes are in `data/derived/book_meta.json`.

**Not shipped.**
- *Raw price bars.* They are OANDA's. With a free practice account you can download the same candles; put them
  in `data/raw/` as described in `research/validate_book.py`, and the `book` stage rebuilds the day series and
  checks them against the shipped ones. In the research repository that check passes exactly.
- *The firm's web pages.* `research/SOURCES_alpha_2026-10-13.json` records each page's address, date and SHA-256
  hash; `python reproduce.py --only rules` re-checks every quoted phrase against the live pages.
- *The builders of the three real strategies in Table 10.* They depend on a larger private research codebase.
  Their daily profit-and-loss series are shipped in `data/derived/K9_daily_series.npz`, so the table reproduces,
  but the series themselves cannot be rebuilt from this package.

## Timestamps of the plans

The plan and its amendments were committed and pushed to a private research repository before the runs they
describe. `provenance/plan_history.txt` is the full history of the plan file with commit hashes and dates, and
`provenance/commits.txt` lists every commit that touched the plan, the scripts and the results, in order. The full
research repository is available to editors and referees on request (contact below); it is not public because it
also holds unrelated personal tools. Git dates can be set by the author, so this is a record, not proof. Plans for
later work will be registered with a third-party service before they are run.

## Licence and citation

Code: MIT (see `LICENSE`). Text, tables and figures of the paper: CC BY 4.0. If you use this package, please cite
the paper and the package:

> Ojebiyi, T. O. (2026). *Fair on Paper: reproduction package* (version 1.0.0). Zenodo.
> https://doi.org/10.5281/zenodo.23374897

That DOI always resolves to the latest version; version 1.0.0 itself is https://doi.org/10.5281/zenodo.23374898.
`CITATION.cff` holds the same details, and GitHub's "Cite this repository" button reads it.

Contact: Timothy Oluwatobi Ojebiyi, tobiojebiyi@gmail.com, ORCID [0009-0009-7786-8549](https://orcid.org/0009-0009-7786-8549)
