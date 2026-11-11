"""Sensitivity & Ablation Study (theta x slopeGatePct x raw_onset_delay) on 40 PTs x 12 scenarios = 480 trials."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "system" / "backend"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_DIR))

from app.config.topology import build_topology
from app.engine.drift_forecast import EngineParams, evaluate_window
from experiments.run_full_experiments import SCENARIOS, generate_scenario_series


def main():
    _, _, sensors = build_topology()
    pt_sensors = [s for s in sensors if s.measurement_type == "PRESSURE"][:40]

    grid = []
    for theta in (1.5, 1.8, 2.0, 2.5):
        for gate_pct in (2.5, 5.0, 10.0):
            for raw_onset in (1, 2):
                tp = fp = fn = tn = 0
                leads = []
                for sdef in pt_sensors:
                    lim = sdef.limits
                    for idx, (scen, is_fault, mag) in enumerate(SCENARIOS, 1):
                        seed = 2026111199 + hash((sdef.tag_id, idx)) % 100000
                        hist, ser = generate_scenario_series(lim, scen, mag, seed)
                        breach = next((i for i, pt in enumerate(ser) if i >= 10 and pt.good and (pt.v >= lim.high or pt.v <= lim.low)), None)
                        win = list(hist)
                        streak = 0
                        first_trig = None
                        for i, pt in enumerate(ser):
                            win.append(pt)
                            raw = evaluate_window(sdef.tag_id, win[-70:], pt.v, lim, EngineParams(theta, gate_pct), f"t{i}")
                            if raw.state == "EVENT":
                                streak = raw_onset
                            elif raw.state in ("T-30", "T-20", "T-10"):
                                streak += 1
                            else:
                                streak = 0
                            if i >= 10 and first_trig is None and streak >= raw_onset:
                                first_trig = i
                        trig = first_trig is not None
                        if is_fault and trig:
                            tp += 1
                            if breach is not None:
                                leads.append(max(0.0, float(breach - first_trig)))
                        elif is_fault and not trig:
                            fn += 1
                        elif not is_fault and trig:
                            fp += 1
                        else:
                            tn += 1
                prec = tp / (tp + fp) if tp + fp else 0.0
                rec = tp / (tp + fn) if tp + fn else 0.0
                f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
                far = fp / (fp + tn) if fp + tn else 0.0
                grid.append({
                    "theta": theta,
                    "slope_gate_pct": gate_pct,
                    "raw_onset": raw_onset,
                    "TP": tp, "FP": fp, "FN": fn, "TN": tn,
                    "Precision": round(prec, 4),
                    "Recall": round(rec, 4),
                    "F1": round(f1, 4),
                    "FAR": round(far, 4),
                    "MeanLeadMin": round(sum(leads) / len(leads), 3) if leads else 0.0,
                })

    out_path = PROJECT_ROOT / "evidence" / "test_reports" / "ablation_sensitivity.json"
    out_path.write_text(json.dumps(grid, indent=2), encoding="utf-8")
    print(f"Saved {len(grid)} ablation configurations to {out_path}")


if __name__ == "__main__":
    main()
