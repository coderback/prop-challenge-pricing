"""The trade container of the older simulator: trades plus flattened per-day marked-to-market paths."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class TradeSet:
    """Trades plus flattened per-day MTM paths for the evaluation simulator."""

    trades: pd.DataFrame
    day0: np.ndarray = field(default_factory=lambda: np.zeros(0, "datetime64[D]"))
    offsets: np.ndarray = field(default_factory=lambda: np.zeros(0, int))
    lengths: np.ndarray = field(default_factory=lambda: np.zeros(0, int))
    flat_close: np.ndarray = field(default_factory=lambda: np.zeros(0))
    flat_low: np.ndarray = field(default_factory=lambda: np.zeros(0))

    @staticmethod
    def concat(sets: list["TradeSet"], sleeve_scales: list[float] | None = None) -> "TradeSet":
        sets = [s for s in sets if len(s.trades)]
        if not sets:
            return TradeSet(pd.DataFrame())
        scales = sleeve_scales or [1.0] * len(sets)
        trades, closes, lows, day0, lengths = [], [], [], [], []
        for s, k in zip(sets, scales):
            t = s.trades.copy()
            t["Rw"] = t["Rw"] * k
            trades.append(t)
            closes.append(s.flat_close * k)
            lows.append(s.flat_low * k)
            day0.append(s.day0)
            lengths.append(s.lengths)
        lengths = np.concatenate(lengths)
        offsets = np.concatenate([[0], np.cumsum(lengths)[:-1]]).astype(int)
        return TradeSet(pd.concat(trades, ignore_index=True), np.concatenate(day0), offsets, lengths,
                        np.concatenate(closes), np.concatenate(lows))
