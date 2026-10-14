"""One command to reproduce "Fair on Paper: What a Prop-Firm Challenge Is Worth, and Who Pays for It".

    python reproduce.py                 every result, table, figure and the paper, from the shipped day series
    python reproduce.py --quick         the same pipeline on 5,000 paths: a check that it runs, not results
    python reproduce.py --only k1 k4    selected stages
    python reproduce.py --list          the stages, in order
    python reproduce.py --check         compare data/checks with results/reference (after a full run)

A full run takes about two and a quarter hours on one core and needs about 4 GB of memory. Each stage writes its
log to data/logs. Stages marked "network" fetch public pages and are skipped unless asked for by name.
"""
import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable
STAGES = [  # name, command, log, note
    ("tests", [PY, "-m", "pytest", "tests", "-q"], "tests.log", "unit tests, including the path-by-path check against the older simulator"),
    ("book", [PY, "research/validate_book.py"], "validate_book.log", "rebuild the day series from raw bars, if data/raw holds them"),
    ("gates", [PY, "research/run_K.py", "gates"], "run_K_gates.log", "gate: the simulator against the older one on 2,000+ real-book cases"),
    ("k1", [PY, "research/run_K.py", "k1"], "run_K_k1.log", "the skill x sizing map, H1-H3 (about 40 minutes)"),
    ("k2", [PY, "research/run_K.py", "k2"], "run_K_k2.log", "one rule removed at a time"),
    ("k3", [PY, "research/run_K.py", "k3"], "run_K_k3.log", "bridge to Lim's model"),
    ("robust", [PY, "research/run_K.py", "robust"], "run_K_robust.log", "robustness rows"),
    ("k4", [PY, "research/run_K.py", "k4"], "run_K_k4.log", "fee and break-evens"),
    ("x1", [PY, "research/run_K.py", "x1"], "run_K_x1.log", "claim-exclusion table for the 24 tests"),
    ("explore", [PY, "research/run_K.py", "explore"], "run_K_explore.log", "exploratory checks"),
    ("bonus", [PY, "research/info_K_bonus.py"], "info_K_bonus.log", "the fourth-payout bonus"),
    ("slippage", [PY, "research/info_K_slippage.py"], "explore_slippage.log", "stop slippage (exploratory)"),
    ("funded_risk", [PY, "research/info_K_funded_risk.py"], "explore_funded_risk.log", "funded risk (exploratory)"),
    ("k5", [PY, "research/run_K_ext.py", "k5"], "run_K_ext_k5.log", "horizon grid, H4-H7"),
    ("k6", [PY, "research/run_K_ext.py", "k6"], "run_K_ext_k6.log", "other instruments, H8-H9"),
    ("k7gates", [PY, "research/run_K7.py", "gates"], "run_K7_gates.log", "gates for the policy solver"),
    ("k7", [PY, "research/run_K7.py", "solve"], "run_K7_solve.log", "the buyer's best policy"),
    ("k7report", [PY, "research/run_K7.py", "report"], "run_K7_report.log", "H10-H13"),
    ("k8", [PY, "research/run_K8.py", "run"], "run_K8.log", "the plan menu (about 40 minutes)"),
    ("k8report", [PY, "research/run_K8.py", "report"], "run_K8_report.log", "H14-H18"),
    ("k9", [PY, "research/run_K9.py"], "run_K9.log", "real strategies through the contract, H19-H21"),
    ("lim", [PY, "research/validate_lim.py"], "validate_lim.log", "independent re-implementation of Lim (2026)"),
    ("export", [PY, "research/run_K.py", "export"], "run_K_export.log", "copy results into paper/prop_contract/results"),
    ("export2", [PY, "research/export_paper2.py"], "export_paper2.log", "the extension results and every hypothesis number"),
    ("exhibits", [PY, "paper/prop_contract/make_exhibits.py"], "make_exhibits.log", "figures, tables and number macros"),
    ("pdf", None, "pdflatex.log", "compile the paper (needs pdflatex)"),
    ("rules", [PY, "research/validate_rules.py"], "validate_rules.log", "network: re-check the quoted rule text against the firm's live pages"),
    ("citations", [PY, "research/validate_citations.py"], "validate_citations.log", "network: look every reference up in Crossref and arXiv"),
]
NETWORK = {"rules", "citations"}
PAPER = {"export", "export2", "exhibits", "pdf"}
REFERENCE = ["K1_map.csv", "K2_rules.csv", "K3_lim_replication.csv", "K3_real_through_lim.csv", "K3_normal_through_alpha.csv",
             "K_robustness.csv", "X1_claim_exclusion.csv", "K5_horizon.csv", "K5_D.csv", "K6_books.csv", "K7_classes.csv",
             "K8_plans.csv", "K9_real_books.csv", "K_bonus.csv", "V1_lim_cells.csv"]


