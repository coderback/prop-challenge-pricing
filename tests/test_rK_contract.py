import numpy as np
import pandas as pd

from propcontract.legacy.evalsim import Book, SimConfig, run_funded, run_one
from propcontract.legacy.trades import TradeSet
from propcontract.contract import (BREACH_DAILY, BREACH_STATIC, CASHOUT, MAX_RISK, PASS, TIMEOUT, BookDays, Contract,
                                   DayTuples,
                                   MatrixDays, book_moments, evaluate, fund, sharpe_at, side_moments, solve_p,
                                   stationary_bootstrap)

ONE = np.zeros(1, int)


def _flat(R, n=400):
    """One path that repeats the daily result(s) R; the worst mark is min(R, 0)."""
    R = np.resize(np.asarray(R, float), n)[None, :]
    return MatrixDays(R, np.minimum(R, 0.0))


def _ts(day0, close, low):
    n = len(day0)
    trades = pd.DataFrame({"R": close, "Rw": close, "stop_dist": np.full(n, 10.0), "entry": np.full(n, 1000.0)})
    return TradeSet(trades, np.asarray(day0, "datetime64[D]"), np.arange(n), np.ones(n, int),
                    np.asarray(close, float), np.asarray(low, float))


def test_two_steps_with_gap_and_minimum_days():
    res = evaluate(_flat(2.0), ONE, np.array([0.01]), Contract.s2())          # +$200 a day
    assert res["outcome"][0] == PASS and res["p1_t"][0] == 4                   # $11,000 on the fifth day
    assert res["pass_t"][0] == 9                                               # restart on day 7, +$600 by day 9
    quick = evaluate(_flat(2.0), ONE, np.array([0.06]), Contract.s2())         # +12% on day one
    assert quick["p1_t"][0] == 2                                               # held back by the 3-day minimum
    assert evaluate(_flat(2.0), ONE, np.array([0.06]), Contract.s2(min_days=0))["p1_t"][0] == 0
    one = evaluate(_flat(2.0), ONE, np.array([0.01]), Contract.s2(target_p2=None))
    assert one["outcome"][0] == PASS and one["pass_t"][0] == 4


def test_floors_intraday_and_at_the_close():
    dip = MatrixDays(np.full((1, 50), 0.1), np.full((1, 50), -6.0))            # −6% intraday, +0.1% at the close
    assert evaluate(dip, ONE, np.array([0.01]), Contract.s2(eval_days=50))["outcome"][0] == BREACH_DAILY
    assert evaluate(dip, ONE, np.array([0.01]), Contract.s2(eval_days=50, daily_dd=None))["outcome"][0] == TIMEOUT
    assert evaluate(dip, ONE, np.array([0.01]), Contract.s2(eval_days=50, intraday=False))["outcome"][0] == TIMEOUT
    slide = evaluate(_flat(-1.0), ONE, np.array([0.01]), Contract.s2())        # −1% a day
    assert slide["outcome"][0] == BREACH_STATIC
    crash = MatrixDays(np.full((1, 50), -11.0))
    assert evaluate(crash, ONE, np.array([0.01]), Contract.s2(eval_days=50))["outcome"][0] == BREACH_STATIC   # static first


def test_daily_floor_reference_and_step_maturity():
    R = np.r_[np.full(4, 2.0), -5.3, np.zeros(60)][None, :]                    # +8%, then −5.3% in a day
    days = MatrixDays(R)
    assert evaluate(days, ONE, np.array([0.01]), Contract.s2(eval_days=60, daily_ref="initial"))["outcome"][0] == BREACH_DAILY
    assert evaluate(days, ONE, np.array([0.01]), Contract.s2(eval_days=60))["outcome"][0] == TIMEOUT   # 5% of $10,800 = $540
    idle = evaluate(_flat(0.0), ONE, np.array([0.01]), Contract.lim(window=400))
    assert idle["outcome"][0] == TIMEOUT
    late = np.r_[np.zeros(30), np.full(10, 2.0)][None, :]                      # the target only after day 30
    assert evaluate(MatrixDays(late), ONE, np.array([0.01]), Contract.lim(window=40))["outcome"][0] == TIMEOUT
    assert evaluate(MatrixDays(late), ONE, np.array([0.01]), Contract.lim(maturity=False, window=40))["p1_t"][0] == 34


