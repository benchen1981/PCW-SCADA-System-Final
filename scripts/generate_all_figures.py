"""Generate publication-grade 300-DPI figures from actual experimental outputs and logs."""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib import font_manager
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = ROOT / "figures"
THESIS_PIC_DIR = ROOT / "thesis" / "picture"
EVIDENCE_FIG_DIR = ROOT / "evidence" / "figures"
for d in (FIG_DIR, THESIS_PIC_DIR, EVIDENCE_FIG_DIR):
    d.mkdir(parents=True, exist_ok=True)

for cand in ["PingFang TC", "Heiti TC", "Arial Unicode MS", "Noto Sans CJK TC"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.sans-serif"] = [cand, "DejaVu Sans"]
        break
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.facecolor"] = "white"
plt.rcParams["axes.facecolor"] = "white"


def save_fig(fig: plt.Figure, name: str) -> None:
    for out_dir in (FIG_DIR, THESIS_PIC_DIR, EVIDENCE_FIG_DIR):
        fig.savefig(out_dir / name, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_architecture_diagrams() -> None:
    """Design diagrams (explicitly labeled as system design, not empirical benchmarks)."""
    # 1. Dual-Level Fab & 8-PCW Topology Diagram
    fig, ax = plt.subplots(figsize=(11, 5.4))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
    ax.axis("off")

    def box(x, y, w, h, title, body, fc="#f8fafc", ec="#111827", lw=1.5):
        r = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.6", facecolor=fc, edgecolor=ec, linewidth=lw)
        ax.add_patch(r)
        ax.text(x + w / 2, y + h - 3.0, title, ha="center", va="top", fontsize=9.5, fontweight="bold", color="#111827")
        ax.text(x + w / 2, y + h / 2 - 1.5, body, ha="center", va="center", fontsize=8.0, color="#1f2937")

    ax.text(50, 58, "設計架構圖：雙層半導體晶圓廠 PCW01–PCW08 迴路與 320 測點拓撲", ha="center", va="top", fontsize=11.5, fontweight="bold")
    box(4, 37, 42, 16, "2F Cleanroom 無塵室生產層", "Group 1: PCW01, PCW02 (1.50 bar | H=1.70, L=1.30)\nGroup 2: PCW03, PCW04 (1.90 bar | H=2.10, L=1.70)\n各迴路 10 Submains × (PTS, PTR, FT, PDT) = 160 測點", fc="#f1f5f9")
    box(54, 37, 42, 16, "1F Sub-Fab 廠務輔助層", "Group 3: PCW05, PCW06 (2.50 bar | H=2.70, L=2.30)\nGroup 4: PCW07, PCW08 (2.20 bar | H=2.40, L=2.00)\n各迴路 10 Submains × (PTS, PTR, FT, PDT) = 160 測點", fc="#f1f5f9")
    box(16, 17, 68, 12, "CUB 中央廠務公用區 (供給與熱交換迴路)", "冰水主機 / 板式熱交換器 / VFD 主泵群 -> 供回水獨立立管 (Riser) -> 全廠 80 組 Submain 配對 (160 PT)", fc="#e2e8f0")
    box(10, 2, 80, 9, "Modbus/TCP FLOAT32 CDAB 映射 (40001–40639, 640 Registers)", "Unit ID 1 | FC03/06/16 | 每感測器占 2 暫存器 -> 1 分鐘聚合 Historian -> PT 單點 / 配對 / 系統三層推論", fc="#ffffff")

    for x in (25, 75):
        ax.annotate("", xy=(x, 36.5), xytext=(x, 29.5), arrowprops=dict(arrowstyle="<->", lw=1.5, color="#111827"))
    ax.annotate("", xy=(50, 16.5), xytext=(50, 11.5), arrowprops=dict(arrowstyle="<->", lw=1.5, color="#111827"))
    save_fig(fig, "fig_fab_topology_design.png")

    # 2. Five-Layer Implemented vs Planned System Architecture Diagram
    fig, ax = plt.subplots(figsize=(11, 5.2))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 56)
    ax.axis("off")
    ax.text(50, 54.5, "系統分層架構圖（實線＝本機/線上實測驗證；虛線＝廠區授權規劃中項目）", ha="center", va="top", fontsize=11, fontweight="bold")

    layers = [
        (42, "1. Data Source Layer", "模擬器 (NORMAL/DRIFT/STEP/SPIKE/BAD/COMM_LOSS)\n& Python Modbus/TCP Server (:15020)", "現場實體 PT/FT/PDT 與 PLC\n(尚未接入實體廠務設備)", True),
        (32, "2. Data Management Layer", "1-min Historian 環形緩衝 + SQLite WAL\n(historian_points, prediction_logs, alarms)", "正式工廠 MS-SQL SCADA Historian\n(規劃架構)", True),
        (22, "3. Inference Layer", "統一 Dual-Window N10 + Slope + L1–L7 引擎\nPython 與 TypeScript 1:1 對等 (< 1e-9)", "每分鐘 SQL Agent 批次排程\n(規劃架構)", True),
        (12, "4. Result Integration Layer", "FastAPI REST (/api/*) + SSE (/api/stream) + WS (/ws/stream)\nModbus Holding Register 回寫與即時一致同步", "OPC-UA / SQL-to-SCADA Tag\n回寫正式產線 HMI (規劃中)", True),
        (2,  "5. HMI Presentation Layer", "React 19 Web SCADA (9 大頁面 + Pair 診斷)\nChrome/Puppeteer 自動巡檢與 >10 分鐘實驗", "現場中控室正式輪班監控\n(待場域驗證後部署)", True),
    ]
    for y, title, impl, plan, _ in layers:
        r1 = patches.FancyBboxPatch((4, y), 56, 7.6, boxstyle="round,pad=0.3", facecolor="#f8fafc", edgecolor="#111827", linewidth=1.6, linestyle="-")
        r2 = patches.FancyBboxPatch((64, y), 32, 7.6, boxstyle="round,pad=0.3", facecolor="#ffffff", edgecolor="#64748b", linewidth=1.3, linestyle="--")
        ax.add_patch(r1)
        ax.add_patch(r2)
        ax.text(6, y + 6.4, f"{title}（已實作驗證）", ha="left", va="top", fontsize=8.8, fontweight="bold", color="#111827")
        ax.text(6, y + 4.1, impl, ha="left", va="top", fontsize=7.6, color="#1f2937")
        ax.text(66, y + 6.4, "規劃中／未驗證範圍", ha="left", va="top", fontsize=8.3, fontweight="bold", color="#475569")
        ax.text(66, y + 4.1, plan, ha="left", va="top", fontsize=7.4, color="#475569")
        if y > 2:
            ax.annotate("", xy=(32, y - 0.3), xytext=(32, y - 2.1), arrowprops=dict(arrowstyle="<-", lw=1.4, color="#111827"))
            ax.annotate("", xy=(80, y - 0.3), xytext=(80, y - 2.1), arrowprops=dict(arrowstyle="<-", lw=1.2, ls="--", color="#64748b"))

    save_fig(fig, "fig_system_architecture_layers.png")

    # 3. Past-Only Causal Window Diagram (schematic equal-readability widths)
    fig, ax = plt.subplots(figsize=(11.0, 3.8))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.text(50, 9.5, "Past-Only 70 分鐘因果滑動視窗與外推視域示意圖（禁止未來資料參與 t 時刻推論）", ha="center", va="top", fontsize=10.5, fontweight="bold")
    segs = [
        (3, 38, "#e2e8f0", "基準視窗 B = [t-70, t-10)\n60 pts: BaseAvg60, M60"),
        (41, 13, "#cbd5e1", "前期 P\n[t-10, t-5)\n5 pts"),
        (54, 13, "#94a3b8", "近期 R\n[t-5, t)\n5 pts"),
        (67, 30, "#f8fafc", "外推視域 (僅輸出 Fcst，不讀未來值)\nt+10 (T-10) | t+20 (T-20) | t+30 (T-30)"),
    ]
    for x, w, fc, lbl in segs:
        ls = "--" if x >= 67 else "-"
        rect = patches.Rectangle((x, 3.0), w, 4.0, facecolor=fc, edgecolor="#111827", linewidth=1.4, linestyle=ls)
        ax.add_patch(rect)
        ax.text(x + w / 2, 5.0, lbl, ha="center", va="center", fontsize=8.0, color="#111827", fontweight="bold" if 41 <= x < 67 else "normal")
    ax.axvline(67 / 100.0 * 100, ymin=0.18, ymax=0.80, color="#b91c1c", lw=2.2)
    ax.text(67, 1.8, "推論時刻 t (x_now)", ha="center", va="top", fontsize=9, fontweight="bold", color="#b91c1c")
    save_fig(fig, "fig_past_only_window_design.png")


def plot_excel_replay() -> None:
    rows = list(csv.DictReader((ROOT / "experiments" / "EXCEL_PROGRAM_COMPARISON.csv").open()))
    t_idx = np.arange(len(rows))
    vals = np.array([float(r["value"]) for r in rows])
    states = [r["excel_state"] for r in rows]
    uni_states = [r["unified_v1_state"] for r in rows]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11.5, 5.8), sharex=True, gridspec_kw={"height_ratios": [2.2, 1.0]})
    ax1.plot(t_idx, vals, color="#1f2937", lw=1.0, label="PT-1 壓力讀值 (bar)")
    ax1.axhline(1.70, color="#b91c1c", ls="--", lw=1.3, label="SCADA Hard Alarm = 1.70 bar")
    ax1.axhline(1.55, color="#64748b", ls=":", lw=1.0, label="Gate30 = 1.55 bar")
    for lvl, col, mk in (("T-30", "#d97706", "o"), ("T-20", "#ea580c", "^"), ("T-10", "#dc2626", "s"), ("EVENT", "#7c2d12", "x")):
        idx = [i for i, s in enumerate(uni_states) if s == lvl]
        if idx:
            ax1.scatter(idx, vals[idx], s=14, color=col, marker=mk, label=f"Unified V1 {lvl} ({len(idx)})", zorder=3)
    ax1.set_ylabel("壓力 (bar)")
    ax1.set_title("PT-1 歷史資料 (480 分鐘) 逐筆回放與 Excel/程式一致性驗證 (最大誤差 = 0.0)", fontsize=10.5, fontweight="bold")
    ax1.legend(ncol=3, fontsize=7.5, loc="lower right")
    ax1.grid(alpha=0.25)

    code_map = {"INSUFFICIENT_DATA": -1, "Normal": 0, "NORMAL": 0, "T-30": 1, "T-20": 2, "T-10": 3, "EVENT": 4}
    ax2.step(t_idx, [code_map.get(s, 0) for s in states], where="post", color="#475569", lw=1.2, label="Excel Rollback 狀態")
    ax2.step(t_idx, [code_map.get(s, 0) for s in uni_states], where="post", color="#111827", lw=1.1, ls="--", label="Unified V1 狀態")
    ax2.set_yticks([-1, 0, 1, 2, 3, 4])
    ax2.set_yticklabels(["INSUFF", "NORMAL", "T-30", "T-20", "T-10", "EVENT"], fontsize=7.5)
    ax2.set_xlabel("時間序列索引 (分鐘, 2026-08-05 03:01 起)")
    ax2.set_ylabel("推論狀態")
    ax2.legend(fontsize=8, loc="upper left")
    ax2.grid(alpha=0.25)
    save_fig(fig, "fig_excel_pt1_replay.png")


