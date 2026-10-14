"""The buyer's best state-dependent policy for a challenge contract (plan amendment 3, K7).

Model: each day is an independent draw from the book's own history; a buyer of skill p gets the better side with
probability p; the trade must be taken and only its size is chosen. The objective is the expected sum of payouts
requested within the contract window. Backward induction on a dollar grid gives the policy that is exact for
this model and grid. ``Policy`` turns the tables into the callables that ``contract.evaluate`` and
``contract.fund`` accept, so the same policy can be simulated on any day source, real paths included.

Not in the state: the minimum number of trading days per step (it is enforced by the simulator).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .contract import EPS, IB, Contract, DayTuples


@dataclass(frozen=True)
class Grid:
    h: float = 5.0           # balance step, dollars
    hg: float = 10.0         # best-day step, dollars
    x_max: float = 3000.0    # funded profit cap, dollars


@dataclass
class Atoms:
    """One day's possible outcomes: R and L in stop units, the stop distance v, and the probability w."""

    R: np.ndarray
    L: np.ndarray
    v: np.ndarray
    w: np.ndarray

    @classmethod
    def from_book(cls, tup: DayTuples, lo: int, p: float) -> "Atoms":
        """Every business day from index ``lo``: both sides of a trade day (better side with probability p),
        and a no-trade outcome for a day without a trade."""
        has = tup.has[lo:]
        n = len(has)
        R, L, v = tup.R[lo:][has], tup.L[lo:][has], tup.v[lo:][has]
        b = np.argmax(R, axis=1)
        rows = np.arange(len(R))
        idle = int((~has).sum())
        return cls(R=np.r_[R[rows, b], R[rows, 1 - b], np.zeros(idle)], L=np.r_[L[rows, b], L[rows, 1 - b], np.zeros(idle)],
                   v=np.r_[v, v, np.ones(idle)],
                   w=np.r_[np.full(len(R), p / n), np.full(len(R), (1 - p) / n), np.full(idle, 1.0 / n)])

    def dollars(self, a: float, lev: float | None, cap: float | None, intraday: bool):
        """Dollar result and worst intraday mark of the day at intended risk ``a`` under the published caps."""
        m = np.full(len(self.R), a)
        if cap is not None:
            m = np.minimum(m, cap)
        if lev is not None:
            m = np.minimum(m, lev * self.v)
        m = m * IB
        return m * self.R, m * (self.L if intraday else self.R)


def _split(pos: np.ndarray):
    lo = np.floor(pos + 1e-9)
    return lo.astype(np.int64), pos - lo


# ------------------------------------------------------------------------------------------------ evaluation
def solve_step(atoms: Atoms, c: Contract, actions, grid: Grid, target: float, reward: np.ndarray, horizon: int):
    """One evaluation step. States are balances floor + h·(1..nb) below the target. ``reward[t]`` is the value
    of passing at the close of day t. Returns the value [horizon + 1, nb] and the action index [horizon, nb]."""
    floor = (1 - c.static_dd) * IB
    nb = int(round((IB * (1 + target) - floor) / grid.h)) - 1
    b = floor + grid.h * np.arange(1, nb + 1)
    goal = IB * (1 + target)
    T, P = [], []
    for a in actions:
        dB, dW = atoms.dollars(a, c.lev_eval, None, c.intraday)
        worst = b[:, None] + dW[None, :]
        dead = worst <= floor + EPS
        if c.daily_dd is not None:
            ref = (1 - c.daily_dd) * b if c.daily_ref == "balance" else b - c.daily_dd * IB
            dead |= worst <= ref[:, None] + EPS
        b1 = b[:, None] + dB[None, :]
        win = ~dead & (b1 >= goal - EPS)
        alive = ~dead & ~win
        lo, frac = _split((b1 - floor) / grid.h - 1)
        w = atoms.w[None, :] * alive
        M = np.zeros((nb, nb))
        rows = np.broadcast_to(np.arange(nb)[:, None], lo.shape)
        np.add.at(M, (rows, np.clip(lo, 0, nb - 1)), w * (1 - frac))
        np.add.at(M, (rows, np.clip(lo + 1, 0, nb - 1)), w * frac)
        T.append(M)
        P.append((atoms.w[None, :] * win).sum(axis=1))
    V = np.zeros((horizon + 1, nb))
    pol = np.zeros((horizon, nb), np.uint8)
    for t in range(horizon - 1, -1, -1):
        Q = np.stack([M @ V[t + 1] + p * reward[t] for M, p in zip(T, P)])
        pol[t] = Q.argmax(axis=0)
        V[t] = Q.max(axis=0)
    return V, pol


