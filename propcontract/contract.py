"""Vectorised challenge-contract simulator for one-trade-a-day books (research/PREREGISTRATION_paper2_contract_map.md).

A path is a purchase followed by at most one intraday trade per trading day. A day carries the trade's net
result R and its worst intraday mark L, both in units of the stop distance, and v, the stop distance as a
fraction of price (so leverage and lot caps can be applied). Balances are in dollars on a $10k account.

The unit of simulation is an *account*: a path (``row``) with a risk setting. Stacking the same paths with
different risks prices a whole sizing grid in one pass. The day loop is the only Python loop.

With ``Contract.s2()`` the two stages reproduce ``r2.evalsim.run_one`` and ``run_funded`` to the cent (the
thresholds and their arithmetic are copied on purpose).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq

IB = 10_000.0
EPS = 1e-9
RUNNING, PASS, BREACH_STATIC, BREACH_DAILY, TIMEOUT, MAX_RISK, CASHOUT = 0, 1, 2, 3, 4, 5, 6


@dataclass(frozen=True)
class Contract:
    # ---- evaluation ----
    target_p1: float = 0.10
    target_p2: float | None = 0.05        # None = one step
    static_dd: float = 0.10
    trail_dd: float | None = None         # trailing loss limit: floor = highest end-of-day balance − limit, capped
                                          # at the initial balance; replaces static_dd when set
    daily_dd: float | None = 0.05         # None = no daily rule
    daily_ref: str = "balance"            # 5% of the day's opening balance; "initial" = 5% of initial (Lim)
    intraday: bool = True                 # floors checked on the day's worst mark; False = at the close only
    min_days: int = 3
    step_days: tuple = (None, None)       # maturity of each step in trading days
    eval_days: int | None = 504           # analysis horizon for passing, in trading days from purchase
    phase_gap: int = 2                    # idle trading days after step 1
    fund_gap: int = 3                     # trading days between passing and the first funded day
    window: int = 756                     # trading days from purchase
    lev_eval: float | None = 10.0         # evaluation leverage cap (notional / initial)
    # ---- funded ----
    funded_days: int | None = None        # funded horizon in trading days; None = until the window ends
    lev_funded: float | None = None       # lot cap expressed as leverage
    risk_cap: float | None = None         # per-position risk cap (Focused Trader Group: 1%)
    max_risk: float | None = 0.03         # open loss on the position that closes the account
    split: float = 0.80
    min_profit: float = 0.02
    best_day: float | None = 0.40         # best day ≤ this share of the profit of the current payout window
    buffer: float = 0.0                   # profit left in the account at each payout; min_profit applies above it
    payout_every: int | None = None       # None = on demand (first eligible close); n = every n funded days
    payout_lock: int = 2                  # trading days locked after a payout

    @classmethod
    def alpha(cls, lam: float, regime: str = "FTG", **kw) -> "Contract":
        """Alpha Swing $10k as written. ``lam`` = 2.5 lots as leverage (2.5 × price / 10,000)."""
        if regime == "FTG":
            return cls(lev_funded=lam / 2, risk_cap=0.01, **kw)
        return cls(lev_funded=lam, **kw)

    @classmethod
    def s2(cls, **kw) -> "Contract":
        """The S1–S3 model: no leverage or lot caps, no Max Risk Rule, payout checks every 21 days."""
        return cls(**{"lev_eval": None, "max_risk": None, "payout_every": 21, "payout_lock": 0} | kw)

    @classmethod
    def lim(cls, maturity: bool = True, **kw) -> "Contract":
        """Lim (2026), Table 1: closes-only monitoring, sweeps every 20 days, 250 funded days."""
        steps = (30, 60) if maturity else (300, 300)
        return cls(**{"daily_ref": "initial", "intraday": False, "min_days": 0, "step_days": steps, "eval_days": None,
                      "phase_gap": 0, "fund_gap": 1, "window": 900, "lev_eval": None, "funded_days": 250,
                      "max_risk": None, "min_profit": 0.0, "best_day": None, "payout_every": 20,
                      "payout_lock": 0} | kw)


# ------------------------------------------------------------------------------------------------ days
@dataclass
class DayTuples:
    """Both sides of the book's daily trade on a global axis of business days."""

    days: np.ndarray        # datetime64[D]
    has: np.ndarray         # [G] a trade exists
    R: np.ndarray           # [G, 2] net R: column 0 long, 1 short
    L: np.ndarray           # [G, 2] worst intraday mark
    v: np.ndarray           # [G] stop distance / entry price

    @property
    def better(self) -> np.ndarray:
        return np.argmax(self.R, axis=1)

    @classmethod
    def from_tradesets(cls, long_ts, short_ts, days: np.ndarray) -> "DayTuples":
        days = days.astype("datetime64[D]")
        d0 = long_ts.day0.astype("datetime64[D]")
        assert (d0 == short_ts.day0.astype("datetime64[D]")).all(), "long and short books differ in days"
        assert (long_ts.lengths == 1).all() and (short_ts.lengths == 1).all(), "trades must be intraday"
        pos = np.searchsorted(days, d0)
        ok = (pos < len(days)) & (days[np.minimum(pos, len(days) - 1)] == d0)
        pos = pos[ok]
        assert len(np.unique(pos)) == len(pos), "more than one trade on a day"
        G = len(days)
        has, R, L, v = np.zeros(G, bool), np.zeros((G, 2)), np.zeros((G, 2)), np.ones(G)
        has[pos] = True
        for c, ts in enumerate((long_ts, short_ts)):
            R[pos, c] = ts.flat_close[ts.offsets][ok]
            L[pos, c] = ts.flat_low[ts.offsets][ok]
        v[pos] = (long_ts.trades["stop_dist"] / long_ts.trades["entry"]).to_numpy()[ok]
        return cls(days, has, R, L, v)