def plot_baseline_and_ablation() -> None:
    summary = json.loads((ROOT / "evidence" / "test_reports" / "full_experiments_summary.json").read_text())
    pt_stats = summary["matrix_summary"]["pt_160"]
    models = ["Static Threshold", "EWMA", "Naive OLS", "Proposed Unified"]
    labels = ["Static\n(ISA-18.2)", "EWMA\n(λ=0.2, 3σ)", "Naive OLS\n(k=10)", "Proposed\nUnified V1"]

    rec = [pt_stats[m]["Recall"] * 100 for m in models]
    prec = [pt_stats[m]["Precision"] * 100 for m in models]
    f1 = [pt_stats[m]["F1"] * 100 for m in models]
    far = [pt_stats[m]["FAR"] * 100 for m in models]
    lead = [pt_stats[m]["MeanLeadMin"] for m in models]

    x = np.arange(len(models))
    w = 0.21
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.4, 4.8))
    b1 = ax1.bar(x - 1.5 * w, rec, w, label="Recall (%)", color="#1e293b")
    b2 = ax1.bar(x - 0.5 * w, prec, w, label="Precision (%)", color="#64748b")
    b3 = ax1.bar(x + 0.5 * w, f1, w, label="F1×100", color="#94a3b8")
    b4 = ax1.bar(x + 1.5 * w, far, w, label="FAR (%)", color="#cbd5e1", edgecolor="#111827", hatch="//")
    for bars in (b1, b2, b3, b4):
        for bar in bars:
            h = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width() / 2, h + 1.2, f"{h:.1f}", ha="center", va="bottom", fontsize=6.4, rotation=45)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=8.5)
    ax1.set_ylim(0, 126)
    ax1.set_ylabel("百分比 / 分數 (%)")
    ax1.set_title("(a) 160 PT 測點 (1,920 場) 四種方法公平比較", fontsize=10, fontweight="bold", pad=22)
    ax1.legend(fontsize=7.5, ncol=4, loc="lower center", bbox_to_anchor=(0.5, 1.00), frameon=False)
    ax1.grid(axis="y", alpha=0.25)

    bars_l = ax2.bar(x, lead, 0.48, color=["#cbd5e1", "#94a3b8", "#475569", "#111827"])
    for bar in bars_l:
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width() / 2, h + 0.25, f"{h:.2f} min", ha="center", va="bottom", fontsize=8)
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, fontsize=8.5)
    ax2.set_ylim(0, max(lead) + 2.5)
    ax2.set_ylabel("平均預警提前量 (min)")
    ax2.set_title("(b) 1,280 異常場次平均提前量 (Lead Time)", fontsize=10, fontweight="bold")
    ax2.grid(axis="y", alpha=0.25)
    save_fig(fig, "fig_model_comparison_1920.png")

    # Ablation chart (theta x raw_onset at g=5%)
    ab = json.loads((ROOT / "evidence" / "test_reports" / "ablation_sensitivity.json").read_text())
    g5 = [r for r in ab if r["slope_gate_pct"] == 5.0]
    thetas = [1.5, 1.8, 2.0, 2.5]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.3))
    for onset, ls, mk, col in ((1, "--", "o", "#64748b"), (2, "-", "s", "#111827")):
        sub = [next(r for r in g5 if r["theta"] == th and r["raw_onset"] == onset) for th in thetas]
        ax1.plot(thetas, [r["FAR"] * 100 for r in sub], ls=ls, marker=mk, color=col, lw=1.8, label=f"raw_onset = {onset}")
        ax2.plot(thetas, [r["MeanLeadMin"] for r in sub], ls=ls, marker=mk, color=col, lw=1.8, label=f"raw_onset = {onset}")
        for r in sub:
            ax1.annotate(f"{r['FAR']*100:.1f}%", (r["theta"], r["FAR"] * 100), textcoords="offset points", xytext=(0, 6), ha="center", fontsize=7.5)
            ax2.annotate(f"{r['MeanLeadMin']:.2f}m", (r["theta"], r["MeanLeadMin"]), textcoords="offset points", xytext=(0, 6), ha="center", fontsize=7.5)
    ax1.set_title("(a) 敏感度 θ 與突波確認次數對誤報率 (FAR) 之影響", fontsize=9.5, fontweight="bold")
    ax1.set_xlabel("N10 門檻 θ (g = 5% span)")
    ax1.set_ylabel("誤報率 FAR (%)")
    ax1.set_ylim(0, 50)
    ax1.grid(alpha=0.25)
    ax1.legend(fontsize=8)
    ax2.set_title("(b) 敏感度 θ 與突波確認次數對平均提前量之影響", fontsize=9.5, fontweight="bold")
    ax2.set_xlabel("N10 門檻 θ (g = 5% span)")
    ax2.set_ylabel("平均提前量 (min)")
    ax2.set_ylim(9.0, 12.0)
    ax2.grid(alpha=0.25)
    ax2.legend(fontsize=8)
    save_fig(fig, "fig_ablation_onset_sensitivity.png")


