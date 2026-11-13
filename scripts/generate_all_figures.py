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
    # 1. Dual-Building Fab & CUB Spatial Topology Diagram (FAB B2F-6F & CUB B2F-6F with Skybridge & Open Basement)
    fig, ax = plt.subplots(figsize=(15.5, 10.6), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    fig.patch.set_facecolor("#ffffff")

    # Outer container
    outer = patches.FancyBboxPatch((0.8, 0.8), 98.4, 98.4, boxstyle="round,pad=0.4", facecolor="#ffffff", edgecolor="#cbd5e1", linewidth=1.2)
    ax.add_patch(outer)

    # Title & Subtitle
    ax.text(50, 97.4, "半導體雙棟晶圓廠（FAB / CUB, B2F～6F）空間拓撲、空橋管廊與 PCW 封閉循環流程圖", ha="center", va="center", fontsize=14, fontweight="bold", color="#0f172a")
    ax.text(50, 95.0, "Dual-Building Spatial Architecture (FAB & CUB, B2F-6F), Skybridge Pipe Gallery, Open Basement & PCW Closed-Loop Operation", ha="center", va="center", fontsize=8.8, color="#64748b", style="italic")

    # Ground level line across buildings
    ax.plot([1.5, 98.5], [32.5, 32.5], color="#94a3b8", linestyle="--", linewidth=1.2, zorder=2)
    ax.text(2.2, 33.2, "地上層 (Above Ground) ▲", fontsize=8, fontweight="bold", color="#475569")
    ax.text(2.2, 31.5, "地下層 (Basement) ▼", fontsize=8, fontweight="bold", color="#475569")

    # ==================== 1. FAB BUILDING (Left) ====================
    fab_bg = patches.FancyBboxPatch((3.0, 13.0), 41.5, 79.5, boxstyle="round,pad=0.5", facecolor="#f8fafc", edgecolor="#3b82f6", linewidth=1.8)
    ax.add_patch(fab_bg)
    b_fab = patches.FancyBboxPatch((4.5, 88.2), 38.5, 3.8, boxstyle="round,pad=0.2", facecolor="#1d4ed8", edgecolor="none")
    ax.add_patch(b_fab)
    ax.text(23.7, 90.1, "FAB 棟（生產廠房 · B2F～6F）", ha="center", va="center", fontsize=11, fontweight="bold", color="#ffffff")

    # Floors in FAB
    # 6F
    f6_fab = patches.Rectangle((4.5, 84.0), 38.5, 3.6, facecolor="#ffffff", edgecolor="#cbd5e1", linewidth=0.8)
    ax.add_patch(f6_fab)
    ax.text(5.5, 85.8, "6F", fontsize=9, fontweight="bold", color="#475569", va="center")
    ax.text(8.5, 85.8, "屋頂排氣洗滌塔（Scrubbers）/ 冰水送風機房（MAU Penthouse）", fontsize=7.8, color="#334155", va="center")

    # 5F Cleanroom (Highlighted)
    f5_fab = patches.Rectangle((4.5, 73.5), 38.5, 9.8, facecolor="#eff6ff", edgecolor="#2563eb", linewidth=1.5)
    ax.add_patch(f5_fab)
    ax.text(5.5, 81.5, "5F Cleanroom（無塵室生產層 · Group 1 & 2）", fontsize=9.2, fontweight="bold", color="#1d4ed8")
    ax.text(5.5, 79.0, "• 涵蓋迴路：PCW01～PCW04 獨立閉迴路（20 組 Submains，共 80 測點）", fontsize=7.8, color="#1e3a8a")
    ax.text(5.5, 76.8, "• 製程設備：微影步進機（EUV / ArFi Litho）、乾式電漿蝕刻（Dry Etch）、高溫擴散氧化", fontsize=7.5, color="#334155")
    ax.text(5.5, 74.8, "• 流體特性：水壓公差極嚴苛（±0.05 bar），對流體水阻與壓力脈動高度敏感", fontsize=7.5, color="#0284c7")

    # 4F
    f4_fab = patches.Rectangle((4.5, 66.8), 38.5, 6.0, facecolor="#ffffff", edgecolor="#cbd5e1", linewidth=0.8)
    ax.add_patch(f4_fab)
    ax.text(5.5, 70.8, "4F", fontsize=9, fontweight="bold", color="#475569")
    ax.text(8.5, 70.8, "無塵室回風夾層（TFS / Return Air Plenum）/ 廠務管路轉接層", fontsize=7.8, color="#334155")
    ax.text(8.5, 68.3, "• 內部配置：PCW 回水集水幹管、排氣風管、化學品二次配管（Hookup）", fontsize=7.4, color="#64748b")

    # 3F Cleanroom (Highlighted)
    f3_fab = patches.Rectangle((4.5, 56.0), 38.5, 10.0, facecolor="#f0fdf4", edgecolor="#059669", linewidth=1.5)
    ax.add_patch(f3_fab)
    ax.text(5.5, 64.0, "3F Cleanroom（無塵室生產層 · Group 3 & 4）", fontsize=9.2, fontweight="bold", color="#047857")
    ax.text(5.5, 61.5, "• 涵蓋迴路：PCW05～PCW08 獨立閉迴路（20 組 Submains，共 80 測點）", fontsize=7.8, color="#065f46")
    ax.text(5.5, 59.3, "• 製程設備：化學氣相沉積（CVD）、物理氣相沉積（PVD）、研磨（CMP）、濕式清洗", fontsize=7.5, color="#334155")
    ax.text(5.5, 57.3, "• 流體特性：大流量連續供水、重負載熱交換，研磨盤摩擦熱即時冷卻", fontsize=7.5, color="#059669")

    # 2F
    f2_fab = patches.Rectangle((4.5, 47.0), 38.5, 8.2, facecolor="#ffffff", edgecolor="#cbd5e1", linewidth=0.8)
    ax.add_patch(f2_fab)
    ax.text(5.5, 52.5, "2F", fontsize=9, fontweight="bold", color="#475569")
    ax.text(8.5, 52.5, "無塵室下層輔助夾層（Sub-Fab Facility Mezzanine）", fontsize=7.8, color="#334155")
    ax.text(8.5, 50.0, "• 內部配置：真空泵浦群（Dry Pumps）、電漿射頻產生器（RF Generators）、洗滌塔", fontsize=7.4, color="#64748b")
    ax.text(8.5, 48.0, "• 輔助冷卻：承接 3F 機台之附屬動力設備二次冷卻水支管", fontsize=7.4, color="#64748b")

    # 1F
    f1_fab = patches.Rectangle((4.5, 34.5), 38.5, 11.5, facecolor="#ffffff", edgecolor="#cbd5e1", linewidth=0.8)
    ax.add_patch(f1_fab)
    ax.text(5.5, 43.5, "1F", fontsize=9, fontweight="bold", color="#475569")
    ax.text(8.5, 43.5, "廠務中央幹道／物流裝卸區／氣瓶室／支援設施", fontsize=7.8, color="#334155")
    ax.text(8.5, 40.5, "• 廠區功能：重型物流出入、化學品裝卸碼頭、公用公用氣體分配盤", fontsize=7.4, color="#64748b")
    ax.text(8.5, 37.0, "• 空橋連接埠：對接地上空橋管廊，電纜線槽與備援管道進出通道", fontsize=7.4, color="#0284c7")

    # B1F (FAB Booster Pumps)
    fb1_fab = patches.Rectangle((4.5, 23.5), 38.5, 9.5, facecolor="#fef3c7", edgecolor="#d97706", linewidth=1.5)
    ax.add_patch(fb1_fab)
    ax.text(5.5, 31.0, "B1F FAB 棟離心冷卻泵增壓站（Centrifugal Booster Pumps）", fontsize=9.2, fontweight="bold", color="#b45309")
    ax.text(5.5, 28.5, "• 運作核心 [步驟 2]：承接來自 CUB 之 22°C 供水，各二次離心泵加壓推送", fontsize=7.8, color="#92400e", fontweight="bold")
    ax.text(5.5, 26.2, "• 垂直立管中繼：推動冷卻水沿垂直供水立管（Supply Risers）直衝 3F 與 5F", fontsize=7.5, color="#334155")
    ax.text(5.5, 24.2, "• 儀表監控：安裝主流量計（FT）與母管壓力計（PTS），確保揚程與動壓穩定", fontsize=7.5, color="#475569")

    # B2F
    fb2_fab = patches.Rectangle((4.5, 14.0), 38.5, 8.5, facecolor="#ffffff", edgecolor="#cbd5e1", linewidth=0.8)
    ax.add_patch(fb2_fab)
    ax.text(5.5, 20.0, "B2F", fontsize=9, fontweight="bold", color="#475569")
    ax.text(8.5, 20.0, "地下二層重型結構筏基／全廠廢水分流溝槽／綜合共同管溝", fontsize=7.8, color="#334155")
    ax.text(8.5, 17.5, "• 地下共通特性：與 CUB 棟 B2F 開放打通，提供重型管線無障礙鋪設空間", fontsize=7.4, color="#475569")
    ax.text(8.5, 15.2, "• 抗震與阻尼：大體積筏式基礎隔離泵浦低頻震動，阻絕向生產層傳播", fontsize=7.4, color="#64748b")

    # ==================== 2. CUB BUILDING (Right) ====================
    cub_bg = patches.FancyBboxPatch((55.5, 13.0), 41.5, 79.5, boxstyle="round,pad=0.5", facecolor="#f8fafc", edgecolor="#475569", linewidth=1.8)
    ax.add_patch(cub_bg)
    b_cub = patches.FancyBboxPatch((57.0, 88.2), 38.5, 3.8, boxstyle="round,pad=0.2", facecolor="#334155", edgecolor="none")
    ax.add_patch(b_cub)
    ax.text(76.2, 90.1, "CUB 棟（中央廠務大樓 · B2F～6F）", ha="center", va="center", fontsize=11, fontweight="bold", color="#ffffff")

    # Floors in CUB
    # 6F
    f6_cub = patches.Rectangle((57.0, 84.0), 38.5, 3.6, facecolor="#ffffff", edgecolor="#cbd5e1", linewidth=0.8)
    ax.add_patch(f6_cub)
    ax.text(58.0, 85.8, "6F", fontsize=9, fontweight="bold", color="#475569", va="center")
    ax.text(61.0, 85.8, "屋頂大型冷卻水塔群（Cooling Towers & Heat Dissipation）", fontsize=7.8, color="#334155", va="center")

    # 5F
    f5_cub = patches.Rectangle((57.0, 73.5), 38.5, 9.8, facecolor="#ffffff", edgecolor="#cbd5e1", linewidth=0.8)
    ax.add_patch(f5_cub)
    ax.text(58.0, 81.5, "5F 特高壓變電所與配電中樞（161kV Substation）", fontsize=9, fontweight="bold", color="#334155")
    ax.text(58.0, 78.8, "• 主變壓器（Main Transformers）、氣體絕緣開關設備（GIS Switchgear）", fontsize=7.5, color="#475569")
    ax.text(58.0, 76.5, "• 動力中樞：提供變頻泵浦、主冷水機組與無塵室百萬瓦級不斷電電力", fontsize=7.5, color="#64748b")
    ax.text(58.0, 74.5, "• 緊急備援：配備雙迴路自動切換開關（ATS）與柴油發電機組鏈路", fontsize=7.5, color="#64748b")

    # 4F
    f4_cub = patches.Rectangle((57.0, 66.8), 38.5, 6.0, facecolor="#ffffff", edgecolor="#cbd5e1", linewidth=0.8)
    ax.add_patch(f4_cub)
    ax.text(58.0, 70.8, "4F", fontsize=9, fontweight="bold", color="#475569")
    ax.text(61.0, 70.8, "無油離心式空壓機組群（Centrifugal Air Compressors / CDA）", fontsize=7.8, color="#334155")
    ax.text(61.0, 68.3, "• 提供全廠高潔淨乾燥空氣與氣壓控制儀表源", fontsize=7.4, color="#64748b")

    # 3F
    f3_cub = patches.Rectangle((57.0, 56.0), 38.5, 10.0, facecolor="#ffffff", edgecolor="#cbd5e1", linewidth=0.8)
    ax.add_patch(f3_cub)
    ax.text(58.0, 64.0, "3F 超純水系統處理區（Ultra Pure Water / UPW System）", fontsize=9, fontweight="bold", color="#334155")
    ax.text(58.0, 61.5, "• RO 逆滲透、EDI 電透析去離子、紫外線殺菌（UV）與真空脫氣柱", fontsize=7.5, color="#475569")
    ax.text(58.0, 59.3, "• PCW 水質供應：供應電阻率 >18 MΩ·cm 之超純水作為 PCW 補給水", fontsize=7.5, color="#0284c7")
    ax.text(58.0, 57.3, "• 嚴苛防腐阻垢：防止換熱板結垢、微小管徑阻塞與金屬離子析出污染", fontsize=7.5, color="#64748b")

    # 2F
    f2_cub = patches.Rectangle((57.0, 47.0), 38.5, 8.2, facecolor="#ffffff", edgecolor="#cbd5e1", linewidth=0.8)
    ax.add_patch(f2_cub)
    ax.text(58.0, 52.5, "2F", fontsize=9, fontweight="bold", color="#475569")
    ax.text(61.0, 52.5, "廠務中央監控大廳（FMCS Central Control Room）& 伺服器機房", fontsize=7.8, color="#334155")
    ax.text(61.0, 50.0, "• SCADA 系統中樞：本專案 Web SCADA v2.0、Modbus 閘道器與 SQLite 伺服器", fontsize=7.4, color="#0369a1", fontweight="bold")
    ax.text(61.0, 48.0, "• 24 小時值班監控：即時推播全廠 320 測點 T-30/20/10 早期預警與 TTL 倒數", fontsize=7.4, color="#0369a1")

    # 1F
    f1_cub = patches.Rectangle((57.0, 34.5), 38.5, 11.5, facecolor="#ffffff", edgecolor="#cbd5e1", linewidth=0.8)
    ax.add_patch(f1_cub)
    ax.text(58.0, 43.5, "1F 集中式主冷水機組區（Central Chillers 能源中樞）", fontsize=9, fontweight="bold", color="#334155")
    ax.text(58.0, 40.5, "• 設備配置：離心式主冷水機組群（Centrifugal Chillers, 數千 RT 製冷能力）", fontsize=7.5, color="#475569")
    ax.text(58.0, 38.2, "• 冰水供應：生產 7°C 冰水（Chilled Water），供應全廠一次冷源與換熱混水", fontsize=7.5, color="#2563eb")
    ax.text(58.0, 36.0, "• 變頻主泵：一次循環定壓泵群，維持全廠冷卻能源充沛供給", fontsize=7.5, color="#64748b")

    # B1F (CUB PCW Processing)
    fb1_cub = patches.Rectangle((57.0, 23.5), 38.5, 9.5, facecolor="#f1f5f9", edgecolor="#475569", linewidth=1.5)
    ax.add_patch(fb1_cub)
    ax.text(58.0, 31.0, "B1F CUB 棟冷卻水熱交換與水質再循環中樞", fontsize=9.2, fontweight="bold", color="#0f172a")
    ax.text(58.0, 28.5, "• 處理流程 [步驟 5 & 6]：脫氣器（除氣泡）-> 微米濾網 -> 一次板換（PHE）降溫", fontsize=7.6, color="#0f172a", fontweight="bold")
    ax.text(58.0, 26.2, "• 混水恆溫 [步驟 1]：視回水水溫及水量，調度混入一次冰水，維持 22.0 ± 0.5 °C", fontsize=7.6, color="#0284c7", fontweight="bold")
    ax.text(58.0, 24.2, "• 差壓調度：差壓旁通調度閥（DPV），防止端部憋壓與水錘脈衝", fontsize=7.4, color="#475569")

    # B2F
    fb2_cub = patches.Rectangle((57.0, 14.0), 38.5, 8.5, facecolor="#ffffff", edgecolor="#cbd5e1", linewidth=0.8)
    ax.add_patch(fb2_cub)
    ax.text(58.0, 20.0, "B2F", fontsize=9, fontweight="bold", color="#475569")
    ax.text(61.0, 20.0, "大型地下水蓄水池／消防儲槽／廢水集中中和池", fontsize=7.8, color="#334155")
    ax.text(61.0, 17.5, "• 地下共通特性：地下二層全開放連通 FAB 棟，提供緊急大量儲備水源", fontsize=7.4, color="#475569")
    ax.text(61.0, 15.2, "• 連通管線：重型管線在地下室貫穿兩棟，無地面阻礙", fontsize=7.4, color="#64748b")

    # ==================== 3. INTERCONNECTIONS ====================
    # A. Skybridge (地上鋼構空橋管廊)
    sb_box = patches.FancyBboxPatch((44.0, 52.0), 12.0, 14.0, boxstyle="round,pad=0.3", facecolor="#fef9c3", edgecolor="#ca8a04", linewidth=1.8, linestyle="-")
    ax.add_patch(sb_box)
    ax.plot([44.5, 55.5], [52.5, 65.5], color="#eab308", linewidth=1.2, alpha=0.6)
    ax.plot([44.5, 55.5], [65.5, 52.5], color="#eab308", linewidth=1.2, alpha=0.6)
    ax.text(50.0, 63.8, "地上鋼構空橋", ha="center", va="center", fontsize=9, fontweight="bold", color="#854d0e")
    ax.text(50.0, 61.8, "（Pipe Bridge）", ha="center", va="center", fontsize=8, fontweight="bold", color="#854d0e")
    ax.text(50.0, 57.5, "內含：\n• PCW 熱水回水主管 [步驟 4]\n• 雙向備援水管\n• 儀表與通訊線槽", ha="center", va="center", fontsize=7.0, color="#713f12")

    # B. Open Interconnected Basement (地下室開放共通)
    bs_box = patches.FancyBboxPatch((44.0, 14.0), 12.0, 18.5, boxstyle="square,pad=0.2", facecolor="#e0f2fe", edgecolor="#0284c7", linewidth=2.0, linestyle="-")
    ax.add_patch(bs_box)
    ax.text(50.0, 28.5, "地下室開放共通", ha="center", va="center", fontsize=9.2, fontweight="bold", color="#0369a1")
    ax.text(50.0, 26.5, "（B1F～B2F 通廊）", ha="center", va="center", fontsize=8.2, fontweight="bold", color="#0369a1")
    ax.text(50.0, 21.0, "兩棟地下室無實體隔震牆\n開放連通 · 自由穿梭\n\n[步驟 1] 供水主管\nCUB 供應水 -> FAB B1F", ha="center", va="center", fontsize=7.2, color="#0c4a6e", multialignment="center")

    # ==================== 4. WATER FLOW ARROWS & LABELS ====================
    # Step 1: Supply from CUB B1F -> FAB B1F (through basement)
    ax.annotate("", xy=(43.5, 27.5), xytext=(57.0, 27.5),
                arrowprops=dict(arrowstyle="->", lw=3.0, color="#2563eb"))
    ax.text(50.0, 29.8, "PCW 供水 (22°C) ->", ha="center", va="bottom", fontsize=8.2, fontweight="bold", color="#1d4ed8")

    # Step 2: Riser up inside FAB from B1F to 3F & 5F
    ax.annotate("", xy=(4.0, 77.0), xytext=(4.0, 28.0),
                arrowprops=dict(arrowstyle="->", lw=3.0, color="#2563eb"))
    ax.text(2.6, 52.0, "垂直供水立管 (Supply Riser) ▲", rotation=90, ha="center", va="center", fontsize=8.5, fontweight="bold", color="#1d4ed8")

    # Step 3: Feeding into 3F & 5F Cleanroom tools
    ax.annotate("", xy=(7.0, 78.5), xytext=(4.0, 78.5),
                arrowprops=dict(arrowstyle="->", lw=2.0, color="#2563eb"))
    ax.text(12.0, 78.5, "[步驟 3] Submain 調節閥進機台盤管吸熱", fontsize=7.5, color="#1e3a8a", fontweight="bold", va="center")

    ax.annotate("", xy=(7.0, 61.0), xytext=(4.0, 61.0),
                arrowprops=dict(arrowstyle="->", lw=2.0, color="#2563eb"))
    ax.text(12.0, 61.0, "[步驟 3] Submain 調節閥進機台盤管吸熱", fontsize=7.5, color="#065f46", fontweight="bold", va="center")

    # Step 4: Return flow from 5F down and into Skybridge
    ax.annotate("", xy=(44.0, 58.5), xytext=(42.5, 78.5),
                arrowprops=dict(arrowstyle="->", lw=2.8, color="#dc2626"))
    ax.annotate("", xy=(44.0, 58.5), xytext=(42.5, 61.0),
                arrowprops=dict(arrowstyle="->", lw=2.8, color="#dc2626"))
    ax.text(39.0, 69.5, "回水立管 (Return) ▼", rotation=90, ha="center", va="center", fontsize=8.2, fontweight="bold", color="#b91c1c")

    # Skybridge return to CUB B1F
    ax.annotate("", xy=(57.0, 31.0), xytext=(55.5, 58.5),
                arrowprops=dict(arrowstyle="->", lw=2.8, color="#dc2626"))
    ax.text(59.5, 45.0, "熱水回流 CUB (B1F) ▼", rotation=-90, ha="center", va="center", fontsize=8.2, fontweight="bold", color="#b91c1c")

    # ==================== 5. BOTTOM SUMMARY BAR (Section 1.1.3 Highlights) ====================
    sum_box = patches.FancyBboxPatch((3.0, 1.8), 94.0, 9.5, boxstyle="round,pad=0.4", facecolor="#ffffff", edgecolor="#0284c7", linewidth=1.5)
    ax.add_patch(sum_box)

    ax.text(5.0, 9.4, "1.1.3 PCW 系統架構配置、功能目的與運作程序精要彙整：", fontsize=9.5, fontweight="bold", color="#0369a1")
    ax.text(5.0, 7.3, "1. 架構配置：8 套獨立封閉循環迴路（PCW01～PCW08）· 80 個 Submain 分支 · 全廠 320 測點（160 支壓力計 PT-01～160、80 支溫度計 TT、16 支主流量計 FT）", fontsize=8.2, color="#0f172a", fontweight="bold")
    ax.text(5.0, 5.3, "2. 參數分組與工程門檻：四大參數分組（G1～G4）各自定義嚴格運轉基準線（Baseline）與四級警報安全門檻（HiHi, Hi, Lo, LoLo）", fontsize=8.0, color="#334155")
    ax.text(5.0, 3.4, "3. 功能目的：提供高純度去離子冷卻水，維持供水溫度在 22.0 ± 0.5 °C，並維持穩定供回水壓差，即時吸收製程高熱", fontsize=8.0, color="#334155")
    ax.text(5.0, 1.6, "4. 運作程序：CUB 供應水 -> FAB B1F 增壓 -> 垂直立管向上輸送至 3F/5F 各區 -> Submain 進機台吸熱 -> 匯入回水集水管 -> 空橋熱水回 CUB -> 脫氣器與微米濾網 -> 一次板換降溫 -> 混入冰水再循環", fontsize=7.8, color="#b45309", fontweight="bold")

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
