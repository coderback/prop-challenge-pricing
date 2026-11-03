"""Assemble demo/data/site-data.json from results/reference/*.csv and the paper's table sources.

Run from the repository root:  python demo/data/build_site_data.py
Nothing is estimated: CSV rows are copied (rounded) and LaTeX table rows are parsed as written.
"""
import json, re
from pathlib import Path
import pandas as pd

R = Path("results/reference"); P = Path("paper/prop_contract")
def clean(s):
    s = s.replace("\\\\", "").replace(r"\$", "$").replace("$-$", "−").replace(r"\%", "%").replace(r"\,", " ").replace("$D>0$", "D>0").replace("$D<0$", "D<0")
    s = re.sub(r"\$([^$]*)\$", r"\1", s) if s.count("$") % 2 == 0 and "$" in s and not re.search(r"\$\d", s) else s
    return s.replace("{", "").replace("}", "").strip()
def tex_rows(name):
    out = []
    for line in (P / name).read_text(encoding="utf8").splitlines():
        line = line.strip()
        if not line or line.startswith(r"\midrule") or line.startswith(r"\addlinespace"): continue
        out.append([clean(c) for c in line.rstrip("\\").split("&")])
    return out

k1 = pd.read_csv(R / "K1_map.csv")
k1 = k1[["skill", "regime", "r_pct", "rf_pct", "V", "V_lo", "V_hi", "p_pass", "p_payout", "selected"]]
map_rows = [[("0.3" if str(r.skill) == "0.3" else str(r.skill)), r.regime, float(r.r_pct), float(r.rf_pct), round(float(r.V), 2), round(float(r.V_lo), 2), round(float(r.V_hi), 2),
             round(float(r.p_pass), 4), round(float(r.p_payout), 4), bool(r.selected)] for r in k1.itertuples()]
k8 = pd.read_csv(R / "K8_plans.csv")
plans_rows = [{"plan": r.plan, "regime": r.regime, "skill": str(r.skill), "r": None if pd.isna(r.r_pct) else float(r.r_pct), "rf": None if pd.isna(r.rf_pct) else float(r.rf_pct),
               "p_pass": None if pd.isna(r.p_pass) else round(float(r.p_pass), 4), "p_payout": round(float(r.p_payout), 4), "V": round(float(r.V), 2), "V_lo": round(float(r.V_lo), 2), "V_hi": round(float(r.V_hi), 2)} for r in k8.itertuples()]
k5 = pd.read_csv(R / "K5_D.csv")
horizon = [{"clock": r.clock, "months": int(r.months), "sizing": round(float(r.sizing_gain), 2), "skill": round(float(r.skill_gain), 2), "D": round(float(r.D), 2), "D_lo": round(float(r.D_lo), 2), "D_hi": round(float(r.D_hi), 2)} for r in k5.itertuples()]
k9 = pd.read_csv(R / "K9_real_books.csv")
LAB = {"A1b": "Pre-fix long-USD leg", "A2b": "Month-end reversal", "M1r": "Fade the macro surprise", "R3": "A2b and M1r together", "W3": "All three together"}
books = [{"id": r.book, "label": LAB[r.book], "period": r.purchases, "n": int(r.n), "sharpe": round(float(r.net_sharpe), 3), "tpy": round(float(r.trades_per_year), 1), "p_pass": round(float(r.p_pass), 4), "p_payout": round(float(r.p_payout), 4),
          "V": round(float(r.V), 1), "V_lo": round(float(r.V_lo), 1), "V_hi": round(float(r.V_hi), 1), "ideal": round(float(r.V_ideal_same_sharpe), 1)} for r in k9.itertuples()]
k6 = pd.read_csv(R / "K6_books.csv")
instr = [{"book": r.book.replace("_", "/"), "V_coin": round(float(r.V_coin), 1), "V_lo": round(float(r.V_lo), 1), "V_hi": round(float(r.V_hi), 1)} for r in k6.itertuples()]
verdicts = [{"id": c[0], "claim": c[1], "found": c[2], "verdict": c[3]} for c in tex_rows("tab_verdicts.tex")]
sizes = {}
for c in tex_rows("tab_menu_sizes.tex"):
    sizes[c[0]] = {"pct": float(c[1]), "ev": [None if x in ("--", "") else int(x.replace(",", "").replace("−", "-")) for x in c[2:8]]}
menu = []
for c in tex_rows("tab_menu.tex"):
    num = lambda x: None if x in ("--", "") else float(x.replace("−", "-"))
    menu.append({"plan": c[0], "terms": c[1], "fee": num(c[2]), "p_pass": num(c[3]), "p_paid": num(c[4]), "V": num(c[5]), "V_std": num(c[6]), "EV": num(c[7]), "per_fee": num(c[8]), "V_s03": num(c[9])})
out = {"map": map_rows, "plans": plans_rows, "menu": menu, "sizes": sizes, "horizon": horizon, "books": books, "instruments": instr, "verdicts": verdicts}
Path("demo/data/site-data.json").write_text(json.dumps(out, separators=(",", ":"), ensure_ascii=False), encoding="utf8")
print("ok", len(json.dumps(out)) // 1024, "KB;", len(map_rows), "map rows;", len(verdicts), "verdicts;", len(menu), "menu")
for m in menu: print(m)
print(sizes); print(verdicts[0], verdicts[-1])