class BookDays:
    """Paths through a book. Each path's day index is ``start + t`` (historical order) or ``gidx[row, t]``
    (resampled). The side is the better one where ``take_better[row, t]``, or ``side[day]`` if sides are fixed."""

    def __init__(self, tup: DayTuples, start=None, gidx=None, take_better=None, side=None):
        self.tup, self.start, self.gidx, self.take_better, self.side = tup, start, gidx, take_better, side
        self.better = tup.better

    def at(self, t: int, rows: np.ndarray):
        g = self.start[rows] + t if self.gidx is None else self.gidx[rows, t]
        if self.side is not None:
            c = self.side[g]
        else:
            b = self.better[g]
            c = np.where(self.take_better[rows, t], b, 1 - b)
        return self.tup.R[g, c], self.tup.L[g, c], self.tup.v[g], self.tup.has[g]


class MatrixDays:
    """Explicit per-path outcomes ``R[row, t]`` (and ``L``; the close if omitted), a trade every day."""

    def __init__(self, R: np.ndarray, L: np.ndarray | None = None, v: float = np.inf):
        self.R, self.L, self.v = R, L, v

    def at(self, t: int, rows: np.ndarray):
        R = self.R[rows, t]
        L = R if self.L is None else self.L[rows, t]
        return R, L, np.full(len(rows), self.v), np.ones(len(rows), bool)


# ------------------------------------------------------------------------------------------------ stages
def _floor(c: Contract, high):
    """The overall loss limit in dollars: static, or trailing the highest end-of-day balance ``high``."""
    return (1 - c.static_dd) * IB if c.trail_dd is None else np.minimum(IB, high - c.trail_dd * IB)


def _breaches(c: Contract, b0, worst, floor):
    static = worst <= floor + EPS
    if c.daily_dd is None:
        return static, np.zeros(len(b0), bool)
    daily = (1 - c.daily_dd) * b0 if c.daily_ref == "balance" else b0 - c.daily_dd * IB
    return static, (worst <= daily + EPS) & ~static


def _track(r_sum, r_n, r_min, r_max, idx, m):
    r_sum[idx] += m
    r_n[idx] += 1
    r_min[idx] = np.minimum(r_min[idx], m)
    r_max[idx] = np.maximum(r_max[idx], m)


def _risk_stats(r_sum, r_n, r_min, r_max) -> dict:
    return {"risk_mean": r_sum / np.maximum(r_n, 1), "risk_min": np.where(r_n > 0, r_min, 0.0), "risk_max": r_max}


