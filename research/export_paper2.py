"""Copy the results of amendments 1-5 (K5-K9, the bonus and the stop-slippage check) into
paper/prop_contract/results and compute the numbers behind every hypothesis verdict. Run after
``research/run_K.py export``, from the repository root:

    python research/export_paper2.py
"""
import json
import re
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

OUT, LOGS, DST = Path("data/checks"), Path("data/logs"), Path("paper/prop_contract/results")
POL = Path("data/r2cache/K7_policies")


def ci(x):
    x = np.asarray(x, float)
    m, se = x.mean(), x.std(ddof=1) / np.sqrt(len(x))
    return {"mean": float(m), "lo": float(m - 1.96 * se), "hi": float(m + 1.96 * se)}


def verdict(d, positive=True):
    lo, hi = (d["lo"], d["hi"]) if positive else (-d["hi"], -d["lo"])
    return "SUPPORTED" if lo > 0 else "REFUTED" if hi < 0 else "INCONCLUSIVE"


def table_from_log(path: Path, header_starts: str) -> pd.DataFrame:
    """A whitespace table printed by pandas in a log: the header line starts with ``header_starts``."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    i = next(k for k, ln in enumerate(lines) if ln.strip().startswith(header_starts))
    rows = []
    for ln in lines[i + 1:]:
        parts = ln.split()
        try:
            rows.append([float(p) for p in parts])
        except ValueError:
            break
    return pd.DataFrame(rows)


def main():
    DST.mkdir(parents=True, exist_ok=True)
    for name in ("K5_horizon.csv", "K5_D.csv", "K6_books.csv", "K7_classes.csv", "K8_plans.csv", "K9_real_books.csv",
                 "K_bonus.csv"):
        shutil.copyfile(OUT / name, DST / name)
    shutil.copyfile("research/FEES_alpha_2026-10-13.json", DST / "FEES_alpha_2026-10-13.json")

    # ---- stop slippage and funded risk (exploratory), from their logs
    s = table_from_log(LOGS / "explore_slippage.log", "slip (share of stop)")
    s.columns = ["slip", "r_pct", "p_pass", "daily_breaches", "V_FTG_0.9", "V_FTG_1.0", "V_STD_2.0", "V_STD_2.5"]
    s.to_csv(DST / "K_slippage.csv", index=False)

    # ---- K7: the free policy's size by balance on the day of purchase (step 1, FTG)
    pol = {}
    for sk in ("coin", "0.3", "1.0"):
        z = np.load(POL / f"{sk}_FTG_D.npz")
        pol[sk] = z["eval_actions"][z["pol1"][0]] * 100
    bal = 9000 + 5.0 * np.arange(1, len(pol["coin"]) + 1)
    pd.DataFrame({"balance": bal, **pol}).to_csv(DST / "K7_policy_step1.csv", index=False)

    ext = {}
    # ---- K5
    d5 = pd.read_csv(OUT / "K5_D.csv")
    z5 = np.load(OUT / "K5_paths.npz")
    D = {(c, int(h)): z5[f"D|{c}|{h}"].astype(float) for c in ("none", "classic 30/60") for h in (12, 24, 36, 60)}
    ext["K5"] = {"D": {f"{c}|{h}": ci(x) for (c, h), x in D.items()},
                 "H4": {**ci(D[("classic 30/60", 12)]), "verdict": verdict(ci(D[("classic 30/60", 12)]))},
                 "H5": {**ci(D[("none", 60)]), "verdict": verdict(ci(D[("none", 60)]), positive=False)},
                 "H6": {f"{c}|{a}-{b}": {**ci(D[(c, a)] - D[(c, b)]), "verdict": verdict(ci(D[(c, a)] - D[(c, b)]))}
                        for c in ("none", "classic 30/60") for a, b in ((12, 24), (24, 36), (36, 60))},
                 "H7": {str(h): {**ci(D[("classic 30/60", h)] - D[("none", h)]),
                                 "verdict": verdict(ci(D[("classic 30/60", h)] - D[("none", h)]))} for h in (12, 24, 36, 60)}}
    for h in ("H6", "H7"):
        vs = [v["verdict"] for v in ext["K5"][h].values()]
        ext["K5"][h + "_overall"] = "SUPPORTED" if all(v == "SUPPORTED" for v in vs) else "REFUTED" if "REFUTED" in vs else "INCONCLUSIVE"
    assert np.allclose(d5.D.to_numpy(), [ext["K5"]["D"][f"{c}|{h}"]["mean"] for c, h in zip(d5.clock, d5.months)], atol=1e-3)

    # ---- K6
    k6 = pd.read_csv(OUT / "K6_books.csv")
    ext["K6"] = {"H8": "SUPPORTED" if (k6.H8 == "inside").all() else "REFUTED" if (k6.H8 == "outside").any() else "INCONCLUSIVE",
                 "H9": "SUPPORTED" if (k6.H9 == "SUPPORTED").all() else "REFUTED" if (k6.H9 == "REFUTED").any() else "INCONCLUSIVE",
                 "lo_pct": float(k6.V_coin.min() / 100), "hi_pct": float(k6.V_coin.max() / 100)}

    # ---- K7
    k7 = pd.read_csv(OUT / "K7_classes.csv", dtype={"skill": str})
    z7 = np.load(OUT / "K7_paths.npz")
    V7 = lambda s, g, c: z7[f"V|{s}|{g}|{c}"].astype(float)                # noqa: E731
    er = {s: z7[f"eval_risk|{s}|FTG|D"].astype(float) * 100 for s in ("coin", "0.3", "1.0")}
    row = k7[(k7.skill == "coin") & (k7.regime == "FTG") & (k7["class"] == "D")].iloc[0]
    h10 = ci(V7("coin", "FTG", "D") - 1.10 * V7("coin", "FTG", "A"))
    h11 = {"coin-0.3": ci(er["coin"] - er["0.3"]), "0.3-1.0": ci(er["0.3"] - er["1.0"])}
    h13a, h13b = ci(V7("coin", "FTG", "B") - 1.02 * V7("coin", "FTG", "A")), ci(V7("1.0", "STD", "B") - 1.05 * V7("1.0", "STD", "A"))
    ratio = [row.model_value / row.V, row.model_value / row.V_hi, row.model_value / row.V_lo]
    v11 = [verdict(v) for v in h11.values()]
    v13 = [verdict(h13a, positive=False), verdict(h13b)]
    ext["K7"] = {"gain": {f"{s}|{g}|{c}": float(V7(s, g, c).mean() / V7(s, g, "A").mean() - 1) for s in ("coin", "0.3", "1.0")
                          for g in ("FTG", "STD") for c in ("B", "C", "D")},
                 "H10": {**h10, "verdict": verdict(h10)},
                 "H11": {"levels": {s: float(v.mean()) for s, v in er.items()}, "steps": h11,
                         "verdict": "SUPPORTED" if all(v == "SUPPORTED" for v in v11) else "REFUTED" if "REFUTED" in v11 else "INCONCLUSIVE"},
                 "H12": {"ratio": ratio[0], "lo": ratio[1], "hi": ratio[2],
                         "verdict": "SUPPORTED" if ratio[1] >= 0.90 and ratio[2] <= 1.10 else "REFUTED" if ratio[2] < 0.90 or ratio[1] > 1.10 else "INCONCLUSIVE"},
                 "H13": {"coin": h13a, "skilled": h13b,
                         "verdict": "SUPPORTED" if v13 == ["SUPPORTED", "SUPPORTED"] else "REFUTED" if "REFUTED" in v13 else "INCONCLUSIVE"}}

    # ---- K8
    fees = json.loads(Path("research/FEES_alpha_2026-10-13.json").read_text(encoding="utf-8"))["plans"]
    fee10 = {"Swing": 147, "Pro 10%": 77, "Pro 10% bi-weekly": 87, "Pro 8%": 57, "Pro 6%": 47, "One 6%": 67, "One 10%": 87,
             "One 12%": 107, "Direct": 97}
    assert fee10["Swing"] == next(v["on_demand"][1] for k, v in fees.items() if k.startswith("Swing"))
    z8 = np.load(OUT / "K8_paths.npz")
    V8 = lambda p, g="FTG", s="coin": z8[f"{p}|{g}|0.03|{s}"].astype(float)   # noqa: E731
    per_fee = {p: {k: v / fee10[p] for k, v in ci(V8(p, "STD" if p == "Direct" else "FTG")).items()} for p in fee10}
    evaln = [p for p in fee10 if p not in ("Direct", "Pro 10% bi-weekly")]
    sw = per_fee["Swing"]
    below = [p for p in evaln if p != "Swing" and per_fee[p]["hi"] < sw["lo"]]
    above = [p for p in evaln if p != "Swing" and per_fee[p]["lo"] > sw["hi"]]
    h14, h15 = ci(V8("Pro 10%") - V8("Swing")), ci(V8("Pro 10%") - fee10["Pro 10%"])
    h17, h18 = ci(V8("One 10%") - V8("Pro 10%")), ci(V8("Direct", "STD") - fee10["Direct"])
    ext["K8"] = {"fee10": fee10, "per_fee": per_fee,
                 "H14": {**h14, "verdict": verdict(h14)}, "H15": {**h15, "verdict": verdict(h15)},
                 "H16": {"below_swing": below, "verdict": "REFUTED" if below else "SUPPORTED" if len(above) == len(evaln) - 1 else "INCONCLUSIVE"},
                 "H17": {**h17, "verdict": verdict(h17, positive=False)}, "H18": {**h18, "verdict": verdict(h18, positive=False)}}

    # ---- K9 (verdict lines as printed by the run)
    log = (LOGS / "run_K9.log").read_text(encoding="utf-8", errors="replace")
    ext["K9"] = {h: re.search(rf"{h} overall: (\w+)", log).group(1) for h in ("H19", "H21")}
    m = re.search(r"H20 best book (\w+): V \$([\d.]+) \[([\d.]+), ([\d.]+)\] against the coin flip's \$([\d.]+)\s+(\w+)", log)
    ext["K9"]["H20"] = {"book": m.group(1), "V": float(m.group(2)), "lo": float(m.group(3)), "hi": float(m.group(4)),
                        "coin": float(m.group(5)), "verdict": m.group(6)}
    ext["K9"]["H21_steps"] = {b: {"d": float(d), "lo": float(lo), "hi": float(hi), "verdict": v} for b, d, lo, hi, v in
                              re.findall(r"H21 (\w+): late minus early \$([+-][\d.]+) \[([+-][\d.]+), ([+-][\d.]+)\]\s+(\w+)", log)}
    (DST / "extensions.json").write_text(json.dumps(ext, indent=1), encoding="utf-8")
    print("exported to", DST)
    print(json.dumps({k: {h: (v["verdict"] if isinstance(v, dict) and "verdict" in v else v) for h, v in d.items() if h.startswith("H")}
                      for k, d in ext.items()}, indent=1))


if __name__ == "__main__":
    main()