# ------------------------------------------------------------------------------------------------ funded
class _Kernel:
    """Transition of the funded state (profit x, best day g) for one size."""

    def __init__(self, atoms: Atoms, a: float, c: Contract, grid: Grid, x: np.ndarray, ng: int):
        dB, dW = atoms.dollars(a, c.lev_funded, c.risk_cap, c.intraday)
        w = atoms.w.copy()
        if c.max_risk is not None:
            w = np.where(dW <= -c.max_risk * IB + EPS, 0.0, w)          # the Max Risk Rule closes the account
        lo, frac = _split(dB / grid.h)
        self.o_min, self.o_max = int(lo.min()), int(lo.max()) + 1
        n_off = self.o_max - self.o_min + 1
        off = np.arange(self.o_min, self.o_max + 1)
        self.jo = np.clip(np.rint(np.maximum(off * grid.h, 0.0) / grid.hg).astype(np.int64), 0, ng - 1)

        def kernel(weight):
            k = np.bincount(lo - self.o_min, weights=weight * (1 - frac), minlength=n_off)
            return k + np.bincount(lo + 1 - self.o_min, weights=weight * frac, minlength=n_off)

        self.full = kernel(w)
        bal = IB + x
        cushion = bal - (1 - c.static_dd) * IB
        if c.daily_dd is not None:
            cushion = np.minimum(cushion, c.daily_dd * bal if c.daily_ref == "balance" else c.daily_dd * IB)
        self.near = np.flatnonzero(cushion <= -dW.min() + EPS)             # rows where some outcome breaches
        self.rows = np.stack([kernel(np.where(dW <= -cushion[i] + EPS, 0.0, w)) for i in self.near]) \
            if self.near.size else np.zeros((0, n_off))
        self.ng = ng
        self.cols = np.maximum(np.arange(ng)[None, :], self.jo[:, None])   # [offset, g] -> g after the day
        # jo never falls as the offset rises, so "the best day is unchanged" means the first cut[g] offsets
        self.cut = np.array([int((self.jo <= j).sum()) for j in range(ng)])

    def apply(self, U: np.ndarray) -> np.ndarray:
        """Expected value after the day for every state, given the value U[x, g] at the close."""
        nx, ng = U.shape
        n_off = len(self.full)
        lo_pad, hi_pad = max(0, -self.o_min), max(0, self.o_max)
        Up = np.pad(U, ((lo_pad, hi_pad), (0, 0)), mode="edge")
        base = lo_pad + self.o_min                                          # row of Up that offset o_min reaches from x[0]
        out = np.empty_like(U)
        for j in range(ng):                                                 # outcomes that leave the best day at g
            out[:, j] = np.correlate(Up[base:, j], self.full[: self.cut[j]], mode="valid")[:nx]
        rows = base + np.arange(n_off)[:, None] + np.arange(nx)[None, :]    # outcomes that set a new best day
        Z = self.full[:, None] * Up[rows, self.jo[:, None]]
        S = np.vstack([np.cumsum(Z[::-1], axis=0)[::-1], np.zeros((1, nx))])  # S[m] = sum of Z over offsets >= m
        out += S[self.cut].T
        if self.near.size:                                                  # rows near the floor: surviving outcomes only
            M = Up[base + self.near[:, None] + np.arange(n_off)[None, :]]   # [row, offset, g]
            M = np.take_along_axis(M, np.broadcast_to(self.cols[None], M.shape), axis=2)
            out[self.near] = np.einsum("no,noj->nj", self.rows, M)
        return out


