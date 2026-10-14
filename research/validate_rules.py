"""Amendment 1, V2: check every phrase quoted in RULES_alpha_swing_2026-10-13.md against the raw text of its source
page, fetched directly (no summarising reader). Raw pages are saved under data/sources/ (not committed) with their
SHA-256. Run from the repository root:
    python research/validate_rules.py            fetch, save and check
    python research/validate_rules.py --offline  re-check the saved pages
"""
import hashlib
import html
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("data/sources/alpha_2026-10-13")
HELP = "https://help.alphacapitalgroup.uk/en/articles/"
PAGES = {
    "swing": HELP + "9789907-alpha-swing",
    "daily": HELP + "6934210-what-are-the-daily-risk-limits-and-how-do-they-work",
    "inactivity": HELP + "8420080-inactivity",
    "lots": HELP + "6934289-what-is-the-lot-size-limit-on-qualified-analyst-accounts",
    "maxrisk": HELP + "15888623-what-is-the-max-risk-rule-and-how-does-it-work",
    "ondemand": HELP + "10102634-performance-fee-on-demand",
    "paid": HELP + "6933755-how-do-i-get-paid-performance-fees",
    "earn": HELP + "7060937-what-do-qualified-analysts-earn-from-account-profits",
    "ftg": HELP + "9691161-focused-trader-group",
    "gambling": HELP + "7060909-what-is-alpha-capital-group-s-policy-against-gambling-in-trading",
    "terms": "https://alphacapitalgroup.uk/terms-and-conditions",
}
QUOTES = {
    "swing": ["Phase 1 profit target: 10%", "Phase 2 profit target: 5%", "Max Drawdown (static): 10%",
              "Max Daily Drawdown (balance-based): 5%", "Minimum trading days (for each phase): 3"],
    "daily": ["breaches are always applied based on open trades (unrealised losses)"],
    "inactivity": ["All accounts, at all stages"],
    "lots": ["the total combined lots/position size allowed at any one time"],
    "maxrisk": ["applies to Qualified Accounts only", "floating/unrealised losses"],
    "ondemand": ["a minimum of 2% of gross profits on the account balance",
                 "no single trading day should contribute more than a set percentage of the total generated profits"],
    "paid": ["processed and paid within 2 business days", "You can resume trading once your account balance has been reset"],
    "earn": ["an 80% share of the profits"],
    "ftg": ["a temporary group into which Qualified Analyst accounts may be moved",
            "Using a swing trading account primarily for scalping or frequent intraday strategies, without any swing trading activity",
            "Excessive max lot / max margin usage",
            "the maximum allowable risk for any single position is 1% of your initial balance"],
    "gambling": ["A significant change in lot size compared to the overall average on the account", "all or nothing",
                 "the removal of profits"],
    "terms": ["There are no time limits applicable to the Evaluations",
              "There is no maximum virtual position size exposure during the evaluation stage",
              "Swing accounts are only available with the On-Demand payout type", "maintain the same level of risk",
              "will not be paid where we ascertain, in our sole discretion", "a minimum of 2% of gross profits on the account balance"],
}
# facts recorded without quotation marks: print the page's own words around these anchors for reading
ANCHORS = {
    "swing": ["leverage", "on-demand", "time limit"], "daily": ["gmt", "00:00"], "inactivity": ["30"],
    "lots": ["swing", "first", "second"], "maxrisk": ["21", "3%", "2%", "per asset", "breach"],
    "ondemand": ["40%", "reset", "best day"], "paid": ["closed", "minimum", "days"], "earn": ["90%"],
    "ftg": ["1.25", "1:5", "next trading day", "rolling", "full risk"], "gambling": ["closure", "terminat"],
    "terms": ["refund", "same level of risk"],
}


def norm(s: str) -> str:
    s = html.unescape(s)
    for a, b in (("‘", "'"), ("’", "'"), ("“", '"'), ("”", '"'), ("–", "-"), ("—", "-"),
                 (" ", " "), ("​", "")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip().lower()


def text_of(raw: str) -> str:
    body = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    return norm(re.sub(r"(?s)<[^>]+>", " ", body))


def embedded(raw: str) -> str:
    """Text held in script payloads (JSON), with escapes decoded and tags removed."""
    s = raw.replace('\\"', '"').replace("\\n", " ").replace("\\/", "/")
    s = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), s)
    return norm(re.sub(r"(?s)<[^>]+>", " ", s))


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                                             "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
                                               "Accept-Language": "en-GB,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def main():
    offline = "--offline" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    report, misses = {}, 0
    for key, url in PAGES.items():
        path = OUT / f"{key}.html"
        try:
            raw = path.read_text(encoding="utf-8") if offline else fetch(url)
        except Exception as e:                                             # noqa: BLE001
            print(f"\n## {key}: FETCH FAILED ({e})\n   {url}")
            report[key] = {"url": url, "error": str(e)}
            continue
        if not offline:
            path.write_text(raw, encoding="utf-8")
        visible, hidden = text_of(raw), embedded(raw)
        rows = {}
        print(f"\n## {key}: {len(raw):,} bytes, {len(visible):,} characters of visible text\n   {url}")
        for q in QUOTES.get(key, []):
            where = "visible" if norm(q) in visible else "embedded" if norm(q) in hidden else None
            rows[q] = where
            print(f"   [{'ok ' if where else 'MISS'}] {q}" + (f"  ({where})" if where == "embedded" else ""))
            misses += where is None
        src = visible if len(visible) > 2000 else hidden
        for a in ANCHORS.get(key, []):
            for m in list(re.finditer(re.escape(a.lower()), src))[:2]:
                print(f"      ~ '{a}': ...{src[max(0, m.start() - 170): m.end() + 230]}...")
        report[key] = {"url": url, "sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(), "bytes": len(raw),
                       "quotes": rows}
    report["_checked_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (OUT / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    total = sum(len(v) for v in QUOTES.values())
    print(f"\n{total - misses} of {total} quoted phrases found verbatim; report in {OUT / 'report.json'}")


if __name__ == "__main__":
    main()