def pdf(log: Path) -> int:
    if shutil.which("pdflatex") is None:
        log.write_text("pdflatex not found; skipped\n")
        print("    pdflatex not found; skipped")
        return 0
    code = 0
    with open(log, "w", encoding="utf-8") as fh:
        for _ in range(3):
            code = subprocess.call(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
                                   cwd=ROOT / "paper" / "prop_contract", stdout=fh, stderr=subprocess.STDOUT)
            if code:
                break
    return code


def check() -> int:
    import numpy as np
    import pandas as pd
    bad = 0
    for name in REFERENCE:
        a, b = ROOT / "data" / "checks" / name, ROOT / "results" / "reference" / name
        if not a.exists():
            print(f"  {name:32s} not regenerated yet")
            bad += 1
            continue
        x, y = pd.read_csv(a), pd.read_csv(b)
        if x.shape != y.shape or list(x.columns) != list(y.columns):
            print(f"  {name:32s} DIFFERENT SHAPE {x.shape} against {y.shape}")
            bad += 1
            continue
        num = x.select_dtypes("number").columns
        same_text = x.drop(columns=num).fillna("").astype(str).equals(y.drop(columns=num).fillna("").astype(str))
        d = np.nanmax(np.abs(x[num].to_numpy(float) - y[num].to_numpy(float)) / (1e-9 + np.abs(y[num].to_numpy(float)))) if len(num) else 0.0
        ok = same_text and (np.isnan(d) or d < 1e-6)
        bad += not ok
        print(f"  {name:32s} {'identical' if ok else 'DIFFERS'} (largest relative difference {d:.1e})")
    print("ALL TABLES REPRODUCED" if not bad else f"{bad} table(s) differ or are missing")
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only", nargs="+", metavar="STAGE")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.list:
        for name, _, _, note in STAGES:
            print(f"  {name:12s} {note}")
        return 0
    if a.check:
        return check()
    names = [s[0] for s in STAGES]
    skip = NETWORK | (PAPER if a.quick else set())      # a quick run must not overwrite the paper's results
    todo = a.only or [n for n in names if n not in skip]
    unknown = [n for n in todo if n not in names]
    if unknown:
        sys.exit(f"unknown stage(s): {unknown}; see --list")
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONIOENCODING="utf-8", MPLBACKEND="Agg")
    if a.quick:
        env["K_SMOKE"] = "5000"
        print("QUICK MODE: 5,000 paths. This checks that the pipeline runs; its numbers are not the paper's.")
        if not a.only:
            print("The export, exhibit and PDF stages are skipped so the paper's shipped results stay as they are.")
    (ROOT / "data" / "logs").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "checks").mkdir(parents=True, exist_ok=True)
    t_all = time.time()
    for name, cmd, log, note in STAGES:
        if name not in todo:
            continue
        t0 = time.time()
        print(f"[{name}] {note} ...", flush=True)
        path = ROOT / "data" / "logs" / log
        if cmd is None:
            code = pdf(path)
        else:
            with open(path, "w", encoding="utf-8") as fh:
                code = subprocess.call(cmd, cwd=ROOT, env=env, stdout=fh, stderr=subprocess.STDOUT)
        print(f"    {'ok' if code == 0 else 'FAILED'} in {time.time() - t0:.0f}s (log: data/logs/{log})", flush=True)
        if code:
            print(path.read_text(encoding="utf-8", errors="replace")[-1500:])
            return code
    print(f"done in {(time.time() - t_all) / 60:.0f} minutes")
    if not a.quick and not a.only:
        return check()
    return 0


if __name__ == "__main__":
    sys.exit(main())