def test_leverage_cap_scales_the_position():
    days = MatrixDays(np.full((1, 50), 2.0), v=0.001)                           # 1:10 leverage allows 1% risk
    capped = evaluate(days, ONE, np.array([0.05]), Contract.s2(eval_days=50, lev_eval=10.0))
    free = evaluate(days, ONE, np.array([0.05]), Contract.s2(eval_days=50))
    assert capped["p1_t"][0] == 4 and free["p1_t"][0] == 2


def test_funded_payout_every_21_days_matches_the_old_model():
    res = fund(_flat(0.2, 60), ONE, ONE, np.array([0.01]), Contract.s2(window=60))      # +$20 a day
    assert res["n_pay"][0] == 2 and np.isclose(res["payouts"][0], 2 * 0.8 * 21 * 20)
    spiky = np.r_[30.0, np.full(59, 0.01)][None, :]
    assert fund(MatrixDays(spiky), ONE, ONE, np.array([0.01]), Contract.s2(window=60))["n_pay"][0] == 0
    assert fund(MatrixDays(spiky), ONE, ONE, np.array([0.01]), Contract.s2(window=60, best_day=None))["n_pay"][0] == 1    # later 21-day profits stay under 2%


def test_funded_on_demand_pays_at_the_first_eligible_close_then_locks():
    c = Contract(window=20, max_risk=None, lev_eval=None)                       # on demand, 2-day lock
    res = fund(_flat(0.5, 20), ONE, ONE, np.array([0.01]), c, marks=(4, 20))    # +$50 a day
    # $200 after 4 days (best day 25% of profit) -> paid on day 3; locked on days 4-5; again on days 9 and 15
    assert res["n_pay"][0] == 3 and np.isclose(res["payouts"][0], 3 * 160.0)
    assert np.isclose(res["pay_by"][0, 0], 160.0) and np.isclose(res["pay_by"][0, 1], 480.0)
    small = fund(_flat(0.5, 20), ONE, ONE, np.array([0.01]), Contract(window=20, max_risk=None, min_profit=0.0))
    assert small["n_pay"][0] == 4 and np.isclose(small["payouts"][0], 4 * 120.0)    # day 3: best day is a third
    lim = fund(_flat(0.5, 60), ONE, ONE, np.array([0.01]), Contract.lim(window=60))
    assert lim["n_pay"][0] == 3 and np.isclose(lim["payouts"][0], 3 * 0.8 * 20 * 50)    # sweeps every 20 days


def test_funded_caps_and_max_risk_rule():
    days = MatrixDays(np.full((1, 30), 1.0), np.full((1, 30), -3.2), v=0.004)
    hit = fund(days, ONE, ONE, np.array([0.01]), Contract(window=30))           # −3.2% open loss
    assert hit["outcome"][0] == MAX_RISK and hit["payouts"][0] == 0
    assert fund(days, ONE, ONE, np.array([0.01]), Contract(window=30, max_risk=None))["outcome"][0] == 0
    ftg = fund(days, ONE, ONE, np.array([0.025]), Contract.alpha(2.0, "FTG", window=30, max_risk=None, best_day=None))
    std = fund(days, ONE, ONE, np.array([0.025]), Contract.alpha(2.0, "STD", window=30, max_risk=None, best_day=None))
    # FTG risks min(2.5%, 1%, 1.0 × 0.4%) = 0.4% a day; STD risks min(2.5%, 2.0 × 0.4%) = 0.8% a day
    assert np.isclose(ftg["payouts"][0] / ftg["n_pay"][0], 0.8 * 200.0)         # 5 days × $40
    assert np.isclose(std["payouts"][0] / std["n_pay"][0], 0.8 * 240.0)         # 3 days × $80


