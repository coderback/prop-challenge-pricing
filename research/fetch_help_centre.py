"""Amendment 1, V2 (extension): save every article in the rule-bearing collections of Alpha Capital Group's help
centre, so the rule record can be checked for omissions. Raw pages go to data/sources/ (not committed).
Run from the repository root:
    python research/fetch_help_centre.py            fetch and index
    python research/fetch_help_centre.py --offline  rebuild the index from saved pages
"""
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

ROOT = "https://help.alphacapitalgroup.uk"
OUT = vr.OUT / "all"
COLLECTIONS = ["11007442-alpha-plans", "19682652-trading-rules", "3826555-general", "3848050-evaluation",
               "3848053-qualified-analyst", "3848057-important-trading-terms"]


def body(raw: str) -> tuple[str, str, str]:
    t = vr.text_of(raw)
    title = t.split(" | ")[0]
    end = t.find("did this answer your question")
    t = t[: end if end > 0 else len(t)]
    m = re.search(r"((?:january|february|march|april|may|june|july|august|september|october|november|december) \d{1,2}, \d{4})", t)
    date = m.group(1) if m else ""
    return title, date, t[m.end():].strip() if m else t


def main():
    offline = "--offline" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    urls = {}
    if not offline:
        for c in COLLECTIONS:
            raw = vr.fetch(f"{ROOT}/en/collections/{c}")
            for href in re.findall(r'href="([^"]*?/en/articles/[^"#?]+)"', raw):
                url = href if href.startswith("http") else ROOT + href
                urls[url.rsplit("/", 1)[1].split("-")[0]] = (url, c)
            time.sleep(0.5)
        for aid, (url, c) in sorted(urls.items()):
            path = OUT / f"{aid}.html"
            if not path.exists():
                path.write_text(vr.fetch(url), encoding="utf-8")
                time.sleep(0.5)
        (OUT / "_urls.json").write_text(json.dumps(urls, indent=1), encoding="utf-8")
    urls = json.loads((OUT / "_urls.json").read_text(encoding="utf-8"))
    index = []
    for aid, (url, c) in sorted(urls.items(), key=lambda kv: (kv[1][1], kv[0])):
        raw = (OUT / f"{aid}.html").read_text(encoding="utf-8")
        title, date, text = body(raw)
        (OUT / f"{aid}.txt").write_text(f"{title}\n{date}\n{url}\n\n{text}\n", encoding="utf-8")
        index.append({"id": aid, "collection": c.split("-", 1)[1], "title": title, "page_date": date, "chars": len(text),
                      "url": url, "sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest()})
    (OUT / "_index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    for r in index:
        print(f"{r['collection'][:18]:18s} {r['id']:>9s} {r['page_date']:>18s} {r['chars']:>6d}  {r['title']}")
    print(f"\n{len(index)} articles saved in {OUT}")


if __name__ == "__main__":
    main()