def solve_funded(atoms: Atoms, c: Contract, actions, grid: Grid, free_timing: bool, keep_tables: bool = True):
    """Funded stage. Returns F0[t], the value of an account whose first (or next post-payout) trading day is t,
    and, if asked, the action table [window, nx, ng] and the request table [window, nx, ng]. The request table
    says whether to take a payout at that state if the rules allow one; the simulator applies the rules exactly."""
    floor_x = -c.static_dd * IB
    nx = int(round((grid.x_max - floor_x) / grid.h))
    x = floor_x + grid.h * np.arange(1, nx + 1)
    ng = int(round(c.best_day * grid.x_max / grid.hg)) + 2 if c.best_day is not None else 1
    g = grid.hg * np.arange(ng)
    i0 = int(round(-floor_x / grid.h)) - 1                                   # index of x = 0
    kernels = [_Kernel(atoms, a, c, grid, x, ng) for a in actions]
    eligible = (x[:, None] >= c.min_profit * IB - EPS) if c.min_profit > 0 else (x[:, None] > 0)
    eligible = np.broadcast_to(eligible, (nx, ng)).copy()
    if c.best_day is not None:
        eligible &= g[None, :] <= c.best_day * x[:, None] + EPS
    cash = c.split * np.broadcast_to(x[:, None], (nx, ng))
    W = c.window
    F0 = np.zeros(W + c.payout_lock + 2)
    act = np.zeros((W, nx, ng), np.uint8) if keep_tables else None
    req = np.zeros((W, nx, ng), bool) if keep_tables else None
    F_next = np.zeros((nx, ng))
    for t in range(W - 1, -1, -1):
        take = cash + F0[t + 1 + c.payout_lock]
        want = take >= F_next if free_timing else np.ones((nx, ng), bool)   # take the payout if one is allowed
        U = np.where(eligible & want, take, F_next)
        Q = np.stack([k.apply(U) for k in kernels])
        F_next = Q.max(axis=0)
        F0[t] = F_next[i0, 0]
        if keep_tables:
            act[t] = Q.argmax(axis=0)
            req[t] = want
    return {"F0": F0, "act": act, "req": req, "x": x, "g": g, "i0": i0}


# ------------------------------------------------------------------------------------------------ whole contract
@dataclass
class Policy:
    """Tables from ``solve`` and the callables the simulator takes."""

    grid: Grid
    c: Contract
    eval_actions: np.ndarray
    fund_actions: np.ndarray
    pol1: np.ndarray
    pol2: np.ndarray
    act: np.ndarray
    req: np.ndarray
    value: float                 # the model's value of a purchase under this policy

    def eval_risk(self, phase, t, balance):
        floor = (1 - self.c.static_dd) * IB
        idx = np.rint((balance - floor) / self.grid.h).astype(np.int64) - 1
        out = np.empty(len(balance))
        for ph, pol in ((0, self.pol1), (1, self.pol2)):
            sel = phase == ph
            if sel.any():
                tt = min(t, pol.shape[0] - 1)
                out[sel] = self.eval_actions[pol[tt, np.clip(idx[sel], 0, pol.shape[1] - 1)]]
        return out

    def _ij(self, balance, max_gain):
        nx, ng = self.act.shape[1:]
        i = np.clip(np.rint((balance - (1 - self.c.static_dd) * IB) / self.grid.h).astype(np.int64) - 1, 0, nx - 1)
        j = np.clip(np.rint(max_gain / self.grid.hg).astype(np.int64), 0, ng - 1)
        return i, j

    def fund_risk(self, t, balance, max_gain):
        i, j = self._ij(balance, max_gain)
        return self.fund_actions[self.act[min(t, self.act.shape[0] - 1), i, j]]

    def request(self, t, balance, max_gain):
        i, j = self._ij(balance, max_gain)
        return self.req[min(t, self.req.shape[0] - 1), i, j]


def solve(atoms: Atoms, c: Contract, eval_actions, fund_actions, grid: Grid = Grid(), free_timing: bool = True) -> Policy:
    """Backward induction through the funded stage, step 2 and step 1 of contract ``c``."""
    assert c.trail_dd is None and c.buffer == 0, "the solver covers static limits without a retained buffer"
    eval_actions, fund_actions = np.asarray(eval_actions, float), np.asarray(fund_actions, float)
    fd = solve_funded(atoms, c, fund_actions, grid, free_timing)
    H = c.window if c.eval_days is None else min(c.eval_days, c.window)
    F0 = np.r_[fd["F0"], np.zeros(H + c.fund_gap + 1)]
    two = c.target_p2 is not None
    reward2 = np.array([F0[t + c.fund_gap] for t in range(H)])
    V2, pol2 = solve_step(atoms, c, eval_actions, grid, c.target_p2 if two else c.target_p1, reward2, H)
    start = int(round(c.static_dd * IB / grid.h)) - 1                         # index of the initial balance
    if not two:
        return Policy(grid, c, eval_actions, fund_actions, pol2, pol2, fd["act"], fd["req"], float(V2[0, start]))
    V2p = np.vstack([V2, np.zeros((c.phase_gap + 2, V2.shape[1]))])
    reward1 = np.array([V2p[t + 1 + c.phase_gap, start] for t in range(H)])
    V1, pol1 = solve_step(atoms, c, eval_actions, grid, c.target_p1, reward1, H)
    return Policy(grid, c, eval_actions, fund_actions, pol1, pol2, fd["act"], fd["req"], float(V1[0, start]))
