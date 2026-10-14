"""Figures, table fragments and number macros for the contract paper, from paper/prop_contract/results
(written by ``research/run_K.py export``). Run from the repository root:

    python paper/prop_contract/make_exhibits.py

fig_map    pass probability and value by evaluation risk and skill (Figure 1)
fig_fee    fee against the no-skill value by account size (Figure 2)
fig_skill  value by skill; sizing against skill by horizon (Figure 3)
fig_tests  the 24 tests' Sharpe ratios with 90% intervals (Figure 4)
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mt
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
RES = HERE / "results"
H = json.loads((RES / "headline.json").read_text(encoding="utf-8"))
K1 = pd.read_csv(RES / "K1_map.csv", dtype={"skill": str})
K2 = pd.read_csv(RES / "K2_rules.csv", dtype={"skill": str})
X1 = pd.read_csv(RES / "X1_claim_exclusion.csv")
LIM = pd.read_csv(RES / "K3_lim_replication.csv")
REAL = pd.read_csv(RES / "K3_real_through_lim.csv")
GAUSS = pd.read_csv(RES / "K3_normal_through_alpha.csv", dtype={"skill": str})
# amendments 1-5 (research/export_paper2.py)
EXT = json.loads((RES / "extensions.json").read_text(encoding="utf-8"))
FEES = json.loads((RES / "FEES_alpha_2026-10-13.json").read_text(encoding="utf-8"))["plans"]
K5 = pd.read_csv(RES / "K5_horizon.csv", dtype={"skill": str})
K5D = pd.read_csv(RES / "K5_D.csv")
K6 = pd.read_csv(RES / "K6_books.csv")
K7 = pd.read_csv(RES / "K7_classes.csv", dtype={"skill": str})
K8 = pd.read_csv(RES / "K8_plans.csv", dtype={"skill": str})
K9 = pd.read_csv(RES / "K9_real_books.csv")
SLIP = pd.read_csv(RES / "K_slippage.csv")
POLICY = pd.read_csv(RES / "K7_policy_step1.csv")
BONUS = pd.read_csv(RES / "K_bonus.csv", dtype={"skill": str})

# palette: validated with the dataviz checker on a white surface (ordinal blue ramp; categorical blue/orange)
BLUES = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"]
C1, C2 = "#2a78d6", "#eb6834"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e4e0"
plt.rcParams.update({"font.size": 8, "axes.titlesize": 8.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
                     "axes.axisbelow": True, "legend.frameon": False, "lines.linewidth": 1.5})
SKILLS = ["coin", "0.0", "0.3", "1.0", "2.0"]
NAME = {"coin": "Coin flip", "0.0": "0", "0.15": "0.15", "0.3": "0.3", "0.5": "0.5", "0.75": "0.75", "1.0": "1.0",
        "1.5": "1.5", "2.0": "2.0"}
ALL = ["coin", "0.0", "0.15", "0.3", "0.5", "0.75", "1.0", "1.5", "2.0"]
P = {str(r["skill"]): r for r in H["skill"]}
POL = {k: v for k, v in H["policy"].items()}


def pol(skill, regime):
    r, rf = POL[f"{'coin' if skill == 'coin' else float(skill)}|{regime}"]
    return round(r * 100, 4), round(rf * 100, 4)


def cell(skill, regime, r=None, rf=None):
    r0, rf0 = pol(skill, regime)
    r, rf = r0 if r is None else r, rf0 if rf is None else rf
    return K1[(K1.skill == skill) & (K1.regime == regime) & (K1.r_pct == r) & (K1.rf_pct == rf)].iloc[0]


def money(x, d=0):
    return f"{'$-$' if x < 0 else ''}\\${abs(x):,.{d}f}"


def save(fig, name):
    fig.savefig(HERE / f"{name}.pdf")
    fig.savefig(HERE / f"{name}.png", dpi=170)
    plt.close(fig)


# ------------------------------------------------------------------ Figure 1: the map
fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.05))
for s, c in zip(SKILLS, BLUES):
    d = K1[(K1.skill == s) & (K1.regime == "FTG") & (K1.rf_pct == 1.0)].sort_values("r_pct")
    axes[0].plot(d.r_pct, d.p_pass, "-o", color=c, ms=3, label=NAME[s])
    axes[1].plot(d.r_pct, d.V, "-o", color=c, ms=3, label=NAME[s])
axes[0].set_ylabel("Probability of passing both steps")
axes[0].set_ylim(0, 1)
axes[1].set_yscale("log")
axes[1].set_ylim(0.4, 4000)
axes[1].yaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
axes[1].set_ylabel("Expected payouts per $10k (log scale)")
for fee in (40, 147):
    axes[1].axhline(fee, color=MUTED, lw=0.8, ls=(0, (4, 3)))
    axes[1].annotate(f"${fee} fee", (1.0, fee), xycoords=("axes fraction", "data"), xytext=(3, 0),
                     textcoords="offset points", ha="left", va="center", fontsize=7, color=MUTED, annotation_clip=False)
for ax in axes:
    ax.axvline(5, color=MUTED, lw=0.8, ls=":")
    ax.set_xlabel("Evaluation risk per trade (% of the account)")
    ax.set_xticks([0.5, 1, 2, 3, 4, 5, 6, 8])
    ax.xaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"{v:g}"))
axes[0].annotate("5% daily limit", (5, 0.97), xytext=(3, 0), textcoords="offset points", fontsize=7, color=MUTED, va="top")
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=5, title="Buyer's net Sharpe ratio", fontsize=7.5, title_fontsize=7.5,
           columnspacing=1.6, handlelength=1.8)
fig.tight_layout(rect=(0, 0.12, 1, 1), w_pad=1.6)
save(fig, "fig_map")

# ------------------------------------------------------------------ Figure 2: fee against the no-skill value
fees, code = {int(k): v for k, v in H["fees"]["list"].items()}, {int(k): v for k, v in H["fees"]["code"].items()}
v_ftg, v_std = H["hyp"]["FTG"]["coin"]["mean"] / 100, H["hyp"]["STD"]["coin"]["mean"] / 100      # % of the account
fig, ax = plt.subplots(figsize=(6.5, 2.9))
x = np.arange(len(fees))
lst = np.array([f / a * 100 for a, f in fees.items()])
cod = np.array([code[a] / a * 100 for a in fees])
ax.vlines(x, cod, lst, color=GRID, lw=2.2, zorder=1)
ax.plot(x, lst, "o", color=C1, ms=6.5, label="List fee", zorder=3)
ax.plot(x, cod, "o", color=C2, ms=6.5, label="Fee with the best code found on 13 October 2026", zorder=3)
v_slip = SLIP[(SLIP.slip == 0.10) & (SLIP.r_pct == 3.5)]["V_FTG_1.0"].iloc[0] / 100   # stops slipping 10% of their distance
ax.axhspan(v_slip, v_ftg, color=BLUES[0], alpha=0.28, lw=0, zorder=0)
ax.annotate(f"with stops slipping 10% ({v_slip:.2f}%)", (len(fees) - 0.45, v_slip),
            xytext=(0, 2), textcoords="offset points", ha="right", va="bottom", fontsize=7, color=MUTED)
for i, (xi, a, b) in enumerate(zip(x, lst, cod)):
    for val in (a, b):
        left = i == 1 and val == a                          # this label would sit on the standard-regime line
        ax.annotate(f"{val:.2f}%", (xi, val), xytext=(-7 if left else 7, 0), textcoords="offset points",
                    ha="right" if left else "left", va="center", fontsize=7, bbox=dict(fc="white", ec="none", pad=0.8), zorder=4)
for val, ls, text in ((v_ftg, "-", f"No-skill value, restricted regime ({v_ftg:.2f}%)"),
                      (v_std, (0, (4, 3)), f"No-skill value, standard regime ({v_std:.2f}%)")):
    ax.axhline(val, color=INK, lw=0.9, ls=ls, zorder=2)
    ax.annotate(text, (len(fees) - 0.45, val), xytext=(0, 3), textcoords="offset points", ha="right", va="bottom", fontsize=7)
ax.set_xticks(x, [f"${a // 1000}k" for a in fees])
ax.set_xlim(-0.5, len(fees) - 0.4)
ax.set_ylim(0, 1.75)
ax.set_xlabel("Account size")
ax.set_ylabel("% of the account")
ax.grid(axis="x", visible=False)
ax.legend(loc="lower left", fontsize=7.5, handletextpad=0.4)
fig.tight_layout()
save(fig, "fig_fee")

# ------------------------------------------------------------------ Figure 3: skill
fig, axes = plt.subplots(1, 2, figsize=(6.5, 2.95), gridspec_kw={"width_ratios": [1.25, 1]})
ax = axes[0]
for regime, c, name in (("FTG", C1, "Restricted regime"), ("STD", C2, "Standard regime")):
    f = H["frontier"][regime]
    ax.plot(f["S"], f["V"], "-o", color=c, ms=3.5, label=name)
ax.set_yscale("log")
ax.set_ylim(30, 5000)
ax.set_yticks([40, 100, 147, 300, 1000, 3000])
ax.yaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
ax.yaxis.set_minor_formatter(mt.NullFormatter())
for fee in (40, 147):
    ax.axhline(fee, color=MUTED, lw=0.8, ls=(0, (4, 3)))
    ax.annotate(f"${fee} fee", (2.0, fee), xytext=(0, 2), textcoords="offset points", ha="right", va="bottom", fontsize=7,
                color=MUTED)
ax.annotate("coin flip", (H["frontier"]["FTG"]["S"][0], H["frontier"]["FTG"]["V"][0]), xytext=(2, -11),
            textcoords="offset points", fontsize=7, color=MUTED)
ax.set_xlabel("Buyer's net Sharpe ratio")
ax.set_ylabel("Expected payouts per $10k purchase (log scale)")
ax.legend(loc="upper left", fontsize=7.5)
ax.set_title("(a) Value at the best sizing, 36 months", loc="left")
ax = axes[1]
coin, conv, s03 = cell("coin", "FTG"), cell("coin", "FTG", 1.0, 1.0), cell("0.3", "FTG")
hz = pd.DataFrame([{"months": m, "sizing": coin[c] - conv[c], "skill": s03[c] - coin[c]}
                   for m, c in ((12, "V12"), (24, "V24"), (36, "V"))])
for clock, ls, tag in (("none", "-", "no time limit"), ("classic 30/60", (0, (4, 2)), "30/60-day limits")):
    d = K5D[K5D.clock == clock].sort_values("months")
    ax.plot(d.months, d.sizing_gain, "o", ls=ls, color=C1, ms=3.5, label=f"Sizing, {tag}")
    ax.plot(d.months, d.skill_gain, "o", ls=ls, color=C2, ms=3.5, label=f"Sharpe of 0.3, {tag}")
ax.set_xticks([12, 24, 36, 60])
ax.set_xlabel("Value window (months from purchase)")
ax.set_ylabel("Gain in expected payouts")
ax.yaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
ax.set_ylim(0, 320)
ax.legend(loc="upper left", fontsize=6.8, handlelength=2.2)
ax.set_title("(b) Sizing against skill by window", loc="left")
fig.tight_layout(w_pad=1.4)
save(fig, "fig_skill")

# ------------------------------------------------------------------ Figure 4: the 24 tests
t = X1.sort_values("sharpe").reset_index(drop=True)
star = H["frontier"]["FTG"]["be_147"]
fig, ax = plt.subplots(figsize=(6.5, 4.5))
y = np.arange(len(t))
ax.hlines(y, t.lower, t.upper, color=BLUES[1], lw=1.4)
post = t.test == "M1r"
ax.plot(t.sharpe[~post], y[~post], "o", color=BLUES[3], ms=4.5)
ax.plot(t.sharpe[post], y[post], "o", mfc="white", mec=BLUES[3], mew=1.3, ms=4.5)
star_txt = f"{star:.2f}".replace("-", "−")
for val, text, ha in ((star, f"break-even at the\n$10k list fee ({star_txt})", "right"),
                      (0.3, "0.3", "center"), (0.5, "0.5", "center")):
    ax.axvline(val, color=MUTED, lw=0.8, ls=(0, (4, 3)))
    ax.annotate(text, (val, len(t) - 0.3), xytext=(-3 if ha == "right" else 3, 2), textcoords="offset points",
                ha="right" if ha == "right" else "left", va="bottom", fontsize=7, color=MUTED)
ax.set_yticks(y, [f"{a}  {b}" for a, b in zip(t.test, t.idea)], fontsize=7)
ax.set_ylim(-0.7, len(t) + 1.3)
ax.set_xlim(-1.85, 1.45)
ax.xaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"{v:g}".replace("-", "−")))
ax.set_xlabel("Annualised net Sharpe ratio (point estimate and 90% interval)")
ax.grid(axis="y", visible=False)
ax.tick_params(axis="y", length=0, colors=INK)
fig.tight_layout()
save(fig, "fig_tests")

# ------------------------------------------------------------------ tables
def write(name, body):
    (HERE / f"{name}.tex").write_text(body + "\n", encoding="utf-8", newline="\n")


rows = []
for s in ALL:
    a, b = cell(s, "FTG"), cell(s, "STD")
    rows.append(f"{NAME[s]} & {P[s]['net_sharpe']:.2f} & {P[s]['p'] * 100:.1f} & {a.r_pct:g} & {a.p_pass:.3f} & {a.p_payout:.3f} & "
                f"{a.V:,.0f} & {b.r_pct:g} & {b.rf_pct:g} & {b.p_pass:.3f} & {b.p_payout:.3f} & {b.V:,.0f}\\\\")
write("tab_policy", "\n".join(rows).replace("-0.21", "$-$0.21"))

d = K1[(K1.skill == "coin") & (K1.regime == "FTG") & (K1.rf_pct == 1.0)].sort_values("r_pct")
sd = P["coin"]["sd_R"]
write("tab_coin", "\n".join(
    f"{r.r_pct:g} & {r.r_pct * sd:.2f} & {r.p_step1:.3f} & {r.p_pass:.3f} & "
    f"{'--' if np.isnan(r.months_p50) else f'{r.months_p50:.1f}'} & {r.ev_static:.3f} & {r.ev_daily:.3f} & {r.ev_timeout:.3f} & "
    f"{r.p_payout:.3f} & {r.V:,.0f}\\\\" for r in d.itertuples()))

v10 = H["hyp"]["FTG"]["coin"]["mean"]
rows = []
for a, f in fees.items():
    c = code[a]
    ev_l, ev_c = (v10 - f / a * 1e4) * a / 1e4, (v10 - c / a * 1e4) * a / 1e4
    q = 1 - (c / a * 1e4) / v10
    rows.append(f"\\${a:,} & {f:,.0f} & {f / a * 100:.2f} & {money(ev_l)} & {c:,.2f} & {c / a * 100:.2f} & {money(ev_c)} & "
                f"{'--' if q <= 0 else f'{q * 100:.0f}'}\\\\")
write("tab_fee", "\n".join(rows))

ORDER = [("c one step", "Step 2 (one step only)"), ("n step maturities 30/60", "\\emph{Added:} step maturities of 30 and 60 days"),
         ("o no trading costs", "Trading costs"), ("l 100% split (arithmetic)", "The firm's 20\\% share"),
         ("m fee refund at $147 (arithmetic)", "No fee refund (refund of \\$147 with the first payout)"),
         ("h no Best Day Rule", "Best Day Rule"), ("b floors at the close only", "Intraday monitoring of the floors"),
         ("j payout checks every 21 days", "\\emph{Instead of on demand:} payout checks every 21 days"),
         ("f no funded lot or position caps", "Funded lot and position caps"), ("k no payout lock", "Two-day payout lock"),
         ("i no 2% minimum", "2\\% minimum profit"), ("d no minimum days", "Three-day minimum"),
         ("a no daily floor", "Daily floor"), ("g no Max Risk Rule", "Max Risk Rule"),
         ("e no evaluation leverage cap", "Evaluation leverage cap"),
         ("bare contract (a, b, d-k, o)", "All frictions together (two steps kept)")]


def rule_table(regime):
    out = []
    base = {s: K2[(K2.skill == s) & (K2.regime == regime) & (K2.variant == "baseline")].iloc[0] for s in ("coin", "0.3", "1.0")}
    out.append("Baseline value & " + " & ".join(f"{base[s].V:,.0f}" for s in ("coin", "0.3", "1.0")) + "\\\\\\midrule")
    for key, label in ORDER:
        vals = []
        for s in ("coin", "0.3", "1.0"):
            r = K2[(K2.skill == s) & (K2.regime == regime) & (K2.variant == key)].iloc[0]
            vals.append(f"{'+' if r.dV >= 0.5 else ''}{r.dV:,.0f}".replace("-", "$-$") if abs(r.dV) >= 0.5 else "0")
        out.append(f"{label} & " + " & ".join(vals) + "\\\\" + ("\\midrule" if key.startswith("bare") is False and key == ORDER[-2][0] else ""))
    return "\n".join(out)


write("tab_rules", rule_table("FTG"))
write("tab_rules_std", rule_table("STD"))

t3 = LIM[LIM.table == "Lim T3 funded"].reset_index(drop=True)
rows = []
for i, r in REAL.iterrows():
    rows.append(f"{r.S:g} & {r.vol_pct:g} & {r.lim_normal:.3f} & {t3.ours[i]:.3f} & {r.r_pct:.2f} & {r.real_close:.3f} & "
                f"{r.real_intraday:.3f}\\\\")
write("tab_lim", "\n".join(rows))

hy = H["hyp"]


def hrow(label, d, ci_=False):
    def f(k):
        x = d[k]
        s = money(x["mean"])
        return s + (f" ({money(x['lo'])} to {money(x['hi'])})" if ci_ else "")
    return f"{label} & {f('coin')} & {f('conv')} & {f('s03')} & {f('D')}\\\\"


rb = H["robust"]
rows = [hrow("Primary (restricted regime)", hy["FTG"]), "\\midrule",
        hrow("1. Standard regime, its own selected policy", hy["STD"]),
        hrow("2. Block bootstrap of trading days", rb["2 block bootstrap (21 days)"]),
        hrow("3. Purchases February 2005 to February 2014", hy["FTG purchases 2005-02 to 2014-02"]),
        hrow("3. Purchases January 2017 to November 2021", hy["FTG purchases 2017-01 to 2021-11"]),
        hrow("4. Payout checks every 21 days", rb["4 payout checks every 21 days"]),
        hrow("5. 60-month window", rb["5 60-month window"]),
        hrow("6. Costs at 1.0 times the measured spread", rb["6 cost stress x1.0"]),
        hrow("6. Costs at 2.0 times the measured spread", rb["6 cost stress x2.0"])]
write("tab_hyp", "\n".join(rows))

VERD = {"REFUTED": "Refuted", "INCONCLUSIVE": "Inconclusive", "MATERIAL": "Above"}
scol = [c for c in X1.columns if c.startswith("at S*")][0]
rows = []
for _, r in X1.iterrows():
    line = (f"{r['test']} & {r['idea']} & {r['years']:.1f} & {r['sharpe']:.2f} & {r['lower']:.2f} to {r['upper']:.2f} & "
            f"{r['mde']:.2f} & {VERD[r[scol]]} & {VERD[r['at 0.3']]} & {VERD[r['at 0.5']]}")
    rows.append(line.replace("-0.", "$-$0.").replace("-1.", "$-$1.").replace("&P", "\\&P") + "\\\\")
write("tab_tests", "\n".join(rows))

# ------------------------------------------------------------------ number macros
f, fs = H["frontier"]["FTG"], H["frontier"]["STD"]
c = H["coin_funded"]
coin1 = cell("coin", "FTG", 1.0, 1.0)
s03c = cell("0.3", "FTG", 1.0, 1.0)
halfrf = cell("coin", "FTG", rf=0.5)
n0 = {
    "Vcoin": money(hy["FTG"]["coin"]["mean"]), "VcoinLo": money(hy["FTG"]["coin"]["lo"]), "VcoinHi": money(hy["FTG"]["coin"]["hi"]),
    "VcoinPct": f"{hy['FTG']['coin']['mean'] / 100:.2f}\\%", "VcoinStd": money(hy["STD"]["coin"]["mean"]),
    "VcoinStdLo": money(hy["STD"]["coin"]["lo"]), "VcoinStdHi": money(hy["STD"]["coin"]["hi"]),
    "VcoinStdPct": f"{hy['STD']['coin']['mean'] / 100:.2f}\\%", "Vconv": money(hy["FTG"]["conv"]["mean"]),
    "Vskill": money(hy["FTG"]["s03"]["mean"]), "VskillLo": money(hy["FTG"]["s03"]["lo"]), "VskillHi": money(hy["FTG"]["s03"]["hi"]),
    "VskillConv": money(s03c.V), "VskillStd": money(hy["STD"]["s03"]["mean"]),
    "SizingGain": money(hy["FTG"]["sizing"]["mean"]), "SkillGain": money(hy["FTG"]["skill"]["mean"]),
    "Dval": money(hy["FTG"]["D"]["mean"]), "DvalLo": money(hy["FTG"]["D"]["lo"]), "DvalHi": money(hy["FTG"]["D"]["hi"]),
    "Ppass": f"{c['p_pass'] * 100:.1f}\\%", "Ppaid": f"{c['p_paid'] * 100:.1f}\\%", "PpassExact": f"{c['p_pass']:.3f}",
    "PpaidExact": f"{c['p_paid']:.3f}", "VperFunded": money(c["v_per_funded"]), "ShareFundedPaid": f"{c['share_funded_paid'] * 100:.0f}\\%",
    "PaidMedian": money(c["paid_median"]), "PaidPninetyfive": money(c["paid_p95"]),
    "EVpromo": money(hy["FTG"]["coin"]["mean"] - 40), "EVlist": money(hy["FTG"]["coin"]["mean"] - 147),
    "BEsharpeList": f"{f['be_147']:.2f}".replace("-", "$-$"), "SkillEqSizing": f"{f['skill_eq_sizing']:.2f}",
    "SkillEqPromo": f"{f['skill_eq_promo']:.2f}", "CoinSharpe": f"{P['coin']['net_sharpe']:.2f}".replace("-", "$-$"),
    "CoinCost": f"{-P['coin']['mean_R']:.4f}", "CoinSd": f"{P['coin']['sd_R']:.2f}", "HitThree": f"{P['0.3']['p'] * 100:.1f}\\%",
    "HitOne": f"{P['1.0']['p'] * 100:.1f}\\%", "HitTwo": f"{P['2.0']['p'] * 100:.1f}\\%", "HitZero": f"{P['0.0']['p'] * 100:.1f}\\%",
    "TradeDays": f"{H['trade_days']:,}", "Lam": f"{H['lam']:.2f}", "Vmedian": f"{H['v_median'] * 100:.2f}\\%",
    "CapStd": f"{H['lam'] * H['v_median'] * 100:.1f}\\%", "Pref": f"{H['p_ref']:,.0f}",
    "VcoinOnePct": money(coin1.V), "PpassOnePct": f"{coin1.p_pass * 100:.0f}\\%", "VcoinHalfRf": money(halfrf.V),
    "VskillOne": money(cell("1.0", "FTG").V), "VskillTwo": money(cell("2.0", "FTG").V),
    "Npaths": f"{H['n_paths']:,}", "MdeMedian": f"{X1.mde.median():.2f}",
    "RefutedThree": str((X1["at 0.3"] == "REFUTED").sum()), "RefutedFive": str((X1["at 0.5"] == "REFUTED").sum()),
    "DenialPromo": f"{(1 - 40 / hy['FTG']['coin']['mean']) * 100:.0f}\\%",
}
write("numbers", "\n".join(f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in n0.items()))
print(f"wrote 4 figures, 8 tables and {len(n0)} macros to {HERE}")
print(hz.round(1).to_string(index=False))


# =================================================================== amendments 1-5: K5 to K9
SIZES = [5_000, 10_000, 25_000, 50_000, 100_000, 200_000]
PLAN_ORDER = ["Pro 8%", "Pro 10%", "Pro 10% bi-weekly", "Pro 6%", "Direct", "Swing", "One 12%", "One 10%", "One 6%"]
STRUCT = {"Swing": "10\\%, then 5\\%; 10\\% static", "Pro 10%": "10\\%, then 5\\%; 10\\% static",
          "Pro 10% bi-weekly": "as Pro 10\\%, paid every two weeks", "Pro 8%": "8\\%, then 5\\%; 8\\% static",
          "Pro 6%": "6\\%, then 6\\%; 6\\% static", "One 6%": "6\\%; 4\\% trailing", "One 10%": "10\\%; 6\\% trailing",
          "One 12%": "12\\%; 8\\% trailing", "Direct": "no evaluation; 5\\% trailing"}
FEE_KEY = {"Swing": ("Swing", "on_demand"), "Pro 10%": ("Alpha Pro 10%", "on_demand"), "Pro 10% bi-weekly": ("Alpha Pro 10%", "bi_weekly"),
           "Pro 8%": ("Alpha Pro 8%", "on_demand"), "Pro 6%": ("Alpha Pro 6%", "on_demand"), "One 6%": ("Alpha One 6%", "on_demand"),
           "One 10%": ("Alpha One 10%", "on_demand"), "One 12%": ("Alpha One 12%", "on_demand"), "Direct": ("Alpha Direct", "on_demand")}


def plan_fees(plan):
    prefix, key = FEE_KEY[plan]
    return next(v[key] for k, v in FEES.items() if k.startswith(prefix))


def k8(plan, regime="FTG", skill="coin", mr=0.03):
    g = "STD" if plan == "Direct" else regime
    return K8[(K8.plan == plan) & (K8.regime == g) & (K8.skill == skill) & (K8.max_risk == mr)].iloc[0]


def tex(s):
    return s.replace("%", "\\%")


def neg(x, fmt="{:,.0f}"):
    return ("$-$" if x < 0 else "") + fmt.format(abs(x))


# ------------------------------------------------------------------ Figure: the plan menu
PF = EXT["K8"]["per_fee"]
order = sorted(PLAN_ORDER, key=lambda p: PF[p]["mean"])
fig, ax = plt.subplots(figsize=(6.5, 3.1))
y = np.arange(len(order))
ax.axvline(1.0, color=INK, lw=0.9)
ax.annotate("fee = value", (1.0, len(order) - 0.45), xytext=(3, 0), textcoords="offset points", fontsize=7, va="center")
for yi, p in zip(y, order):
    f10 = plan_fees(p)[1]
    std = k8(p, "STD").V / f10
    ax.hlines(yi, min(PF[p]["mean"], std), max(PF[p]["mean"], std), color=GRID, lw=2.2, zorder=1)
    if p != "Direct":
        ax.plot(std, yi, "o", mfc="white", mec=C1, mew=1.3, ms=5.5, zorder=3)
    ax.plot(PF[p]["mean"], yi, "o", color=C1, ms=6, zorder=4)
    ax.annotate(f"${PF[p]['mean']:.2f}", (PF[p]["mean"], yi), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=7)
ax.plot([], [], "o", color=C1, ms=6, label="Restricted regime")
ax.plot([], [], "o", mfc="white", mec=C1, mew=1.3, ms=5.5, label="Standard regime")
ax.set_yticks(y, [f"{p} (${plan_fees(p)[1]})" for p in order])
ax.tick_params(axis="y", length=0, colors=INK)
ax.set_ylim(-0.6, len(order) - 0.1)
ax.set_xlim(0, 2.25)
ax.xaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"${v:.2f}"))
ax.set_xlabel(r"Expected payouts per \$1 of list fee, no-skill buyer, \$10k account")
ax.grid(axis="y", visible=False)
ax.legend(loc="lower right", fontsize=7.5, handletextpad=0.3)
fig.tight_layout()
save(fig, "fig_menu")

# ------------------------------------------------------------------ Figure: the best policy
fig, ax = plt.subplots(figsize=(6.5, 2.8))
for col, c, name in (("coin", C2, "No skill (coin flip)"), ("0.3", BLUES[1], "Sharpe 0.3"), ("1.0", BLUES[4], "Sharpe 1.0")):
    ax.step(POLICY.balance, POLICY[col], where="mid", color=c, lw=1.3, label=name)
ax.axvline(10_000, color=MUTED, lw=0.8, ls=":")
ax.annotate("purchase", (10_000, 8.3), xytext=(3, 0), textcoords="offset points", fontsize=7, color=MUTED, va="top")
ax.annotate("floor", (9_000, 8.3), xytext=(3, 0), textcoords="offset points", fontsize=7, color=MUTED, va="top")
ax.annotate("target", (11_000, 8.3), xytext=(-3, 0), textcoords="offset points", fontsize=7, color=MUTED, va="top", ha="right")
ax.set_xlim(9_000, 11_000)
ax.set_ylim(0, 8.6)
ax.xaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
ax.yaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"{v:g}%"))
ax.set_xlabel("Account balance in step 1, on the day of purchase")
ax.set_ylabel("Risk on the next trade")
ax.legend(loc="upper center", ncol=3, fontsize=7.5, bbox_to_anchor=(0.5, 1.16))
fig.tight_layout()
save(fig, "fig_policy")

# ------------------------------------------------------------------ tables
rows = []
for p in PLAN_ORDER:
    a, b, s3 = k8(p), k8(p, "STD"), k8(p, skill="0.3")
    f10 = plan_fees(p)[1]
    rows.append(f"{tex(p)} & {STRUCT[p]} & {f10} & {'--' if p == 'Direct' else f'{a.p_pass:.3f}'} & {a.p_payout:.3f} & {a.V:,.0f} & "
                f"{'--' if p == 'Direct' else f'{b.V:,.0f}'} & {neg(a.V - f10)} & {PF[p]['mean']:.2f} & {s3.V:,.0f}\\\\")
write("tab_menu", "\n".join(rows))

rows = []
for p in [q for q in PLAN_ORDER if q != "Pro 10% bi-weekly"]:
    v = k8(p).V
    cells_ = ["--" if f is None else neg(v * a / 1e4 - f) for a, f in zip(SIZES, plan_fees(p))]
    rows.append(f"{tex(p)} & {v / 100:.2f} & " + " & ".join(cells_) + "\\\\")
write("tab_menu_sizes", "\n".join(rows))

us = cell("coin", "FTG")
books = [("NAS100", K6[K6.book == "NAS100_USD"].iloc[0]), ("US500 (the base case)", None), ("EUR/USD", K6[K6.book == "EUR_USD"].iloc[0]),
         ("USD/JPY", K6[K6.book == "USD_JPY"].iloc[0])]
rows = []
for name, r in books:
    if r is None:
        free = K2[(K2.skill == "coin") & (K2.regime == "FTG") & (K2.variant == "o no trading costs")].V.iloc[0]
        rows.append(f"{name} & {neg(P['coin']['mean_R'], '{:.4f}')} & {neg(P['coin']['net_sharpe'], '{:.2f}')} & {us.r_pct:g} & {us.p_pass:.3f} & "
                    f"{us.V:,.0f} ({us.V_lo:,.0f} to {us.V_hi:,.0f}) & {cell('coin', 'FTG', 1.0, 1.0).V:,.0f} & {cell('0.3', 'FTG').V:,.0f} & {free:,.0f}\\\\")
    else:
        rows.append(f"{name} & {neg(r.cost_R, '{:.4f}')} & {neg(r.net_sharpe_coin, '{:.2f}')} & {r.r_pct:g} & {r.p_pass:.3f} & "
                    f"{r.V_coin:,.0f} ({r.V_lo:,.0f} to {r.V_hi:,.0f}) & {r['V_coin_1%/1%']:,.0f} & {r['V_S0.3']:,.0f} & {r.V_coin_no_costs:,.0f}\\\\")
write("tab_books", "\n".join(rows))

rows = []
for clock, label in (("none", "None"), ("classic 30/60", "30 and 60 days")):
    for mo in (12, 24, 36, 60):
        g = K5[(K5.clock == clock) & (K5.months == mo)].set_index("skill")
        d = EXT["K5"]["D"][f"{clock}|{mo}"]
        rows.append(f"{label if mo == 12 else ''} & {mo} & {g.loc['coin'].V:,.0f} ({g.loc['coin'].r_pct:g}\\%) & {g.loc['coin'].V_conv:,.0f} & "
                    f"{g.loc['coin'].still_in_evaluation_conv * 100:.0f}\\% & {g.loc['0.3'].V:,.0f} & {g.loc['1.0'].V:,.0f} & "
                    f"{g.loc['1.0'].V_conv:,.0f} & {neg(d['mean'])} ({neg(d['lo'])} to {neg(d['hi'])})\\\\" + ("\\midrule" if (clock, mo) == ("none", 60) else ""))
write("tab_horizon", "\n".join(rows))

rows = []
for regime, label in (("FTG", "Restricted"), ("STD", "Standard")):
    for s in ("coin", "0.3", "1.0"):
        v = {c: K7[(K7.skill == s) & (K7.regime == regime) & (K7["class"] == c)].V.iloc[0] for c in "ABCD"}
        rows.append(f"{label if s == 'coin' else ''} & {NAME[s]} & {v['A']:,.0f} & {v['B']:,.0f} & {v['C']:,.0f} & {v['D']:,.0f} & "
                    f"+{(v['D'] / v['A'] - 1) * 100:.0f}\\%\\\\" + ("\\midrule" if (regime, s) == ("FTG", "1.0") else ""))
write("tab_classes", "\n".join(rows))

BOOKS9 = {"A1b": "A1b: pre-fix long-USD leg", "A2b": "A2b: month-end reversal", "M1r": "M1r: fade the macro surprise",
          "R3": "R3: A2b and M1r", "W3": "W3: all three"}
rows = []
for b, label in BOOKS9.items():
    for g in ("early", "late"):
        r = K9[(K9.book == b) & (K9.purchases == g)].iloc[0]
        mp = "--" if np.isnan(r.months_p50) else f"{r.months_p50:.1f}"
        rows.append(f"{label if g == 'early' else ''} & {g.capitalize()} & {r.net_sharpe:.2f} & {r.p_pass:.3f} & {mp} & {r.p_payout:.3f} & "
                    f"{r.V:,.0f} ({r.V_lo:,.0f} to {r.V_hi:,.0f}) & {r.V_ideal_same_sharpe:,.0f}\\\\" + ("\\addlinespace" if g == "late" and b != "W3" else ""))
write("tab_real", "\n".join(rows))

swing_fees = plan_fees("Swing")
rows = []
for s_ in (0.0, 0.05, 0.10, 0.25):
    r = SLIP[(SLIP.slip == s_) & (SLIP.r_pct == 3.5)].iloc[0]
    v = r["V_FTG_1.0"]
    first = next((f"\\${a // 1000}k" for a, f in zip(SIZES, swing_fees) if v * a / 1e4 > f), "no size")
    rows.append(f"{s_ * 100:.0f}\\% & {r.p_pass:.3f} & {v:,.0f} & {v / 100:.2f}\\% & {first}\\\\")
write("tab_slip", "\n".join(rows))

VTXT = {"SUPPORTED": "Supported", "REFUTED": "Refuted", "INCONCLUSIVE": "Inconclusive"}


def iv(d, pre="\\$"):
    return f"{neg(d['mean'], pre + '{:,.1f}')} ({neg(d['lo'], '{:,.1f}')} to {neg(d['hi'], '{:,.1f}')})"


e5, e7, e8, e9 = EXT["K5"], EXT["K7"], EXT["K8"], EXT["K9"]
hf = hy["FTG"]
k6v = {r.book: r for r in K6.itertuples()}
verd = [
    ("H1", "The no-skill value lies between the \\$40 promotional and \\$147 list fee", f"{iv(hf['coin'])}; \\$148 in the standard regime", "Supported, not robust"),
    ("H2", "Sizing is worth more than a Sharpe of 0.3 ($D>0$)", f"$D$ = {iv(hf['D'])}", "Refuted"),
    ("H3", "A Sharpe of 0.3 leaves the value below \\$147", iv(hf["s03"]), "Refuted"),
    ("H4", "Classic clock, 12-month window: $D>0$", iv(e5["H4"]), VTXT[e5["H4"]["verdict"]]),
    ("H5", "No clock, 60-month window: $D<0$", iv(e5["H5"]), VTXT[e5["H5"]["verdict"]]),
    ("H6", "Under each clock, $D$ falls as the window lengthens", "all six steps fall", VTXT[e5["H6_overall"]]),
    ("H7", "At every window, $D$ is larger with the clock", f"{iv(e5['H7']['12'])} at 12 months; larger at 24, 36, 60", VTXT[e5["H7_overall"]]),
    ("H8", "The no-skill value is \\$75 to \\$130 on three other instruments",
     f"\\${k6v['NAS100_USD'].V_coin:,.0f}, \\${k6v['EUR_USD'].V_coin:,.0f}, \\${k6v['USD_JPY'].V_coin:,.0f}", VTXT[EXT["K6"]["H8"]]),
    ("H9", "$D<0$ on all three", f"{neg(k6v['NAS100_USD'].D)}, {neg(k6v['EUR_USD'].D)}, {neg(k6v['USD_JPY'].D)}", VTXT[EXT["K6"]["H9"]]),
    ("H10", "The best policy beats the fixed one by more than 10\\% (no skill)", f"$V_D-1.10\\,V_A$ = {iv(e7['H10'])}", VTXT[e7["H10"]["verdict"]]),
    ("H11", "Average evaluation risk under the best policy falls with skill",
     "; ".join(f"{v:.2f}\\%" for v in e7["H11"]["levels"].values()), VTXT[e7["H11"]["verdict"]]),
    ("H12", "The solver's value is within 10\\% of the realised value", f"ratio {e7['H12']['ratio']:.3f} ({e7['H12']['lo']:.3f} to {e7['H12']['hi']:.3f})",
     VTXT[e7["H12"]["verdict"]]),
    ("H13", "Free payout timing adds under 2\\% without skill and over 5\\% at a Sharpe of 1.0 (standard regime)",
     f"{e7['gain']['coin|FTG|B'] * 100:.1f}\\% and {e7['gain']['1.0|STD|B'] * 100:.1f}\\%", VTXT[e7["H13"]["verdict"]]),
    ("H14", "Pro 10\\% is worth at least as much as Swing", iv(e8["H14"]), VTXT[e8["H14"]["verdict"]]),
    ("H15", "Pro 10\\% is worth more than its \\$77 fee", f"EV {iv(e8['H15'])}", VTXT[e8["H15"]["verdict"]]),
    ("H16", "Swing has the lowest value per fee dollar of the plans with an evaluation",
     f"Swing {PF['Swing']['mean']:.2f}; One plans {PF['One 6%']['mean']:.2f} to {PF['One 12%']['mean']:.2f}", VTXT[e8["H16"]["verdict"]]),
    ("H17", "One 10\\% is worth less than Pro 10\\%", iv(e8["H17"]), VTXT[e8["H17"]["verdict"]]),
    ("H18", "Direct is worth less than its \\$97 fee", f"EV {iv(e8['H18'])}", VTXT[e8["H18"]["verdict"]]),
    ("H19", "Every real book is worth less than an idealised buyer at the same Sharpe", "all five intervals below", VTXT[e9["H19"]]),
    ("H20", "The best real book is worth less than the no-skill buyer",
     f"\\${e9['H20']['V']:,.0f} (\\${e9['H20']['lo']:,.0f} to \\${e9['H20']['hi']:,.0f}) against \\${e9['H20']['coin']:,.0f}", VTXT[e9["H20"]["verdict"]]),
    ("H21", "Every real book is worth less on late purchases than on early ones", "clear for one book of five", VTXT[e9["H21"]]),
]
write("tab_verdicts", "\n".join(f"{a} & {b} & {c} & {d}\\\\" for a, b, c, d in verd))

# ------------------------------------------------------------------ number macros for K5-K9
g5 = lambda clock, mo, s: K5[(K5.clock == clock) & (K5.months == mo) & (K5.skill == s)].iloc[0]          # noqa: E731
conv_loss = {mo: 1 - g5("none", mo, "coin").V_conv / g5("none", mo, "coin").V for mo in (12, 24, 36, 60)}
k9 = lambda b, g: K9[(K9.book == b) & (K9.purchases == g)].iloc[0]                                      # noqa: E731
k7v = lambda s, g, c: K7[(K7.skill == s) & (K7.regime == g) & (K7["class"] == c)].iloc[0]               # noqa: E731
slip = lambda s_: SLIP[(SLIP.slip == s_) & (SLIP.r_pct == 3.5)]["V_FTG_1.0"].iloc[0]                     # noqa: E731
bon = lambda s: BONUS[(BONUS.skill == s) & (BONUS.regime == "FTG")]["bonus value $"].iloc[0]            # noqa: E731
pro10 = k8("Pro 10%")
n1 = {
    "DclockTwelve": iv(e5["H4"]), "DnoneSixty": neg(e5["H5"]["mean"], "\\${:,.0f}"),
    "VcoinClock": money(g5("classic 30/60", 36, "coin").V), "VcoinNoCutoff": money(g5("none", 36, "coin").V),
    "ClockCostCoin": f"{(1 - g5('classic 30/60', 36, 'coin').V / g5('none', 36, 'coin').V) * 100:.0f}\\%",
    "ClockCostThree": f"{(1 - g5('classic 30/60', 36, '0.3').V / g5('none', 36, '0.3').V) * 100:.0f}\\%",
    "ClockCostOne": f"{(1 - g5('classic 30/60', 36, '1.0').V / g5('none', 36, '1.0').V) * 100:.0f}\\%",
    "ForfeitTwelve": f"{conv_loss[12] * 100:.0f}\\%", "ForfeitTwentyFour": f"{conv_loss[24] * 100:.0f}\\%",
    "ForfeitThirtySix": f"{conv_loss[36] * 100:.0f}\\%", "ForfeitSixty": f"{conv_loss[60] * 100:.0f}\\%",
    "StillEvalTwelve": f"{g5('none', 12, 'coin').still_in_evaluation_conv * 100:.0f}\\%",
    "StillEvalThirtySix": f"{g5('none', 36, 'coin').still_in_evaluation_conv * 100:.0f}\\%",
    "CautiousOne": money(g5("none", 36, "1.0").V_conv), "CautiousMultiple": f"{g5('none', 36, '1.0').V_conv / g5('none', 36, 'coin').V:.1f}",
    "BookLo": f"{EXT['K6']['lo_pct']:.2f}\\%", "BookHi": f"{EXT['K6']['hi_pct']:.2f}\\%",
    "VNas": money(k6v["NAS100_USD"].V_coin), "VEur": money(k6v["EUR_USD"].V_coin), "VJpy": money(k6v["USD_JPY"].V_coin),
    "VbestCoin": money(k7v("coin", "FTG", "D").V), "GainBestCoin": f"{e7['gain']['coin|FTG|D'] * 100:.0f}\\%",
    "PpassBest": f"{k7v('coin', 'FTG', 'D').p_pass * 100:.1f}\\%", "PpaidBest": f"{k7v('coin', 'FTG', 'D').p_payout * 100:.1f}\\%",
    "VbestCoinPct": f"{k7v('coin', 'FTG', 'D').V / 100:.2f}\\%",
    "GainBestThree": f"{e7['gain']['0.3|FTG|D'] * 100:.0f}\\%", "GainBestOne": f"{e7['gain']['1.0|FTG|D'] * 100:.0f}\\%",
    "GainBestOneStd": f"{e7['gain']['1.0|STD|D'] * 100:.0f}\\%", "GainTimingOneStd": f"{e7['gain']['1.0|STD|B'] * 100:.0f}\\%",
    "ModelRatio": f"{e7['H12']['ratio']:.2f}", "EvalRiskCoin": f"{e7['H11']['levels']['coin']:.1f}\\%",
    "EvalRiskThree": f"{e7['H11']['levels']['0.3']:.1f}\\%", "EvalRiskOne": f"{e7['H11']['levels']['1.0']:.1f}\\%",
    "SpanMedian": f"{k7v('coin', 'FTG', 'D').size_span_median:.0f}", "SpanNinety": f"{k7v('coin', 'FTG', 'D').size_span_p90:.0f}",
    "PerFeeMin": f"\\${min(v['mean'] for v in PF.values()):.2f}", "PerFeeMax": f"\\${max(v['mean'] for v in PF.values()):.2f}",
    "PerFeeSwing": f"\\${PF['Swing']['mean']:.2f}", "PerFeeProTen": f"\\${PF['Pro 10%']['mean']:.2f}",
    "PerFeeProTenLarge": f"\\${pro10.V * 10 / plan_fees('Pro 10%')[4]:.2f}",
    "VProTen": money(pro10.V), "EVProTen": money(e8["H15"]["mean"]), "DiffProSwing": money(e8["H14"]["mean"]),
    "VProTenBi": money(k8("Pro 10% bi-weekly").V), "VDirect": money(k8("Direct").V), "PpaidDirect": f"{k8('Direct').p_payout * 100:.0f}\\%",
    "VOneTen": money(k8("One 10%").V), "DiffOnePro": money(-e8["H17"]["mean"]), "VProTenSkill": money(k8("Pro 10%", skill="0.3").V),
    "VOneSixSkill": money(k8("One 6%", skill="0.3").V),
    "VAoneLate": money(k9("A1b", "late").V), "VAoneLateLo": money(k9("A1b", "late").V_lo), "VAoneLateHi": money(k9("A1b", "late").V_hi),
    "VAoneEarly": money(k9("A1b", "early").V), "IdealAoneLate": money(k9("A1b", "late").V_ideal_same_sharpe),
    "VRthreeLate": money(k9("R3", "late").V), "IdealRthreeLate": money(k9("R3", "late").V_ideal_same_sharpe),
    "SharpeRthreeLate": f"{k9('R3', 'late').net_sharpe:.2f}", "VWthreeLate": money(k9("W3", "late").V),
    "CoinLate": money(e9["H20"]["coin"]),
    "VslipFive": money(slip(0.05)), "VslipTen": money(slip(0.10)), "VslipTwentyFive": money(slip(0.25)),
    "BonusCoin": money(bon("coin"), 2), "BonusOne": money(bon("1.0"), 2),
}
write("numbers_ext", "\n".join(f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in n1.items()))
print(f"wrote 2 more figures, 8 more tables and {len(n1)} more macros")