def test_agrees_with_evalsim_path_by_path():
    rng = np.random.default_rng(7)
    days = pd.bdate_range("2020-01-01", periods=700).to_numpy().astype("datetime64[D]")
    G = len(days)
    has = rng.random(G) < 0.95
    R = rng.normal(0.0, 0.6, (G, 2))
    L = np.minimum(R, -np.abs(rng.normal(0.0, 0.4, (G, 2))))
    tup = DayTuples(days, has, np.where(has[:, None], R, 0.0), np.where(has[:, None], L, 0.0), np.ones(G))
    n, T, H = 80, 300, 200
    start = rng.integers(0, G - T, n)
    take = rng.random((n, T)) < 0.55
    book = BookDays(tup, start=start, take_better=take)
    c = Contract.s2(eval_days=H, window=T)
    cfg = SimConfig(horizon_days=H, keepalive_days=25)
    seen = set()
    for r, rf in ((0.004, 0.004), (0.02, 0.01), (0.03, 0.03), (0.045, 0.0066)):
        cfg.r = r
        ev = evaluate(book, np.arange(n), np.full(n, r), c)
        won = np.flatnonzero(ev["outcome"] == PASS)
        fd = fund(book, won, ev["pass_t"][won] + c.fund_gap, np.full(len(won), rf), c)
        pay = dict(zip(won.tolist(), fd["payouts"].tolist()))
        for i in range(n):
            g = start[i] + np.arange(T)
            side = np.where(take[i], tup.better[g], 1 - tup.better[g])
            day_side = np.zeros(G, int)
            day_side[g] = side
            idx = np.flatnonzero(has)
            ts = _ts(days[idx], tup.R[idx, day_side[idx]], tup.L[idx, day_side[idx]])
            bk = Book(ts, days)
            old = run_one(bk, int(start[i]), cfg)
            code = {"pass": PASS, "breach_static": BREACH_STATIC, "breach_daily": BREACH_DAILY, "timeout": TIMEOUT}
            assert code[old["outcome"]] == ev["outcome"][i]
            assert (old["p1_day"] if old["p1_day"] is not None else -1) == ev["p1_t"][i]
            seen.add(old["outcome"])
            if old["outcome"] == "pass":
                assert old["days"] == ev["pass_t"][i]
                f = run_funded(bk, int(start[i]) + old["days"] + 3, int(start[i]) + T, rf, cfg)
                assert np.isclose(f["payouts"], pay[i], rtol=0, atol=1e-6)
    assert {"pass", "breach_static", "timeout"} <= seen


def test_day_tuples_from_tradesets():
    days = pd.bdate_range("2024-01-01", periods=5).to_numpy().astype("datetime64[D]")
    d0 = [days[0], days[2], np.datetime64("2023-12-29")]                        # the last one is off the axis
    tup = DayTuples.from_tradesets(_ts(d0, [0.5, -1.0, 9.0], [-0.2, -1.0, 9.0]),
                                   _ts(d0, [-0.6, 0.9, 9.0], [-0.7, -0.1, 9.0]), days)
    assert tup.has.tolist() == [True, False, True, False, False]
    assert tup.R[0].tolist() == [0.5, -0.6] and tup.L[2].tolist() == [-1.0, -0.1]
    assert tup.better.tolist()[0] == 0 and tup.better.tolist()[2] == 1
    assert np.isclose(tup.v[0], 0.01)


def test_skill_calibration_hits_the_target_sharpe():
    rng = np.random.default_rng(3)
    days = pd.bdate_range("2010-01-01", periods=2500).to_numpy().astype("datetime64[D]")
    x = rng.normal(0, 0.5, len(days))
    R = np.c_[x - 0.004, -x - 0.004]                                            # long and short, each paying a cost
    mo = side_moments(DayTuples(days, np.ones(len(days), bool), R, np.minimum(R, 0), np.ones(len(days))))
    assert sharpe_at(0.5, mo) < 0                                               # a coin flip loses the spread
    ps = [solve_p(S, mo) for S in (0.0, 0.3, 1.0, 2.0)]
    assert ps == sorted(ps) and 0.5 < ps[0] < ps[-1] < 0.6
    assert all(np.isclose(sharpe_at(p, mo), S, atol=1e-8) for p, S in zip(ps, (0.0, 0.3, 1.0, 2.0)))
    take = rng.random((400, len(days))) < ps[2]                                 # simulate S = 1.0
    best = np.argmax(R, axis=1)
    got = np.where(take, R[np.arange(len(days)), best], R[np.arange(len(days)), 1 - best])
    m, s = book_moments(ps[2], mo)
    assert np.isclose(got.mean(), m, atol=0.002) and np.isclose(got.std(), s, atol=0.005)


def test_stationary_bootstrap_blocks():
    idx = stationary_bootstrap(100, 600, 200, 400, 21, np.random.default_rng(1))
    assert idx.shape == (200, 400) and idx.min() >= 100 and idx.max() < 600
    step = np.diff(idx, axis=1)
    runs_on = (step == 1) | (step == -499)                                      # next day, or the wrap
    assert abs((~runs_on).mean() - 1 / 21) < 0.01