def evaluate(days, row: np.ndarray, risk: np.ndarray, c: Contract) -> dict:
    """Evaluation stage for accounts (path ``row``, risk fraction ``risk``). ``risk`` is one fraction per
    account, or a callable ``risk(phase, t, balance)`` for a state-dependent policy. Returns ``outcome`` codes,
    the pass offset ``pass_t``, the step-1 offset ``p1_t`` (−1 where not reached), ``end_t``, the offset at which
    the evaluation ended (−1 where it was still running at the horizon), and the mean, smallest and largest
    risk actually applied on trade days."""
    A = len(row)
    balance = np.full(A, IB)
    high = np.full(A, IB)
    phase = np.zeros(A, np.int8)
    traded = np.zeros(A, np.int32)
    wake = np.zeros(A, np.int32)
    step_start = np.zeros(A, np.int32)
    outcome = np.zeros(A, np.int8)
    pass_t = np.full(A, -1, np.int32)
    p1_t = np.full(A, -1, np.int32)
    end_t = np.full(A, -1, np.int32)
    r_sum, r_n, r_min, r_max = np.zeros(A), np.zeros(A, np.int32), np.full(A, np.inf), np.zeros(A)
    two_step = c.target_p2 is not None
    targets = np.array([IB * (1 + c.target_p1), IB * (1 + (c.target_p2 if two_step else c.target_p1))])
    maturity = np.array([np.inf if s is None else s for s in c.step_days], float)
    T = c.window if c.eval_days is None else min(c.eval_days, c.window)
    live = np.arange(A)
    for t in range(T):
        if live.size == 0:
            break
        act = live[wake[live] <= t]
        if act.size:
            if np.isfinite(maturity).any():
                late = (t - step_start[act]) >= maturity[phase[act]]
                outcome[act[late]] = TIMEOUT
                end_t[act[late]] = t
                act = act[~late]
            R, L, v, has = days.at(t, row[act])
            m = risk(phase[act], t, balance[act]) if callable(risk) else risk[act]
            if c.lev_eval is not None:
                m = np.minimum(m, c.lev_eval * v)
            _track(r_sum, r_n, r_min, r_max, act[has], m[has])
            m = np.where(has, m * IB, 0.0)
            b0 = balance[act]
            static, daily = _breaches(c, b0, b0 + m * (L if c.intraday else R), _floor(c, high[act]))
            outcome[act[static]] = BREACH_STATIC
            outcome[act[daily]] = BREACH_DAILY
            end_t[act[static | daily]] = t
            ok = ~(static | daily)
            a, b1 = act[ok], (b0 + m * R)[ok]
            traded[a] += has[ok]
            ph = phase[a]
            hit = (b1 >= targets[ph] - EPS) & (traded[a] >= c.min_days)
            done = hit & ((ph == 1) | (not two_step))
            step = hit & ~done
            outcome[a[done]] = PASS
            pass_t[a[done]] = t
            end_t[a[done]] = t
            p1_t[a[step]] = t
            phase[a[step]] = 1
            b1[step] = IB
            traded[a[step]] = 0
            wake[a[step]] = t + 1 + c.phase_gap
            step_start[a[step]] = t + 1 + c.phase_gap
            balance[a] = b1
            high[a] = np.where(step, IB, np.maximum(high[a], b1))
        live = live[outcome[live] == RUNNING]
    outcome[outcome == RUNNING] = TIMEOUT
    if not two_step:
        p1_t = pass_t.copy()
    return {"outcome": outcome, "pass_t": pass_t, "p1_t": p1_t, "end_t": end_t, **_risk_stats(r_sum, r_n, r_min, r_max)}


