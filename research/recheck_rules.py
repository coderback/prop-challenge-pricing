"""Re-read Alpha Capital Group's rule-bearing help-centre articles and terms and compare them with the 13 October
2026 snapshot that Paper 2 prices (research/RULES_alpha_swing_2026-10-13.md).

    python research/recheck_rules.py 2026-11-08            fetch into data/sources/alpha_<date>/ and compare
    python research/recheck_rules.py 2026-11-08 --offline  compare pages already saved

Reports articles added or removed, every article whose body text changed (page chrome and the help centre's
relative "updated ... ago" dates removed), whether each phrase quoted in the paper is still on its page, and
whether the terms text changed. Raw pages go to data/sources/ (not committed); the reading is recorded in
research/VALIDATION_paper2_sources.md.
"""
import difflib
import hashlib
import importlib.util
import json
import re
import sys
import time
from pathlib import Path

spec = importlib.util.spec_from_file_location("vr", "research/validate_rules.py")
vr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vr)
spec2 = importlib.util.spec_from_file_location("fhc", "research/fetch_help_centre.py")
fhc = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(fhc)

OLD = Path("data/sources/alpha_2026-10-13")
UPD = re.compile(r"updated (?:this week|today|yesterday|(?:over |about )?(?:a|an|\d+) (?:day|week|month|year)s? ago)\s*")
DATE_ABS = re.compile(r"(?:january|february|march|april|may|june|july|august|september|october|november|december) \d{1,2}, \d{4}")


def core(raw: str) -> str:
    """Article body without the page chrome or the date line."""
    t = vr.norm(vr.text_of(raw))
    m = UPD.search(t) or DATE_ABS.search(t)
    t = t[m.end():] if m else t
    end = t.find("did this answer your question")
    return t[: end if end > 0 else len(t)].strip()


def diff(a: str, b: str, split=r"(?<=[.!?:])\s+") -> list[str]:
    return [ln[:500] for ln in difflib.unified_diff(re.split(split, a), re.split(split, b), lineterm="", n=0)
            if not ln.startswith(("---", "+++", "@@"))]


def fetch_all(new: Path) -> None:
    urls = {}
    for c in fhc.COLLECTIONS:
        raw = vr.fetch(f"{fhc.ROOT}/en/collections/{c}")
        for href in re.findall(r'href="([^"]*?/en/articles/[^"#?]+)"', raw):
            url = href if href.startswith("http") else fhc.ROOT + href
            urls[url.rsplit("/", 1)[1].split("-")[0]] = (url, c)
        time.sleep(0.5)
    (new / "all" / "_urls.json").write_text(json.dumps(urls, indent=1), encoding="utf-8")
    index = []
    for aid, (url, c) in sorted(urls.items()):
        path = new / "all" / f"{aid}.html"
        if not path.exists():
            path.write_text(vr.fetch(url), encoding="utf-8")
            time.sleep(0.5)
        raw = path.read_text(encoding="utf-8")
        index.append({"id": aid, "collection": c.split("-", 1)[1], "url": url,
                      "sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest()})
    (new / "all" / "_index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    for key, url in vr.PAGES.items():
        (new / f"{key}.html").write_text(vr.fetch(url), encoding="utf-8")
        time.sleep(0.5)


def main():
    date = sys.argv[1]
    new = Path(f"data/sources/alpha_{date}")
    (new / "all").mkdir(parents=True, exist_ok=True)
    if "--offline" not in sys.argv:
        fetch_all(new)
    old_urls = json.loads((OLD / "all" / "_urls.json").read_text(encoding="utf-8"))
    new_urls = json.loads((new / "all" / "_urls.json").read_text(encoding="utf-8"))
    print(f"articles: {len(old_urls)} on 13 Oct, {len(new_urls)} on {date}")
    print("  added:", {k: new_urls[k][0] for k in sorted(set(new_urls) - set(old_urls))})
    print("  removed:", {k: old_urls[k][0] for k in sorted(set(old_urls) - set(new_urls))})
    common = sorted(set(old_urls) & set(new_urls))
    n = 0
    for aid in common:
        a = core((OLD / "all" / f"{aid}.html").read_text(encoding="utf-8"))
        b = core((new / "all" / f"{aid}.html").read_text(encoding="utf-8"))
        if a != b:
            n += 1
            print(f"\n=== {aid}  {new_urls[aid][0]}")
            for ln in diff(a, b):
                print("  " + ln)
    print(f"\n{n} of {len(common)} common articles differ in body text")
    for aid in sorted(set(new_urls) - set(old_urls)):
        print(f"\n=== NEW {aid}: {core((new / 'all' / f'{aid}.html').read_text(encoding='utf-8'))[:1500]}")

    missing = 0
    for key in vr.PAGES:
        t = vr.norm(vr.text_of((new / f"{key}.html").read_text(encoding="utf-8")))
        for q in vr.QUOTES.get(key, []):
            if vr.norm(q) not in t:
                missing += 1
                print(f"MISSING on {key}: {q}")
    print(f"\nquoted phrases: {sum(len(v) for v in vr.QUOTES.values())} checked, {missing} missing")
    a = vr.norm(vr.text_of((OLD / "terms.html").read_text(encoding="utf-8")))
    b = vr.norm(vr.text_of((new / "terms.html").read_text(encoding="utf-8")))
    print(f"terms: identical text = {a == b}")
    for ln in diff(a, b, r"(?<=[.;])\s+"):
        print("  " + ln)


if __name__ == "__main__":
    main()