def _path(R):
    R = np.asarray(R, float)[None, :]
    return MatrixDays(R, np.minimum(R, 0.0))


def test_trailing_limit_follows_the_highest_close_and_stops_at_the_initial_balance():
    c = Contract.s2(target_p1=0.20, target_p2=None, trail_dd=0.06, daily_dd=None, eval_days=40, min_days=0)
    # +2%, +2% (high 10,400, floor 9,800), then -3%, -3% -> 9,800: breach on the fourth day
    res = evaluate(_path([2, 2, -3, -3] + [0] * 36), ONE, np.array([0.01]), c)
    assert res["outcome"][0] == BREACH_STATIC and res["end_t"][0] == 3
    # the same losses from the start (floor 9,400) leave the account alive
    assert evaluate(_path([-3, -2.9] + [0] * 38), ONE, np.array([0.01]), c)["outcome"][0] == TIMEOUT
    # +8% lifts the floor to the initial balance and no further: 10,010 survives, 10,000 does not
    assert evaluate(_path([8, -7.9] + [0] * 38), ONE, np.array([0.01]), c)["outcome"][0] == TIMEOUT
    assert evaluate(_path([8, -8.0] + [0] * 38), ONE, np.array([0.01]), c)["outcome"][0] == BREACH_STATIC
    # a static limit of the same size would have survived the first path
    s = Contract.s2(target_p1=0.20, target_p2=None, static_dd=0.06, daily_dd=None, eval_days=40, min_days=0)
    assert evaluate(_path([2, 2, -3, -3] + [0] * 36), ONE, np.array([0.01]), s)["outcome"][0] == TIMEOUT


def test_retained_buffer_and_window_best_day():
    c = Contract.s2(window=30, trail_dd=0.05, daily_dd=None, buffer=0.03, min_profit=0.01, best_day=None,
                    payout_every=None, split=0.9)
    fd = fund(_path([1] * 30), ONE, ONE, np.array([0.01]), c)                  # +$100 a day
    # first payout at +4% on day 3 (withdraws $100, leaves $10,300), then one a day
    assert fd["n_pay"][0] == 27 and abs(fd["payouts"][0] - 27 * 90.0) < 1e-6 and fd["outcome"][0] == 0
    # 15% best day against the window's profit: the first window is judged on the whole profit ...
    b = Contract.s2(window=30, trail_dd=0.05, daily_dd=None, buffer=0.03, min_profit=0.01, best_day=0.15,
                    payout_every=None, split=0.9)
    first = fund(_path([0.5] * 30), ONE, ONE, np.array([0.01]), b)             # +$50 a day: 50 / 400 = 12.5% on day 7
    # ... so it pays $100 at +4% (day 8). Later windows are judged on their own profit: a $50 day needs $333 of
    # new profit, reached at $350 after seven more days, three times before the window ends
    assert first["n_pay"][0] == 4 and abs(first["payouts"][0] - (90.0 + 3 * 315.0)) < 1e-6


def test_withdrawing_to_the_floor_closes_a_trailing_account():
    c = Contract.s2(window=30, trail_dd=0.04, daily_dd=None, min_profit=0.05, best_day=None, payout_every=None)
    fd = fund(_path([1] * 30), ONE, ONE, np.array([0.01]), c)                  # +5% on day 4: floor at 10,000
    assert fd["n_pay"][0] == 1 and abs(fd["payouts"][0] - 400.0) < 1e-6 and fd["outcome"][0] == CASHOUT
    keep = Contract.s2(window=30, trail_dd=0.04, daily_dd=None, min_profit=0.02, buffer=0.03, best_day=None,
                       payout_every=None)
    fd = fund(_path([1] * 30), ONE, ONE, np.array([0.01]), keep)               # leaves 3% in: the account stays open
    assert fd["outcome"][0] == 0 and fd["n_pay"][0] >= 2
    early = Contract.s2(window=30, trail_dd=0.04, daily_dd=None, min_profit=0.02, best_day=None, payout_every=None)
    fd = fund(_path([1] * 30), ONE, ONE, np.array([0.01]), early)              # paid at +2% each time: floor stays at 9,800
    assert fd["outcome"][0] == 0 and fd["n_pay"][0] == 15 and abs(fd["payouts"][0] - 15 * 160.0) < 1e-6
