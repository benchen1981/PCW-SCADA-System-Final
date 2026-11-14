# PCW Web SCADA 統計式早期預警系統與碩士論文重構專案 (v2.0)

**Bilingual Technical Manual / 中英文完整技術說明文件**

> **半導體廠務製程冷卻水 (Process Cooling Water, PCW) 早期壓力預警與全端 Web SCADA 系統**  
> **Re-Engineered Statistical Early-Warning Methodology, Full-Stack Web SCADA v2.0, Async Modbus/TCP Server, SQLite Historian & Reproducible Verification Suite**  
> **Session Timeline**: 2026-11-11 06:56:50 CST ～ 23:12+ CST (`Steps 000–915+`) · **Live Local Endpoint**: `http://127.0.0.1:8000/` (`Modbus TCP :15020`)  
> **GitHub Repository**: `https://github.com/benchen1981/PCW-SCADA-System-Final.git` (`main`)

---

## 目錄 / Table of Contents

- [Part I：繁體中文完整技術手冊](#part-i繁體中文完整技術手冊)
  - [1. 專案總覽與實測驗收總表](#1-專案總覽與實測驗收總表)
  - [2. 系統架構、拓撲與通訊規格](#2-系統架構拓撲與通訊規格)
  - [3. 完整 Prompts 與開發對話脈絡](#3-完整-prompts-與開發對話脈絡)
  - [4. 開發過程演進與 16 項核心 Debug 實證](#4-開發過程演進與-16-項核心-debug-實證)
  - [5. 完整安裝、啟動、測試與論文編譯執行步驟](#5-完整安裝啟動測試與論文編譯執行步驟)
  - [6. 使用方法與 REST / SSE / Modbus API 指南](#6-使用方法與-rest--sse--modbus-api-指南)
  - [7. 誠實揭露與研究範圍邊界](#7-誠實揭露與研究範圍邊界)
- [Part II: Complete English Technical Guide](#part-ii-complete-english-technical-guide)
  - [1. Executive Summary & Verified Benchmarks](#1-executive-summary--verified-benchmarks)
  - [2. System Architecture & Topology Specifications](#2-system-architecture--topology-specifications)
  - [3. Prompts, Development Timeline & Debug Traceability](#3-prompts-development-timeline--debug-traceability)
  - [4. Step-by-Step Build, Execution & Reproduction](#4-step-by-step-build-execution--reproduction)
  - [5. Interactive Usage, API Reference & Modbus Register Map](#5-interactive-usage-api-reference--modbus-register-map)
  - [6. Honest Scope & Limitations](#6-honest-scope--limitations)

---

# Part I：繁體中文完整技術手冊

## 1. 專案總覽與實測驗收總表

本專案依 [PCW_AI_Coder_Master_Prompt.md](../PCW_AI_Coder_Master_Prompt.md)（共 988 行）執行完整七階段研究與工程重構：於完整保留原始目錄 `Existing/` 未修改的前提下，徹底消除舊專案遺留之結構與演算法盲點，並以獲教授認可之 Excel 初版驗證工作簿（`PCW_T30_T20_T10_FINAL_ROLLBACK_THESIS_VERIFICATION.xlsx`）為基礎完整寫入論文第三章**偏移偵測（Drift Detection）與趨勢預測（Trend Forecast）**兩大核心簡明數學模型與五大【口試備註】（另附 [`thesis/oral_defense_notes.md`](./thesis/oral_defense_notes.md)），重寫並優化整套前後端 **Web SCADA v2.0** 系統、執行線上與本機超過 10 分鐘實時 Modbus 行為偏差實測、完成全廠 320 支測點 3,840 場受控試驗、更換論文全數 14 張圖與 5 張表，並編譯出符合送審與正式印刷規範之 36 頁 A4 碩士論文（`thesis/main.pdf`）。

| 驗收構面 | 實測成果與數據 | 核心實證檔案 |
|---|---|---|
| **全廠感測器規格** | **320 支感測器**（8 PCW × 10 Submain × 4 測點：**160 PT** + **80 FT** + **80 PDT**）；Group 4 PT 基準 `2.20 bar` | [`topology.py`](./system/backend/app/config/topology.py) |
| **單元與全端測試** | **`6 passed in 4.76s`**（拓撲與 CDAB 編碼、$N_{10}\ge\theta$ 與 L1–L7、Python/TS $<10^{-9}$ 對等、10 分鐘偏移、Modbus wire 讀寫、FastAPI API） | [`test_unified_system.py`](./system/tests/test_unified_system.py) |
| **Excel 參考一致率** | `PT-1` 480 列逐筆比對 **480 / 480（100.00%，最大誤差 `0.0`）** | [`EXCEL_PROGRAM_COMPARISON.csv`](./experiments/EXCEL_PROGRAM_COMPARISON.csv) |
| **1,920 場基準實驗** | **160 PT 測點 × 12 情境 = 1,920 場固定隨機種子試驗**（`seed = 2026111400 + run_id`）+ **12/12 邊界測試**；`Recall=100.0%` [95% Wilson CI: `99.70%–100.00%`], `Prec=88.70%` [95% CI: `86.97%–90.24%`], `F1=0.9401`, `Lead=10.60m` | [`BASELINE_COMPARISON.csv`](./experiments/BASELINE_COMPARISON.csv) |
| **突波防抖消融分析** | 40 PT × 12 = 480 場：`raw_onset=2` 使誤報率由 **25.62%** 降至 **6.88%** (`θ=2.0, F1=0.9831`) 與 **1.25%** (`θ=2.5, F1=0.9969`) | [`ablation_sensitivity.json`](./evidence/test_reports/ablation_sensitivity.json) |
| **Apple M5 執行效能** | 單點平均 **`13.54 µs`** (`73,380 ops/s`)、160 PT 批次 **`2.28 ms`**（320 批次 **`4.56 ms`**）、含 SQLite **`19.21 ms`**、Modbus FC03 **`264.2 µs`** | [`performance_benchmarks.json`](./evidence/test_reports/performance_benchmarks.json) |
| **全廠 >10 分鐘實測** | 本機 v2.0 (`11.35 min`) 注入慢速漂移與 `1.72 bar`，全廠 140 支測點依 L2 穩定鎖定 `T-30`、42 支 `EVENT`，SQLite `prediction_logs` 實存 **203,840 筆** | [`pcw_scada_11min.db`](./evidence/database_exports/pcw_scada_11min.db) |
| **Web UI v2.0 巡檢** | 無頭 Chrome `1440×900` 巡檢全 9 頁 + SSE `LIVE STREAM`：0 console/page error、`1.72 bar` 與 Pair Level 即時同步 | [`evidence/browser_screenshots/local_v2/`](./evidence/browser_screenshots/local_v2) |
| **密碼學完整性檢核** | 圖 9 白底黑字呈現 2026-11-14 實驗重跑終端摘要與 SHA-256 數位指紋；35 項核心交付檔案全數通過 `shasum -a 256 -c`（35/35 OK） | [`final_deliverables_sha256.txt`](./evidence/checksums/final_deliverables_sha256.txt) |
| **正式印刷論文** | **40 頁** 中興大學官方格式 A4 PDF（`6.67 MiB`、0 `Overfull \hbox`、15 圖 5 表全部正文引用、第二章 5 節擴充、第四章 1,920 場 160 PT 實證、第五章結論展望、12 筆 Crossref 實查書目）與可編輯 Word 稿（`.docx` / `.doc`） | [`thesis/main.pdf`](./thesis/main.pdf) · [`可編輯修改稿.docx`](./thesis/NCHU_Thesis_陳宥興_可編輯修改稿.docx) |

---

## 2. 系統架構、拓撲與通訊規格

### 2.1 五層軟硬體分層架構

1. **Data Source Layer (`system/backend/app/simulator/engine.py`)**：1 Hz 模擬取樣並整合故障與行為偏差場景（`NONE`, `DRIFT`, `STEP`, `SPIKE`, `BAD_QUALITY`, `COMM_LOSS`）。*規劃未接入：晶圓廠實體 PLC / PT*。
2. **Data Management Layer (`historian/store.py` & `database/sqlite_repo.py`)**：各測點獨立維護 >= 70 分鐘記憶體因果環形緩衝（僅使用 `GOOD` 樣本 1 分鐘聚合），並寫入 SQLite WAL 三大資料表：`historian_points`、`prediction_logs`、`alarm_logs`。*規劃未接入：廠務 MS-SQL Historian*。
3. **Inference & Alarm Layer (`engine/drift_forecast.py` & `engine/alarm_engine.py` & `DriftForecastEngine.ts`)**：嚴格 Past-Only 70 分鐘因果視窗 ($[t-70, t-10)$ vs $[t-10, t)$)、修正後方向性異常密度比 $N_{10} \ge \theta$、五分鐘局部均差斜率、OLS 95% 預測區間與閉式 TTL，搭配 **L1–L7 工業硬化**（含修正後 L2 持續水準偏移閘門 `|mean(C)-BaseAvg60| >= g%*(HI-LO)` 與可調 `raw_onset = 1/2`）及 ISA-18.2 警報狀態機。
4. **Protocol & Gateway Layer (`main.py` & `modbus/tcp_server.py`)**：FastAPI REST API (`/api/*`)、原生 Server-Sent Events 即時推播 (`GET /api/stream`)、WebSocket 端點 (`/ws/stream`)，以及純 Python 非同步 **Modbus/TCP Server (Port `15020`, FC03/06/16, IEEE-754 FLOAT32 CDAB Word-Swap, `40001..40639`)**。
5. **HMI Presentation Layer (`system/frontend/src/`)**：完全刪除舊版複製冗餘檔後以 React 19 + TypeScript 重寫之控制室 UI：
   - `1. Plant Overview`（KPI Strip + 8 迴路健康總覽）
   - `2. Live Sensor Data`（SVG 閉迴路 P&ID 圖 + 320 測點矩陣）
   - `3. Historian Trend`（1-min 特徵曲線 + SQLite `prediction_logs` 稽核查詢）
   - `4. Live Trend`（1 Hz 即時示波器 + OLS 95% PI 投影）
   - `5. Alarm Center`（Engineering / Predictive Drift / Quality 三軌分流 + CSV 匯出）
   - `6. System Prediction`（Sensor 320 / Pair 80 / SQLite Log + 右側預測圓錐圖抽屜）
   - `7. Prediction Tuning`（θ / g% / K_hold / `raw_onset=1/2` 消融調參與單點覆寫）
   - `8. Modbus Simulator`（一鍵實測場景預設按鈕 + 行為偏差注入 + CDAB Hex 監視器）
   - `9. Prediction Model Info`（模型公式、L1–L7 與實機基準總表）

### 2.2 晶圓廠雙棟拓撲與 PCW 系統架構（論文第 1.1.1 節與第 1.1.3 節）

- **雙單體建築與連通管廊**：全廠由 FAB 棟（生產廠房，B2F～6F）與 CUB 棟（中央廠務大樓，B2F～6F）構成。地上以**大型鋼構管廊空橋（Pipe Bridge）** 連接（輸送熱水回水主管、雙向備援水管與線槽）；地下室（B1F～B2F）全面開放共通，作為供水主管與重型能源管溝。
- **無塵室生產層垂直配置**：
  - **5F Cleanroom**：配置 PCW01～PCW04 迴路（微影 EUV/ArFi、乾式蝕刻、高溫擴散），壓力公差極嚴苛（±0.05 bar）。
  - **3F Cleanroom**：配置 PCW05～PCW08 迴路（CVD、PVD、CMP、濕式清洗），承載重散熱與大流量沖洗。
  - **CUB 棟**：1F 主冷水機組（數千 RT）、B1F 一次板式換熱器（PHE）、微米濾網、脫氣器與主循環泵群。
- **PCW 四步驟閉迴路循環程序**：
  $\text{CUB 供應水 (22°C)} \to \text{FAB B1F 增壓} \to \text{垂直立管 (Risers) 衝 3F/5F} \to \text{Submain 機台盤管吸熱} \to \text{回水集水管} \to \text{空橋熱水回流 CUB} \to \text{脫氣與微米濾網} \to \text{一次板換降溫} \to \text{混入冰水再循環}$。

---

## 3. 完整 Prompts 與開發對話脈絡

會話自 `2026-11-11 06:56:50+08:00` 起歷經 `915+` 步驟（完整逐階實錄見 **[`prompt 01-915.md`](./prompt%2001-915.md)**）：

- **Step 000**：依 [`PCW_AI_Coder_Master_Prompt.md`](../PCW_AI_Coder_Master_Prompt.md) 提出 6 項核心需求（分析與整套程式改寫、自動連已部署網頁測試驗證、逐點執行與留存預警紀錄、調整 Modbus 基準拉長 >10 分鐘實測、論文圖表截圖全替換、論文最佳化至印刷送審水準）。
- **Step 365 / 599 / 697 / 819 / 914**：要求生成包含所有 prompt、執行步驟、系統架構、開發過程、debug 紀錄及使用方法之中英文 `README.md`，並持續更新輸出 `prompt xx-xxx.md` 與 `debug xx-xxx.md`。
- **Step 405**：要求立即啟動本機 `http://127.0.0.1:8000/` 服務。
- **Step 424**：要求「整套專案程式改寫、優化，而非複製舊專案局部修補」$\implies$ 促成完整刪除 22 份舊專案冗餘檔、全面重寫前後端 9 大頁面、實作 SSE `LIVE STREAM` 推播與 `rawOnset` 控制面板之 v2.0 深度改造。
- **Step 619**：要求對 `http://127.0.0.1:8000/` 重跑自動瀏覽器實測與全測點 >10 分鐘行為偏差驗證（達成 `11.35 min`、`320/320` 測點全數執行預警／事件、SQLite `203,840` 筆紀錄）並更新論文圖表截圖。
- **Step 721**：指定以初版獲教授認可之 [`PCW_T30_T20_T10_FINAL_ROLLBACK_THESIS_VERIFICATION.xlsx`](../Existing/PCW_T30_T20_T10_FINAL_ROLLBACK_THESIS_VERIFICATION.xlsx) 為程式開發基礎，逐欄解析其公式並於論文第三章清楚定義**偏移偵測（Drift Detection）**與**趨勢預測（Trend Forecast）**兩大核心問題之數學公式與程式對照表（`表 3`）。
- **Step 843 / 876**：要求將論文第三章艱澀數學式簡化為直覺好記形式、增補五大「【口試備註】」與口試 Q&A 小抄 [oral_defense_notes.md](./thesis/oral_defense_notes.md)，並重新生成 [main.tex](./thesis/main.tex) 與 36 頁印刷級 [main.pdf](./thesis/main.pdf)。
- **Step 893**：指定將完整新專案推送至 GitHub `https://github.com/benchen1981/PCW-SCADA-System-Final.git`（建立 `.gitignore` 並成功推送 `main` 分支）。
- **Step 584 / 689 / 805**：逐輪檢查計畫並確認所有任務均已落實。

---

## 4. 開發過程演進與 16 項核心 Debug 實證

完整九大開發階段與 **16 項真實除錯（`Debug 01-001` ～ `01-016`）** 見 [`prompt 01-915.md`](./prompt%2001-915.md) 與 **[`debug 01-016.md`](./debug%2001-016.md)**，關鍵除錯摘要如下：

1. **演算法核心修復 (`01-003`, `01-005`, `01-007`)**：修正 `N10 > theta` 結構不可達為 `N10 >= theta`；於 L2 加入持續水準偏移閘門 `|mean(C)-BaseAvg60| >= g%*(HI-LO)` 解決 >10 分鐘斜率歸零回落 `NORMAL` 問題；同步設定／注入與 Alarm/Prediction 狀態消除 `1.72 bar` 矛盾。
2. **跨語言與通訊端口修復 (`01-004`, `01-006`, `01-012`)**：改寫 TS 建構子欄位通過 Node v24 `--experimental-strip-types` 原生 `<1e-9` 對等測試；避開外部佔用 Port 5020 預設改用 `15020`；隔離 pytest 測試埠為 `15029` 與獨立暫存 DB 確保在背景系統運行同時 `pytest` 穩定 `6 passed`。
3. **文獻與消融實驗除錯 (`01-002`, `01-008`, `01-009`)**：透過 Crossref API 剔除 6 筆虛構或錯配 DOI；實作 `raw_onset=2` 消融將突波誤報率由 `25.62%` 降至 `6.88% / 1.25%`；調整圖表邊距重產 300 DPI PNG。
4. **論文口試排版與系統／版控發布除錯 (`01-010`, `01-011`, `01-013`, `01-014`, `01-015`, `01-016`)**：消除 `Overfull \hbox` 與 18 處 `\t`+`extbf{` 字元損毀；刪除 22 份舊版複製冗餘檔並改採原生 SSE `GET /api/stream` 解決 WebSocket 握手報錯 (`Console errors: 0`)；修復 `DP` (`PDT`) 計數與總覽 KPI 顯示；解決 Excel 雙模型與口試簡化版論文公式溢位（**36 頁 `main.pdf`，0 Overfull/Undefined 警告**）；透過 `.gitignore` 隔離運行庫與 `node_modules` 後順利推送至 GitHub。

---

## 5. 完整安裝、啟動、測試與論文編譯執行步驟

### 步驟 1：建置 v2.0 前端並啟動全端背景服務（Web `:8000` + Modbus `:15020`）
```bash
# Build React 19 + TypeScript v2.0 frontend bundle
cd "PCW_SCADA_Final_Project/system/frontend"
npm install
npx tsc --noEmit
npm run build

# Start FastAPI + SSE + async Modbus/TCP Server (:15020)
cd "../backend"
PCW_MODBUS_PORT=15020 PYTHONPATH=. python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 步驟 2：執行單元、協議與雙語言對等測試（可在伺服器運行同時執行）
```bash
cd "PCW_SCADA_Final_Project"
PYTHONPATH=system/backend python3 -m pytest -v system/tests/test_unified_system.py
# Expected: 6 passed
```

### 步驟 3：重現 Excel 比對、3,840 場基準實驗、壓測與消融分析
```bash
cd "PCW_SCADA_Final_Project"
PYTHONPATH=.:system/backend python3 experiments/run_full_experiments.py
PYTHONPATH=.:system/backend python3 experiments/benchmark_performance.py
PYTHONPATH=.:system/backend python3 experiments/ablation_and_sensitivity.py
```

### 步驟 4：重現雙邊 >10 分鐘無頭 Chrome 實測與製圖
```bash
# Confirm :8000 is running, then execute automated 11.5-minute scripts:
node "PCW_SCADA_Final_Project/scripts/verify_local_rewritten_and_11min.mjs"
node "PCW_SCADA_Final_Project/scripts/verify_deployed_and_10min.mjs"

# Regenerate 300 DPI thesis charts
cd "PCW_SCADA_Final_Project"
PYTHONPATH=.:system/backend python3 scripts/generate_all_figures.py
```

### 步驟 5：編譯 A4 正式印刷品質 PDF 論文、匯出 Word 檔與核對校驗碼
```bash
cd "PCW_SCADA_Final_Project/thesis"
tectonic main.tex

# 匯出官方樣式可編輯 Word 稿（.docx 與 .doc）
cd ".."
python3 scripts/build_clean_docx.py

# 驗證全廠 35 份交付檔案 SHA-256
shasum -a 256 -c evidence/checksums/final_deliverables_sha256.txt
```

---

## 6. 使用方法與 REST / SSE / Modbus API 指南

1. **Web 介面操作流程**：開啟 http://127.0.0.1:8000/ ，確認左上角呈現綠色 **`LIVE STREAM`**。
   - 前往 **8. Modbus Simulator**：點選 **`1.72 bar State Consistency Probe (SM01.PTS)`** 後切換至 **6. System Prediction**，即可實測 Alarm Center (`HIGH`) 與 System Prediction (`EVENT`, Risk=`100`) 與右側 OLS 95% PI 圓錐圖即時同步。
   - 點選 **`>10-min Behavioral Deviation (All 160 PT)`**：可同步將全廠 160 支 PT 設為限值內供／回水基準偏移並疊加慢速漂移，持續觀察超過 10 分鐘後仍由 L2 水準偏移閘門維持預警，並於 **3. Historian Trend $\to$ SQLite Prediction Logs** 查詢每點記錄。
   - 前往 **7. Prediction Tuning**：切換 `raw_onset = 2 (2-min Debounce)` 即時驗證突波防抖抑制。
2. **核心 API 端點**：`GET /api/health`、`GET /api/snapshot`、`GET /api/stream` (SSE)、`POST /api/simulator/config`、`POST /api/simulator/fault`、`POST /api/simulator/control`、`POST /api/prediction/tuning`、`GET /api/predictions/logs`。
3. **Modbus/TCP (Port `15020`, Unit ID `1`, FLOAT32 CDAB Word-Swap)**：Holding Registers `40001..40639`，每組 Submain 佔 8 個暫存器（`+0` `.PTS`、`+2` `.FT`、`+4` `.PTR`、`+6` `.PDT`）。

---

## 7. 誠實揭露與研究範圍邊界

1. 除既有 Excel `PT-1` 480 分鐘歷史序列外，其餘 3,840 場基準測試與 11+ 分鐘長時序實驗均採用受控模擬與故障注入序列；尚未接入晶圓廠實體 PLC、現場 MS-SQL Historian 與 OPC-UA 回寫系統。
2. 線上 `https://pcw-scada-system.vercel.app/` 因無遠端部署授權而保留原始建置供對照驗證。
3. 本機 `203,840` 筆 SQLite **11.35 分鐘**全廠 320 測點長時實測（`320 / 320` 執行預警／事件）係於最終 v2.0 系統上通過 Chrome `LIVE STREAM` 實時執行完畢；`160 PT · 80 FT · 80 PDT` 標籤顯示與 `test_unified_system.py`（`6 passed in 4.38s`）均於最終編輯後通過檢驗。

---

# Part II: Complete English Technical Guide

## 1. Executive Summary & Verified Benchmarks

Executed in strict compliance with [PCW_AI_Coder_Master_Prompt.md](../PCW_AI_Coder_Master_Prompt.md) while keeping `Existing/` completely untouched, `PCW_SCADA_Final_Project/` builds upon the advisor-approved Excel Reference Model (`PCW_T30_T20_T10_FINAL_ROLLBACK_THESIS_VERIFICATION.xlsx`) to deliver a ground-up **full-stack Web SCADA v2.0** re-engineering (eliminating 22 legacy copy-paste files, adding native Server-Sent Events `GET /api/stream`, an async Python Modbus/TCP server on Port `15020`, and SQLite WAL persistence in `prediction_logs`), formalizes both core thesis mathematical models (**Drift Detection** and **Trend Forecast** including `N10 >= theta` & sustained L2 level-shift gating), performs automated headless Chrome testing on both the deployed Vercel app (`11.12 min`) and rewritten local stack (`11.28 min` + `11.35 min` v2.0 9-page SSE patrol), evaluates 320 sensors across 3,840 controlled trials, replaces all thesis figures/screenshots (14 figures, 5 tables), and compiles a print-ready 36-page A4 thesis ([`thesis/main.pdf`](./thesis/main.pdf)) with oral-defense annotations and a standalone Q&A cheat sheet ([`oral_defense_notes.md`](./thesis/oral_defense_notes.md)).

- **Topology Verified**: **320 Sensors** across 8 loops (`PCW01`–`PCW08`) × 10 Submain pairs = **160 PT** + **80 FT** + **80 PDT**; Group 4 PT baseline = `2.20 bar`; FLOAT32 CDAB registers `40001..40639`.
- **Unit & Integration Suite**: **`6 passed in 4.76s`** ([`test_unified_system.py`](./system/tests/test_unified_system.py)) — isolated test DB and port `15029` so tests run cleanly alongside the live `15020`/`8000` daemon.
- **Excel Parity**: `PT-1` 480-row comparison achieved **480 / 480 exact matches** (`max_abs_diff = 0.0`, `tol = 1e-9`). Python vs. TypeScript parity `< 1e-9`.
- **3,840-Trial Benchmark (`160 PT` 1,920-trial subset)**: `Recall = 100.0%` (95% Wilson CI: `99.70%–100.00%`), `Precision = 88.77%`, `F1 = 0.9405`, `FAR = 25.31%`, `Mean Lead = 10.58 min` (`Naive OLS k=10`: `F1 = 0.9412`).
- **Transient Spike Ablation (`40 PT × 12 = 480 trials`)**: Adding `raw_onset = 2` consecutive confirmation before L6 latch cuts FAR from **`25.62%` down to `6.88%`** (`theta=2.0, F1=0.9831`) and **`1.25%`** (`theta=2.5, F1=0.9969`).
- **Apple M5 Latency**: Single `evaluate_window` mean **`14.53 µs`** (`68,352 ops/s`); 320-sensor batch **`4.68 ms`**; 320-sensor batch + SQLite insert **`20.54 ms`**; Modbus TCP `FC03` (20 regs) **`271.4 µs`**.
- **Real-Time >10-Minute Runs**: Deployed Vercel (`11.12 min`) captured the `1.72 bar` UI inconsistency defect and `t = 10.48 min` premature `NORMAL` reset (`N10 = 3.53`); local rewritten v2.0 stack (`11.35 min`) synced `HIGH + EVENT` immediately, executed predictions across **320 / 320** sensors (sustaining `140 T-30 + 42 EVENT` past 10 minutes), and logged **`203,840`** rows across all 320 tags in [`pcw_scada_11min.db`](./evidence/database_exports/pcw_scada_11min.db).

---

## 2. System Architecture & Topology Specifications

1. **Data Source Layer**: 1 Hz simulator with injectable behavioral deviation scenarios (`NONE`, `DRIFT`, `STEP`, `SPIKE`, `BAD_QUALITY`, `COMM_LOSS`). *Planned/unattached: physical fab PLC & field transmitters.*
2. **Data Management Layer**: Per-tag causal 1-minute ring buffers (`HistorianStore`) + SQLite WAL tables (`historian_points`, `prediction_logs`, `alarm_logs`). *Planned/unattached: production MS-SQL Historian.*
3. **Inference & Alarm Layer**: Unified V1 engine (`evaluate_window` + `DriftForecastEngine`) featuring Past-Only 70-min windowing, `N10 >= theta`, 5-min centered mean-difference slope, OLS 95% Student-$t$ prediction bands, closed-form TTL, sustained level-shift L2 gate, L6 hysteresis, configurable `raw_onset` (`1|2`), Pair Level diagnostics (`80` Submains), and ISA-18.2 alarm state machine.
4. **Gateway & Protocol Layer**: FastAPI (`app/main.py`) providing REST endpoints, native SSE (`GET /api/stream`), WebSocket (`/ws/stream`), and pure-Python async Modbus/TCP Server (`Port 15020`, `FC03/06/16`, FLOAT32 CDAB). *Planned/unattached: OPC-UA / plant SCADA tag gateway.*
5. **HMI Presentation Layer**: Clean-slate React 19 + TypeScript control-room UI across 9 views (KPI plant overview, SVG P&ID loop schematic, historian & SQLite audit browser, live oscilloscope with OLS 95% PI preview, ISA-18.2 alarm workbench, prediction + 95% PI cone drawer + Pair diagnostics, tuning & `raw_onset` panel, Modbus preset injector + CDAB hex viewer, and model specification page).

---

## 3. Prompts, Development Timeline & Debug Traceability

- Full chronological session prompts & architecture log (`Steps 000–915+`): **[`prompt 01-915.md`](./prompt%2001-915.md)**
- Full 16-episode debugging log (`Debug 01-001` – `01-016`): **[`debug 01-016.md`](./debug%2001-016.md)**
- **GitHub Repository**: `https://github.com/benchen1981/PCW-SCADA-System-Final.git` (published on `main`)
- Key fixes verified end-to-end: (1) `N10 >= theta` symmetric-noise reachability fix; (2) L2 sustained level-shift gate preventing >10-min `slope -> 0` reset; (3) immediate prediction/alarm state synchronization at `1.72 bar`; (4) Node v24 constructor field refactor for native TypeScript parity (`< 1e-9`); (5) Modbus TCP port isolation (`15020` live / `15029` pytest); (6) purging 6 invalid/mismatched BibTeX DOIs via Crossref; (7) removing 22 copied legacy files and replacing failing WebSocket polling with zero-dependency SSE `LIVE STREAM` (`0` Chrome console/page errors); (8) fixing `DP` (`PDT`) type filtering, 18 bash-corrupted `\textbf{` tokens, caption sync (`11.35 min`), adding Excel Rollback formula mapping + simplified oral-defense Drift Detection / Trend Forecast equations & five defense notes ([`oral_defense_notes.md`](./thesis/oral_defense_notes.md)), eliminating all LaTeX overflow warnings (`36 pages, 0 warnings`), and publishing cleanly to GitHub via `.gitignore`.

---

## 4. Step-by-Step Build, Execution & Reproduction

```bash
# 1. Build v2.0 frontend and launch FastAPI + SSE + Modbus TCP (:15020)
cd "PCW_SCADA_Final_Project/system/frontend"
npm install && npx tsc --noEmit && npm run build
cd "../backend"
PCW_MODBUS_PORT=15020 PYTHONPATH=. python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 2. Run isolated unit, cross-language parity, Modbus & FastAPI integration suite
cd "PCW_SCADA_Final_Project"
PYTHONPATH=system/backend python3 -m pytest -v system/tests/test_unified_system.py

# 3. Reproduce Excel parity, 3,840-trial benchmark, latency suite & spike ablation
PYTHONPATH=.:system/backend python3 experiments/run_full_experiments.py
PYTHONPATH=.:system/backend python3 experiments/benchmark_performance.py
PYTHONPATH=.:system/backend python3 experiments/ablation_and_sensitivity.py

# 4. Run automated 11.5-min Chrome verifications (while :8000 is running) & regenerate charts
node scripts/verify_local_rewritten_and_11min.mjs
node scripts/verify_deployed_and_10min.mjs
PYTHONPATH=.:system/backend python3 scripts/generate_all_figures.py

# 5. Recompile print-ready A4 PDF thesis & verify SHA-256 deliverables manifest
cd thesis && tectonic main.tex && cd ..
shasum -a 256 -c evidence/checksums/final_deliverables_sha256.txt
```

---

## 5. Interactive Usage, API Reference & Modbus Register Map

- **UI Quick Walkthrough (`http://127.0.0.1:8000/`)**: Verify green **`LIVE STREAM`** in the top bar. Open **8. Modbus Simulator** and click **`1.72 bar State Consistency Probe (SM01.PTS)`** or **`>10-min Behavioral Deviation (All 160 PT)`**, then inspect **6. System Prediction** (click any row to view its interactive OLS 95% PI forecast cone SVG or switch to `Pair Level (80)` / `SQLite Execution Log`), and toggle **`raw_onset = 2`** on **7. Prediction Tuning**.
- **Core Endpoints**: `GET /api/health`, `GET /api/snapshot`, `GET /api/stream` (SSE), `POST /api/simulator/config`, `POST /api/simulator/fault`, `POST /api/simulator/control`, `POST /api/prediction/tuning`, `GET /api/predictions/logs`.
- **Modbus Mapping (`127.0.0.1:15020`, FLOAT32 CDAB)**: Holding Registers `40001..40639` (640 registers / 320 tags; 8-register stride per Submain: `+0 .PTS`, `+2 .FT`, `+4 .PTR`, `+6 .PDT`).

---

## 6. Honest Scope & Limitations

1. Except for the 480-row `PT-1` Excel reference series, all 3,840 benchmark trials and 11+ minute real-time runs use controlled simulator/fault-injection sequences and must not be represented as physical fab production telemetry.
2. Live deployment `https://pcw-scada-system.vercel.app/` remains unmodified due to absent remote deployment credentials and serves as the audited legacy baseline comparison target.
3. The `203,840`-row SQLite **11.35-min** all-320-sensor verification (`320 / 320` sensors executing prediction/event states) ran live on the re-engineered v2.0 `LIVE STREAM` SSE stack with zero Chrome console/page errors; post-edit checks (`tsc`, `vite build`, `pytest` 6/6, and thesis PDF recompilation) all passed after the final code edit.