def plot_performance_benchmarks() -> None:
    perf = json.loads((ROOT / "evidence" / "test_reports" / "performance_benchmarks.json").read_text())
    items = [
        ("單點純計算\n(10k calls)", perf["single_predict"]["mean_us"], perf["single_predict"]["p99_us"]),
        ("Modbus FC03\n(20 regs, 100x)", perf["modbus_tcp_fc03_20regs"]["mean_us"], perf["modbus_tcp_fc03_20regs"]["p99_us"]),
        ("SQLite 查詢\n(100 rows)", perf["sqlite_query_100_rows"]["mean_us"], perf["sqlite_query_100_rows"]["p99_us"]),
        ("320 測點批次\n(純計算, 500x)", perf["batch_320_predict"]["mean_us"], perf["batch_320_predict"]["p99_us"]),
        ("320 測點推論+\nSQLite 寫入", perf["full_320_eval_and_sqlite_insert"]["mean_us"], perf["full_320_eval_and_sqlite_insert"]["p99_us"]),
    ]
    labels = [x[0] for x in items]
    means = [x[1] for x in items]
    p99s = [x[2] for x in items]
    x = np.arange(len(items))
    w = 0.35
    fig, ax = plt.subplots(figsize=(10.5, 4.3))
    b1 = ax.bar(x - w / 2, means, w, label="Mean Latency (µs)", color="#334155")
    b2 = ax.bar(x + w / 2, p99s, w, label="P99 Latency (µs)", color="#94a3b8", edgecolor="#111827")
    ax.set_yscale("log")
    for bars in (b1, b2):
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h * 1.12, f"{h:.1f}", ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("延遲 (µs, 對數刻度)")
    ax.set_ylim(5, max(p99s) * 2.5)
    ax.set_title("Apple M5 (macOS 26.7.3) 實測微基準與全系統鏈路延遲分佈", fontsize=10.5, fontweight="bold")
    ax.legend(fontsize=8.5)
    ax.grid(axis="y", alpha=0.25, which="both")
    save_fig(fig, "fig_performance_latency.png")