def fund(days, row: np.ndarray, wake0: np.ndarray, risk: np.ndarray, c: Contract,
         marks: tuple = (252, 504, 756), request=None) -> dict:
    """Funded stage for accounts that start trading at offset ``wake0`` with intended risk ``risk`` (one
    fraction per account, or a callable ``risk(t, balance, best_day)``). A payout is requested at the first
    close that allows one, or, with ``request(t, balance, best_day)``, at the allowed closes it selects. Returns
    the payouts (USD), the number of payouts, the closing ``outcome`` (0 = still open at the end), ``pay_by``,
    the payouts requested before each offset in ``marks``, and the risk actually applied on trade days. With a
    trailing limit, a payout that leaves the balance at or below the floor closes the account (``CASHOUT``)."""
    A = len(row)
    balance = np.full(A, IB)
    base = np.full(A, IB)                 # balance at the start of the current payout window
    keep = c.buffer * IB
    max_gain = np.zeros(A)
    since = np.zeros(A, np.int32)
    payouts = np.zeros(A)
    n_pay = np.zeros(A, np.int32)
    outcome = np.zeros(A, np.int8)
    wake = wake0.astype(np.int32).copy()
    start = wake.copy()
    pay_by = np.zeros((A, len(marks)))
    r_sum, r_n, r_min, r_max = np.zeros(A), np.zeros(A, np.int32), np.full(A, np.inf), np.zeros(A)
    peak = np.full(A, IB)
    live = np.arange(A)
    for t in range(int(wake.min()) if A else c.window, c.window):
        for k, mk in enumerate(marks):
            if mk == t:
                pay_by[:, k] = payouts
        if live.size == 0:
            continue
        act = live[wake[live] <= t]
        if act.size == 0:
            continue
        if c.funded_days is not None:
            over = (t - start[act]) >= c.funded_days
            outcome[act[over]] = TIMEOUT
            act = act[~over]
        R, L, v, has = days.at(t, row[act])
        m = risk(t, balance[act], max_gain[act]) if callable(risk) else risk[act]
        if c.risk_cap is not None:
            m = np.minimum(m, c.risk_cap)
        if c.lev_funded is not None:
            m = np.minimum(m, c.lev_funded * v)
        _track(r_sum, r_n, r_min, r_max, act[has], m[has])
        m = np.where(has, m * IB, 0.0)
        b0 = balance[act]
        mark = L if c.intraday else R
        static, daily = _breaches(c, b0, b0 + m * mark, _floor(c, peak[act]))
        outcome[act[static]] = BREACH_STATIC
        outcome[act[daily]] = BREACH_DAILY
        ok = ~(static | daily)
        if c.max_risk is not None:
            mr = ok & (m * mark <= -c.max_risk * IB + EPS)
            outcome[act[mr]] = MAX_RISK
            ok &= ~mr
        a, b0 = act[ok], b0[ok]
        b1 = b0 + (m * R)[ok]
        mg = np.maximum(max_gain[a], b1 - b0)
        since[a] += 1
        profit = b1 - IB - keep                                  # what a payout would withdraw
        peak[a] = np.maximum(peak[a], b1)
        pay = profit >= c.min_profit * IB if c.min_profit > 0 else profit > 0
        if c.payout_every is not None:
            pay &= since[a] % c.payout_every == 0
        if c.best_day is not None:
            pay &= mg <= c.best_day * (b1 - base[a])
        if request is not None:
            pay &= request(t, b1, mg)
        payouts[a[pay]] += c.split * profit[pay]
        n_pay[a[pay]] += 1
        b1[pay] = IB + keep
        mg[pay] = 0.0
        since[a[pay]] = 0
        wake[a[pay]] = t + 1 + c.payout_lock
        base[a[pay]] = IB + keep
        balance[a] = b1
        max_gain[a] = mg
        if c.trail_dd is not None:                               # withdrawing down to the floor ends the account
            gone = pay & (b1 <= _floor(c, peak[a]) + EPS)
            outcome[a[gone]] = CASHOUT
        live = live[outcome[live] == RUNNING]
    for k, mk in enumerate(marks):
        if mk >= c.window:
            pay_by[:, k] = payouts
    return {"payouts": payouts, "n_pay": n_pay, "outcome": outcome, "pay_by": pay_by, "peak": peak,
            **_risk_stats(r_sum, r_n, r_min, r_max)}


# ------------------------------------------------------------------------------------------------ skill
def side_moments(tup: DayTuples) -> dict:
    """Moments of the better and the worse side's net R on trade days, and the number of trades per year."""
    R = tup.R[tup.has]
    d = tup.days[tup.has]
    years = (d[-1] - d[0]).astype(int) / 365.25
    Rb, Rw = R.max(axis=1), R.min(axis=1)
    return {"mb": Rb.mean(), "mw": Rw.mean(), "qb": (Rb ** 2).mean(), "qw": (Rw ** 2).mean(),
            "per_year": len(R) / years, "n": len(R)}


def book_moments(p: float, mo: dict) -> tuple[float, float]:
    """Mean and standard deviation of the net R of a buyer who takes the better side with probability p."""
    m = p * mo["mb"] + (1 - p) * mo["mw"]
    return m, float(np.sqrt(p * mo["qb"] + (1 - p) * mo["qw"] - m * m))


def sharpe_at(p: float, mo: dict) -> float:
    m, s = book_moments(p, mo)
    return m / s * np.sqrt(mo["per_year"])


def solve_p(S: float, mo: dict) -> float:
    """Hit rate on the better side at which the book's net annualised Sharpe ratio equals S."""
    return float(brentq(lambda p: sharpe_at(p, mo) - S, 0.3, 0.999, xtol=1e-12))


# ------------------------------------------------------------------------------------------------ paths
def stationary_bootstrap(lo: int, hi: int, n: int, T: int, mean_block: float, rng) -> np.ndarray:
    """Politis–Romano index paths over days lo..hi−1: each step moves to the next day with probability
    1 − 1/mean_block, otherwise jumps to a uniformly drawn day; the sample wraps at its end."""
    span = hi - lo
    jump = rng.random((n, T)) < 1.0 / mean_block
    jump[:, 0] = True
    draws = rng.integers(0, span, size=(n, T))
    idx = np.broadcast_to(np.arange(T), (n, T))
    last = np.maximum.accumulate(np.where(jump, idx, 0), axis=1)
    base = np.take_along_axis(draws, last, axis=1)
    return (lo + (base + idx - last) % span).astype(np.int32)
