"""Rebuild the day series from raw 30-minute bars and compare them with the shipped ones.

The raw bars are not redistributed. Put OANDA 30-minute bid candles in data/raw/<CODE>_M30.parquet (a DataFrame
indexed by UTC bar-open time with columns open, high, low, close), for SPX500_USD, NAS100_USD, EUR_USD and
USD_JPY, from 2005-01-01 to 2024-09-30. Without them this stage reports that and passes.

    python research/validate_book.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from propcontract.book import build_tuples

RAW, CACHE = Path("data/raw"), Path("data/r2cache")
META = json.loads(Path("data/derived/book_meta.json").read_text(encoding="utf-8"))
BOOKS = {"SPX500_USD": ("K_tuples_x{s}.npz", (0.0, 1.0, 1.5, 2.0)), "NAS100_USD": ("K6_tuples_NAS100_USD_x{s}.npz", (0.0, 1.5)),
         "EUR_USD": ("K6_tuples_EUR_USD_x{s}.npz", (0.0, 1.5)), "USD_JPY": ("K6_tuples_USD_JPY_x{s}.npz", (0.0, 1.5))}


def main():
    worst, done = 0.0, 0
    for code, (pattern, stresses) in BOOKS.items():
        path = RAW / f"{code}_M30.parquet"
        if not path.exists():
            print(f"{code}: no raw bars at {path}; skipped")
            continue
        bars = pd.read_parquet(path)
        for s in stresses:
            z = np.load(CACHE / pattern.format(s=s))
            t = build_tuples(bars, META[code]["spread_by_server_hour"], META[code]["ref_price"], stress=s)
            same = np.array_equal(t.has, z["has"])
            d = max(float(np.abs(t.R - z["R"]).max()), float(np.abs(t.L - z["L"]).max()), float(np.abs(t.v - z["v"]).max())) if same else np.inf
            worst, done = max(worst, d), done + 1
            print(f"{code} x{s}: {int(t.has.sum())} trade days, same days {same}, largest difference {d:.2e}", flush=True)
    if not done:
        print("No raw bars found: the shipped day series are used as they are.")
        return
    assert worst < 1e-9, "the builder does not reproduce the shipped day series from these bars"
    print("THE SHIPPED DAY SERIES ARE REPRODUCED FROM RAW BARS")


if __name__ == "__main__":
    main()