def plot_11min_realtime_traces() -> None:
    local_path = ROOT / "evidence" / "inference_logs" / "local_11min_deviation_log.json"
    dep_path = ROOT / "evidence" / "inference_logs" / "deployed_11min_deviation_log.json"
    if not local_path.exists() or not dep_path.exists():
        print("11min logs not ready yet; skipping realtime trace plot.")
        return

    local_log = json.loads(local_path.read_text())
    dep_log = json.loads(dep_path.read_text())

    # Plot local 11.5-min behavioral deviation & drift progression
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11.5, 5.8), sharex=True)
    t_loc = [s["elapsedMin"] for s in local_log]
    for tag, lbl, col, ls in (
        ("PCW01.Submain01.PTS", "PCW01.Submain01.PTS (基準+斜坡漂移, H=1.70)", "#b91c1c", "-"),
        ("PCW01.Submain01.PTR", "PCW01.Submain01.PTR (基準下偏 1.38 bar, L=1.30)", "#1d4ed8", "--"),
        ("PCW03.Submain01.PTS", "PCW03.Submain01.PTS (基準上偏 2.02 bar, H=2.10)", "#047857", "-."),
    ):
        vals = []
        for s in local_log:
            rec = next((r for r in s["representative"] if r["tagId"] == tag), None)
            vals.append(rec["currentValue"] if rec else np.nan)
        ax1.plot(t_loc, vals, color=col, ls=ls, lw=1.6, marker="o", ms=3, label=lbl)
    ax1.axhline(1.70, color="#b91c1c", ls=":", lw=1.0, label="PCW01 HI=1.70 / LO=1.30")
    ax1.axhline(1.30, color="#1d4ed8", ls=":", lw=1.0)
    ax1.set_ylim(1.22, 2.28)
    ax1.set_ylabel("壓力讀值 (bar)")
    ax1.set_title("重構 v2.0 系統 11.35 分鐘 Modbus/TCP 基準行為偏差實測軌跡與全廠預警變化", fontsize=10.5, fontweight="bold")
    ax1.legend(fontsize=7.6, ncol=2, loc="upper center")
    ax1.grid(alpha=0.25)

    # Bottom panel: count of all-320 and 160-PT sensors in early warning / event + DRIFT alarms
    all_warn_cnt = [
        sum(s.get("allStateCounts", {}).get(k, 0) for k in ("T-30", "T-20", "T-10", "EVENT"))
        for s in local_log
    ]
    warn_cnt = [
        sum(s["ptStateCounts"].get(k, 0) for k in ("T-30", "T-20", "T-10", "EVENT"))
        for s in local_log
    ]
    drift_alm = [s["driftAlarmsCount"] for s in local_log]
    ax2.plot(t_loc, all_warn_cnt, color="#0369a1", lw=1.7, marker="o", ms=3.2, label="本機重構 v2.0：全廠 320 測點預警/事件數 (累計 320/320)")
    ax2.plot(t_loc, warn_cnt, color="#111827", lw=1.8, marker="s", ms=3.5, label="本機重構 v2.0：160 PT 子集預警/事件數")
    ax2.plot(t_loc, drift_alm, color="#b45309", lw=1.5, ls="--", marker="^", ms=3.5, label="本機重構 v2.0：Alarm Center DRIFT 警報數")

    t_dep = [s["elapsedMin"] for s in dep_log]
    dep_warn = [min(160, s["nonNormalCount"]) for s in dep_log]
    ax2.plot(t_dep, dep_warn, color="#64748b", lw=1.4, ls=":", marker="x", ms=4, label="線上舊版 (Vercel)：PT 非 NORMAL 數 (SM01 於 10.48m 失效)")

    ax2.axvline(10.0, color="#475569", ls="--", lw=1.0)
    ax2.text(10.1, 18, "10 min 門檻線", fontsize=8, color="#475569")
    ax2.set_ylim(-12, 410)
    ax2.set_xlabel("真實經過時間 (minutes)")
    ax2.set_ylabel("感測器 / 警報數量")
    ax2.legend(fontsize=7.2, loc="upper left", ncol=2)
    ax2.grid(alpha=0.25)
    save_fig(fig, "fig_11min_realtime_deviation.png")


def main():
    plot_architecture_diagrams()
    plot_excel_replay()
    plot_baseline_and_ablation()
    plot_performance_benchmarks()
    plot_11min_realtime_traces()
    print("Figures generated in:", FIG_DIR)


if __name__ == "__main__":
    main()
