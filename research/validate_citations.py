"""Look up every citation carried in the research notes and in Paper 1 against Crossref and arXiv, and record
what each one is: a journal article, a working paper, a book, or something else. Raw API records, no summarising
reader. Run from the repository root:
    python research/validate_citations.py            query and save
    python research/validate_citations.py --offline  re-print the saved records
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path("data/sources/citations_2026-10-13")
UA = {"User-Agent": "citation-check/1.0 (research script; urllib)"}

# key: (how we cite it, bibliographic query)
CITES = {
    # Paper 1 (replication note)
    "P1 Goyal-Welch-Zafirov 2024 RFS 37(11) 3490-3557": "Goyal Welch Zafirov A comprehensive 2022 look at the empirical performance of equity premium prediction",
    "P1 Meese-Rogoff 1983 JIE 14(1-2) 3-24": "Meese Rogoff Empirical exchange rate models of the seventies: do they fit out of sample",
    "P1 Chen-Guestrin 2016 KDD 785-794": "Chen Guestrin XGBoost: A scalable tree boosting system",
    # literature review
    "L Boyarchenko-Larsen-Whelan RFS 2023": "Boyarchenko Larsen Whelan The overnight drift",
    "L Lucca-Moench 2015": "Lucca Moench The pre-FOMC announcement drift",
    "L Kurov-Wolfe-Gilbert FRL 2021": "Kurov Wolfe Gilbert The disappearing pre-FOMC announcement drift",
    "L Lopez-Lira-Tang 2023": "Lopez-Lira Tang Can ChatGPT forecast stock price movements? Return predictability and large language models",
    "L Gao-Han-Li-Zhou JFE 2018": "Gao Han Li Zhou Market intraday momentum",
    "L Baltussen-Da-Lammers-Martens JFE 2021": "Baltussen Da Lammers Martens Hedging demand and market intraday momentum",
    "L Kelly-Malamud-Zhou JF 2024": "Kelly Malamud Zhou The virtue of complexity in return prediction",
    "L Buncic 2025": "Buncic Simplified: a closer look at the virtue of complexity in return prediction",
    "L Huang-Li-Wang-Zhou JFE 2020": "Huang Li Wang Zhou Time series momentum: Is it there?",
    "L Jensen-Kelly-Pedersen JF 2023": "Jensen Kelly Pedersen Is there a replication crisis in finance?",
    "L Jensen-Kelly-Malamud-Pedersen RFS 2026": "Jensen Kelly Malamud Pedersen Machine learning and the implementable efficient frontier",
    "L Moreira-Muir 2017": "Moreira Muir Volatility-managed portfolios",
    "L Cederburg-ODoherty-Wang-Yan JFE 2020": "Cederburg O'Doherty Wang Yan On the performance of volatility-managed portfolios",
    "L Barroso-Detzel 2021": "Barroso Detzel Do limits to arbitrage explain the benefits of volatility-managed portfolios?",
    "L Beckmeyer-Branger-Gayda 2023": "Beckmeyer Branger Gayda Retail traders love 0DTE options but should they?",
    "L Schmeling-Schrimpf-Todorov Management Science": "Schmeling Schrimpf Todorov Crypto carry",
    "L Etula et al RFS 2020": "Etula Rinne Suominen Vaittinen Dash for cash: monthly market impact of institutional liquidity needs",
    "L Harvey-Mazzoleni-Melone 2025": "Harvey Mazzoleni Melone The unintended consequences of rebalancing",
    "L Lou-Yan-Zhang RFS 2013": "Lou Yan Zhang Anticipated and repeated shocks in liquid markets",
    "L Chague-De-Losso-Giovannetti 2019/2020": "Chague De-Losso Giovannetti Day trading for a living?",
    # sources of the 24 tests and the rounds before them
    "T Krohn-Mueller-Whelan JF 2024": "Krohn Mueller Whelan Foreign exchange fixings and returns around the clock",
    "T Melvin-Prins 2015": "Melvin Prins Equity hedging and exchange rates at the London 4 p.m. fix",
    "T Mueller-Tahbaz-Salehi-Vedolin 2017": "Mueller Tahbaz-Salehi Vedolin Exchange rates and monetary policy uncertainty",
    "T Tornell-Yuan (2009 WP; later published)": "Tornell Yuan Speculation and hedging in the currency futures markets: are they informative to the spot exchange rates",
    "T Menkhoff-Sarno-Schmeling-Schrimpf 2012": "Menkhoff Sarno Schmeling Schrimpf Carry trades and global foreign exchange volatility",
    "T Lustig-Verdelhan 2007": "Lustig Verdelhan The cross section of foreign currency risk premia and consumption growth risk",
    "T Brunnermeier-Nagel-Pedersen 2008": "Brunnermeier Nagel Pedersen Carry trades and currency crashes",
    "T Olszweski-Zhou 2014": "Olszweski Zhou Strategy diversification: combining momentum and carry strategies within a foreign exchange portfolio",
    "T Koijen-Moskowitz-Pedersen-Vrugt 2018": "Koijen Moskowitz Pedersen Vrugt Carry",
    "T Moskowitz-Ooi-Pedersen 2012": "Moskowitz Ooi Pedersen Time series momentum",
    "T Hurst-Ooi-Pedersen 2017": "Hurst Ooi Pedersen A century of evidence on trend-following investing",
    "T Asness-Moskowitz-Pedersen 2013": "Asness Moskowitz Pedersen Value and momentum everywhere",
    "T Andersen-Bollerslev-Diebold-Vega AER 2003": "Andersen Bollerslev Diebold Vega Micro effects of macro announcements: real-time price discovery in foreign exchange",
    "T Bernard-Thomas 1989": "Bernard Thomas Post-earnings-announcement drift: delayed price response or risk premium?",
    "T Brandt-Kishore-Santa-Clara-Venkatachalam 2008": "Brandt Kishore Santa-Clara Venkatachalam Earnings announcements are full of surprises",
    "T Martineau 2022": "Martineau Rest in peace post-earnings announcement drift",
    "T McLean-Pontiff JF 2016": "McLean Pontiff Does academic research destroy stock return predictability?",
    "T Avellaneda-Lee 2010": "Avellaneda Lee Statistical arbitrage in the US equities market",
    "T Gatev-Goetzmann-Rouwenhorst 2006 RFS": "Gatev Goetzmann Rouwenhorst Pairs trading: performance of a relative-value arbitrage rule",
    "T Daniel-Moskowitz 2016 JFE": "Daniel Moskowitz Momentum crashes",
    "T Tetlock 2007 JF": "Tetlock Giving content to investor sentiment: the role of media in the stock market",
    "T Lakonishok-Smidt 1988": "Lakonishok Smidt Are seasonal anomalies real? A ninety-year perspective",
    "T McConnell-Xu FAJ 2008": "McConnell Xu Equity returns at the turn of the month",
    "T Bailey-Lopez de Prado 2014": "Bailey Lopez de Prado The deflated Sharpe ratio: correcting for selection bias, backtest overfitting and non-normality",
    # prior work the two prop-firm papers lean on, likely to be cited in Paper 2
    "C Barber-Odean 2000": "Barber Odean Trading is hazardous to your wealth: the common stock investment performance of individual investors",
    "C Barber-Lee-Liu-Odean 2014": "Barber Lee Liu Odean The cross-section of speculator skill: evidence from day trading",
    "C Brown-Harlow-Starks 1996": "Brown Harlow Starks Of tournaments and temptations: an analysis of managerial incentives in the mutual fund industry",
    "C Kumar 2009": "Kumar Who gambles in the stock market?",
    "C Heimer-Simsek 2019": "Heimer Simsek Should retail investors' leverage be limited?",
    "C Barberis 2012": "Barberis A model of casino gambling",
    "C Lo 2002": "Lo The statistics of Sharpe ratios",
    "C Benjamini-Hochberg 1995": "Benjamini Hochberg Controlling the false discovery rate: a practical and powerful approach to multiple testing",
    "C Politis-Romano 1994": "Politis Romano The stationary bootstrap",
}
DOIS = {"L Nagel NBER w34104": "10.3386/w34104", "T NBER w24877 (crypto)": "10.3386/w24877", "T NBER w33554 (round 2)": "10.3386/w33554",
        "P1 Andrews SSRN 6426038": "10.2139/ssrn.6426038", "Lim SSRN 7178078": "10.2139/ssrn.7178078",
        "Villahermosa SSRN 7445798": "10.2139/ssrn.7445798"}
ARXIV = ["1908.10063", "2505.16136", "2607.20093", "2507.07296", "2511.18578", "2606.27100"]


def get(url: str) -> str:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def brief(it: dict) -> str:
    au = ", ".join(a.get("family", a.get("name", "?")) for a in it.get("author", [])[:5])
    yr = (it.get("published") or it.get("issued") or {}).get("date-parts", [[None]])[0][0]
    cont = (it.get("container-title") or it.get("institution", [{}])[0:1] or [""])[0]
    cont = cont.get("name", "") if isinstance(cont, dict) else cont
    title = re.sub(r"\s+", " ", (it.get("title") or ["?"])[0])[:95]
    extra = f" {it.get('volume', '')}({it.get('issue', '')}) {it.get('page', '')}".rstrip() if it.get("volume") else ""
    return f"[{it.get('type', '?')}] {au} ({yr}). {title}. {cont}{extra}  doi:{it.get('DOI')}"


def main():
    offline = "--offline" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    store = json.loads((OUT / "crossref.json").read_text(encoding="utf-8")) if offline else {}
    for key, q in CITES.items():
        if not offline:
            url = "https://api.crossref.org/works?rows=4&query.bibliographic=" + urllib.parse.quote(q)
            try:
                store[key] = json.loads(get(url))["message"]["items"]
            except Exception as e:                                         # noqa: BLE001
                store[key] = [{"title": [f"LOOKUP FAILED: {e}"]}]
            time.sleep(0.4)
        print(f"\n# {key}")
        for it in store[key][:4]:
            print("   " + brief(it))
    for key, doi in DOIS.items():
        if not offline:
            try:
                store[key] = [json.loads(get("https://api.crossref.org/works/" + urllib.parse.quote(doi)))["message"]]
            except Exception as e:                                         # noqa: BLE001
                store[key] = [{"title": [f"LOOKUP FAILED: {e}"], "DOI": doi}]
            time.sleep(0.4)
        print(f"\n# {key}\n   " + brief(store[key][0]))
    if not offline:
        (OUT / "crossref.json").write_text(json.dumps(store), encoding="utf-8")
        (OUT / "arxiv.xml").write_text(get("http://export.arxiv.org/api/query?max_results=20&id_list=" + ",".join(ARXIV)),
                                       encoding="utf-8")
    xml = (OUT / "arxiv.xml").read_text(encoding="utf-8")
    print("\n# arXiv")
    for e in re.findall(r"(?s)<entry>(.*?)</entry>", xml):
        f = lambda tag: re.sub(r"\s+", " ", (re.search(rf"(?s)<{tag}[^>]*>(.*?)</{tag}>", e) or [None, ""])[1]).strip()  # noqa: E731
        names = ", ".join(re.findall(r"<name>(.*?)</name>", e)[:5])
        cats = ", ".join(re.findall(r'<category term="([^"]+)"', e))
        print(f"   {f('id').rsplit('/', 1)[-1]}: {names}. {f('title')[:100]}. published {f('published')[:10]}, updated "
              f"{f('updated')[:10]}; {cats}; journal_ref: {f('arxiv:journal_ref') or 'none'}; comment: {f('arxiv:comment')[:90] or 'none'}")


if __name__ == "__main__":
    main()
