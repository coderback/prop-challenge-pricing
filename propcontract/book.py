"""Standalone builder of the one-trade-a-day book from raw 30-minute bars (Paper 2 reproduction package).

It depends on numpy and pandas only and re-implements, for this one trade design, what the research code does
with its general trade simulator: entry at the open of the 14:30 London bar, exit at the open of the 20:30
London bar, a stop at ``stop_atr`` times the Wilder ATR(14) of the previous broker day, bid bars with a modelled
spread. ``research/validate_book.py`` checks that it reproduces the cached day series exactly.

Bars: a DataFrame indexed by UTC bar-open time (tz-aware) with bid ``open``, ``high``, ``low``, ``close``.
Spread: 24 values in price units, one per broker-server hour, measured at ``ref_price``; the spread applied to a
bar is ``spread[hour] × stress × open / ref_price``.
"""
from __future__ import annotations

from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from .contract import DayTuples

LONDON, NEW_YORK = ZoneInfo("Europe/London"), ZoneInfo("America/New_York")
DEV_START, DEV_END = "2005-01-01", "2024-10-01"          # development sample: [start, end)
DAYS = pd.bdate_range("2005-01-03", "2024-09-30").to_numpy().astype("datetime64[D]")


def server_time(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Naive broker-server time: New York time plus seven hours (GMT+2, GMT+3 during US daylight saving)."""
    return idx.tz_convert(NEW_YORK).tz_localize(None) + pd.Timedelta(hours=7)


def bars_at(bars: pd.DataFrame, hhmm: int) -> pd.Series:
    """London date -> position of the bar that opens at ``hhmm`` London time, weekdays only."""
    loc = bars.index.tz_convert(LONDON)
    df = pd.DataFrame({"i": np.arange(len(loc)), "date": loc.normalize().tz_localize(None),
                       "hm": loc.hour * 100 + loc.minute})
    s = df[df.hm == hhmm].groupby("date")["i"].first()
    return s[s.index.dayofweek < 5]


def broker_daily(bars: pd.DataFrame) -> pd.DataFrame:
    """Broker D1 bars by server date, weekend stubs merged into Monday."""
    st = pd.Series(server_time(bars.index), index=bars.index)
    day = st.dt.normalize()
    wd = day.dt.weekday
    day = day + pd.to_timedelta(np.where(wd == 5, 2, np.where(wd == 6, 1, 0)), unit="D")
    df = bars[["open", "high", "low", "close"]].assign(day=day.to_numpy(), st=st.to_numpy()).sort_values("st")
    return df.groupby("day").agg({"open": "first", "high": "max", "low": "min", "close": "last"})


def wilder_atr(daily: pd.DataFrame, n: int = 14) -> pd.Series:
    prev = daily["close"].shift(1)
    tr = pd.concat([daily["high"] - daily["low"], (daily["high"] - prev).abs(), (daily["low"] - prev).abs()],
                   axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def build_tuples(bars: pd.DataFrame, spread_by_hour, ref_price: float, stress: float = 1.5, stop_atr: float = 1.0,
                 entry_hhmm: int = 1430, exit_hhmm: int = 2030, days: np.ndarray = DAYS) -> DayTuples:
    """Both sides of every day's trade: net result R and worst intraday mark L in stop units, and the stop
    distance as a fraction of the long entry price."""
    bars = bars[(bars.index >= pd.Timestamp(DEV_START, tz="UTC")) & (bars.index < pd.Timestamp(DEV_END, tz="UTC"))]
    st = server_time(bars.index)
    hour = st.hour.to_numpy()
    sday = st.normalize().to_numpy().astype("datetime64[D]")
    o, h, lo, c = (bars[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    spread = np.asarray(spread_by_hour, float)[hour] * stress / ref_price * o
    a, b = bars_at(bars, entry_hhmm), bars_at(bars, exit_hhmm)
    both = a.index.intersection(b.index)
    e_all, x_all = a[both].to_numpy(int), b[both].to_numpy(int)
    atr_prev = wilder_atr(broker_daily(bars)).shift(1)
    dist_all = stop_atr * atr_prev.reindex(pd.DatetimeIndex(sday[e_all].astype("datetime64[ns]"))).to_numpy()
    G = len(days)
    has, R, L, v = np.zeros(G, bool), np.zeros((G, 2)), np.zeros((G, 2)), np.ones(G)
    for e, x, dist in zip(e_all, x_all, dist_all):
        if not (np.isfinite(dist) and dist > 0 and x > e):
            continue
        g = int(np.searchsorted(days, sday[e]))
        if g >= G or days[g] != sday[e]:
            continue
        assert sday[x - 1] == sday[e] and not has[g], "the trade must open and close on one server day, once a day"
        for col, s in ((0, 1), (1, -1)):
            entry = o[e] + spread[e] if s > 0 else o[e]
            stop = entry - s * dist
            worst_mark, result = np.inf, None
            for j in range(e, x):
                if s > 0:                                      # longs exit on the bid
                    open_, worst, close_ = o[j], lo[j], c[j]
                    gapped, touched = j > e and open_ <= stop, worst <= stop
                else:                                          # shorts exit on the ask
                    open_, worst, close_ = o[j] + spread[j], h[j] + spread[j], c[j] + spread[j]
                    gapped, touched = j > e and open_ >= stop, worst >= stop
                if gapped or touched:
                    result = s * ((open_ if gapped else stop) - entry) / dist
                    worst_mark = min(worst_mark, result)
                    break
                worst_mark = min(worst_mark, s * (worst - entry) / dist)
            if result is None:                                 # time exit at the open of the exit bar
                exit_px = o[x] if s > 0 else o[x] + spread[x]
                result = s * (exit_px - entry) / dist
            R[g, col], L[g, col] = result, min(worst_mark, result)
            if s > 0:
                v[g] = dist / entry
        has[g] = True
    return DayTuples(days, has, R, L, v)
