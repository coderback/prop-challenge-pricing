"""The state-dependent policy solver (plan amendment 3, K7): transition arithmetic, gate G4 (a constant table
reproduces the fixed-size simulator path by path) and the solver's value against simulation on independent days."""
import numpy as np
import pytest

from propcontract.contract import IB, PASS, BookDays, Contract, DayTuples, MatrixDays, evaluate, fund
from propcontract.optimal import Atoms, Grid, _Kernel, solve


def toy_book(n=600, seed=0, stop_share=0.45):
    """Both sides of a stopped intraday trade: one side's close mirrors the other's, the stop caps each loss at -1."""
    rng = np.random.default_rng(seed)
    move = rng.normal(0.0, 1.1, n)
    R = np.stack([np.clip(move, -1.0, None), np.clip(-move, -1.0, None)], axis=1) - 0.01
    dip = np.abs(rng.normal(0.0, 0.5, (n, 2)))
    L = np.minimum(R, np.maximum(-1.0, np.minimum(R, 0.0) - dip))
    L = np.where(R <= -1.0, R, L)
    has = rng.random(n) > 0.05
    days = np.arange("2010-01-04", n, dtype="datetime64[D]")
    return DayTuples(days, has, np.where(has[:, None], R, 0.0), np.where(has[:, None], L, 0.0), np.full(n, 0.012))


def small_contract(**kw):
    return Contract(**{"window": 150, "eval_days": 100, "lev_eval": 10.0, "lev_funded": 0.9, "risk_cap": 0.01} | kw)


def test_kernel_matches_direct_sum():
    tup = toy_book()
    atoms = Atoms.from_book(tup, 0, 0.5)
    c, grid = small_contract(), Grid(h=5.0, hg=10.0, x_max=600.0)
    nx = int(round((grid.x_max + c.static_dd * IB) / grid.h))
    x = -c.static_dd * IB + grid.h * np.arange(1, nx + 1)
    ng = int(round(c.best_day * grid.x_max / grid.hg)) + 2
    k = _Kernel(atoms, 0.01, c, grid, x, ng)
    U = np.random.default_rng(1).random((nx, ng))
    got = k.apply(U)
    lo_pad, hi_pad = max(0, -k.o_min), max(0, k.o_max)
    Up = np.pad(U, ((lo_pad, hi_pad), (0, 0)), mode="edge")
    base = lo_pad + k.o_min
    near = {int(i): r for i, r in zip(k.near, k.rows)}
    want = np.zeros_like(U)
    for i in list(range(0, nx, 37)) + [int(v) for v in k.near[:5]]:
        ker = near.get(i, k.full)
        for j in range(ng):
            want[i, j] = sum(ker[m] * Up[base + i + m, max(j, k.jo[m])] for m in range(len(ker)))
        assert np.allclose(got[i], want[i], atol=1e-10), i
    assert abs(k.full.sum() - 1.0) < 1e-9                       # every outcome lands somewhere
    dB, _ = atoms.dollars(0.01, c.lev_funded, c.risk_cap, True)
    off = np.arange(k.o_min, k.o_max + 1)
    assert abs((k.full * off).sum() * grid.h - (atoms.w * dB).sum()) < 1e-9   # the split keeps the mean exact


def test_constant_table_reproduces_fixed_sizes():
    """Gate G4."""
    tup = toy_book()
    atoms = Atoms.from_book(tup, 0, 0.5)
    c = small_contract()
    pol = solve(atoms, c, [0.03], [0.01], Grid(x_max=600.0), free_timing=False)
    rng = np.random.default_rng(3)
    n = 400
    gidx = rng.integers(0, len(tup.days), size=(n, c.window)).astype(np.int32)
    days = BookDays(tup, gidx=gidx, take_better=rng.random((n, c.window)) < 0.5)
    row = np.arange(n)
    ev_fix = evaluate(days, row, np.full(n, 0.03), c)
    ev_pol = evaluate(days, row, pol.eval_risk, c)
    for key in ("outcome", "pass_t", "p1_t", "end_t"):
        assert np.array_equal(ev_fix[key], ev_pol[key]), key
    won = np.flatnonzero(ev_fix["outcome"] == PASS)
    assert won.size > 10
    wake = ev_fix["pass_t"][won] + c.fund_gap
    fd_fix = fund(days, won, wake, np.full(won.size, 0.01), c)
    fd_pol = fund(days, won, wake, pol.fund_risk, c, request=pol.request)
    assert np.allclose(fd_fix["payouts"], fd_pol["payouts"]) and np.array_equal(fd_fix["n_pay"], fd_pol["n_pay"])
    assert np.array_equal(fd_fix["outcome"], fd_pol["outcome"])


def simulate(tup, c, pol, p, n, seed):
    rng = np.random.default_rng(seed)
    gidx = rng.integers(0, len(tup.days), size=(n, c.window)).astype(np.int32)
    days = BookDays(tup, gidx=gidx, take_better=rng.random((n, c.window)) < p)
    ev = evaluate(days, np.arange(n), pol.eval_risk, c)
    won = np.flatnonzero(ev["outcome"] == PASS)
    V = np.zeros(n)
    if won.size:
        V[won] = fund(days, won, ev["pass_t"][won] + c.fund_gap, pol.fund_risk, c, request=pol.request)["payouts"]
    return V


@pytest.mark.parametrize("free", [False, True])
def test_solver_value_matches_simulation(free):
    """The solver's value for its own policy against that policy on independent days (min_days is not in the
    state, so it is switched off here)."""
    tup = toy_book(seed=5)
    p = 0.55
    atoms = Atoms.from_book(tup, 0, p)
    c = small_contract(min_days=0)
    pol = solve(atoms, c, [0.01, 0.02, 0.03, 0.04], [0.005, 0.01], Grid(), free_timing=free)   # the cap must not bind
    V = simulate(tup, c, pol, p, 60_000, seed=11)
    se = V.std(ddof=1) / np.sqrt(len(V))
    assert abs(V.mean() - pol.value) < 3 * se + 0.03 * pol.value, (V.mean(), pol.value, se)


def test_free_choice_never_lowers_the_model_value():
    tup = toy_book(seed=7)
    atoms = Atoms.from_book(tup, 0, 0.5)
    c = small_contract(min_days=0)
    g = Grid(x_max=600.0)
    fixed = solve(atoms, c, [0.03], [0.01], g, free_timing=False).value
    sized = solve(atoms, c, [0.01, 0.02, 0.03, 0.04], [0.005, 0.01], g, free_timing=False).value
    both = solve(atoms, c, [0.01, 0.02, 0.03, 0.04], [0.005, 0.01], g, free_timing=True).value
    assert fixed <= sized + 1e-9 <= both + 2e-9


def test_matrix_days_accept_a_policy():
    tup = toy_book()
    c = small_contract()
    pol = solve(Atoms.from_book(tup, 0, 0.5), c, [0.02, 0.04], [0.01], Grid(x_max=600.0))
    R = np.random.default_rng(2).normal(0, 0.6, (50, c.window)).clip(-1)
    ev = evaluate(MatrixDays(R, v=0.012), np.arange(50), pol.eval_risk, c)
    assert set(np.unique(ev["outcome"])) <= {1, 2, 3, 4}
