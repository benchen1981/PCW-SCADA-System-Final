# 詳細開發過程與 Prompt 對話紀錄（Steps 000–915+ / `prompt 01-915.md`）

> **專案名稱**：半導體廠務 PCW（Process Cooling Water）統計式早期預警與全端 Web SCADA 系統重構暨論文驗證（v2.0）  
> **遠端儲存庫**：`https://github.com/benchen1981/PCW-SCADA-System-Final.git`（分支 `main`）  
> **執行日期與跨度**：2026-11-11（06:56:50 CST ～ 23:12+ CST · Session Steps `000`–`915+`）  
> **實測主機**：Apple M5（10 Cores, 16 GiB RAM, macOS 26.7.3 arm64）、Python 3.9.6、Node.js v24.14.1、Google Chrome 157.0.8103.40、Tectonic 0.17.0  
> **關聯檔案**：[README.md](./README.md) | [debug 01-016.md](./debug%2001-016.md) | [oral_defense_notes.md](./thesis/oral_defense_notes.md) | [PCW_AI_Coder_Master_Prompt.md](../PCW_AI_Coder_Master_Prompt.md)

---

## 一、 完整使用者 Prompt 對話紀錄（Verbatim User Inputs, Steps 000–914）

### Prompt 1 — Step 000（2026-11-11 06:56:50+08:00）：主任務與六大核心需求
```text
依 prompt@[/Users/benchen1981/Downloads/Web SCADA Final 20261111/PCW_AI_Coder_Master_Prompt.md] 要求執行，並依遵循下述要求進行：
1. 分析此專案包含論文，改寫"整套專案系統程式"
2. 自動連至已部署網頁系統，自動完成所有測試、驗証
3. 每個sensor預測警報必需確實執行並留記錄
4. 調整Modbus 基準使其行為偏差，時間至少拉長至10分鐘以上，以達到與真實世界完整匹配不做假
5. 論文所有系統截圖和圖表全部更換為最新系統狀態、實驗過程、實驗証明
6. 論文優化至可提交審查及正式印刷要求
```

### Prompt 2 — Step 365（2026-11-11 20:25:58+08:00）：文件與過程紀錄產出
```text
生成詳細中英文readme.md, 包含所有prompt、執行步驟、系統架構、開發過程、debug記錄及使用方法
詳細開發過程對話紀錄(prompt)，包含專案架構輸出為prompt xx-xxx.md
詳細除錯過程對話紀錄(prompt)輸出為debug xx-xxx.md
生成詳細readme.md, 包含執行步驟、系統架構、開發過程、prompt
```

### Prompt 3 — Step 405（2026-11-11 20:30:04+08:00）：本機伺服器啟動指示
```text
本機網頁無法開啟http://127.0.0.1:8000/，立即啟動
```

### Prompt 4 — Step 424（2026-11-11 20:34:24+08:00）：整套專案架構與程式碼徹底重構要求
```text
我要的是「整套專案程式改寫、優化」，不是覆製重作一份一樣的專案
```

### Prompt 5 — Step 584（2026-11-11 20:50:19+08:00）：第一輪計畫落實盤點
```text
所有任務都完成了嗎？
檢查計劃並確認所有項目都已落實。
```

### Prompt 6 — Step 599（2026-11-11 20:50:28+08:00）：中英文文件與過程日誌更新（第一輪）
```text
生成詳細中英文readme.md, 包含所有prompt、執行步驟、系統架構、開發過程、debug記錄及使用方法
詳細開發過程對話紀錄(prompt)，包含專案架構輸出為prompt xx-xxx.md
詳細除錯過程對話紀錄(prompt)輸出為debug xx-xxx.md
生成詳細readme.md, 包含執行步驟、系統架構、開發過程、prompt
```

### Prompt 7 — Step 619（2026-11-11 21:05:19+08:00）：對 v2.0 系統重跑 >10 分鐘實時全測與論文更新
```text
依prompt要求執行，並依遵循下述要求進行
1.自動連至已部署網頁系統，自動完成所有測試、驗証
2.網址：http://127.0.0.1:8000/
3.每個sensor預測警報必需確實執行並留記錄
4.調整Modbus 基準使其行為偏差，時間至少拉長至10分鐘以上，以達到與真實世界完整匹配不做假
5.論文所有系統截圖和圖表全部更換為最新系統狀態、實驗過程、實驗証明
```

### Prompt 8 — Step 689（2026-11-11 22:21:53+08:00）：第二輪計畫核對
```text
所有任務都完成了嗎？
檢查計劃並確認所有項目都已落實。
```

### Prompt 9 — Step 697（2026-11-11 22:22:00+08:00）：v2.0 實測後中英文文件同步要求
```text
生成詳細中英文readme.md, 包含所有prompt、執行步驟、系統架構、開發過程、debug記錄及使用方法
詳細開發過程對話紀錄(prompt)，包含專案架構輸出為prompt xx-xxx.md
詳細除錯過程對話紀錄(prompt)輸出為debug xx-xxx.md
生成詳細readme.md, 包含執行步驟、系統架構、開發過程、prompt
```

### Prompt 10 — Step 721（2026-11-11 22:24:03+08:00）：Excel 初版驗證模型數學分析與雙核心模型帶入論文
```text
立即執行
1.這份excel@[/Users/benchen1981/Downloads/Web SCADA Final 20261111/Existing/PCW_T30_T20_T10_FINAL_ROLLBACK_THESIS_VERIFICATION.xlsx] 為初版模型開發驗証，其設計方向及預測準確率已得到教授認可，後續以此excel模型為程式開發基礎，立即將模型數學公式分析及帶入論文
2.論文要解決的問題是偏移偵測 (Drift Detection)和趨勢預測 (Forecast)，這二個模型的數學公式要交代清楚
```

### Prompt 11 — Step 805（2026-11-11 22:36:08+08:00）：第三輪計畫核對
```text
所有任務都完成了嗎？
檢查計劃並確認所有項目都已落實。
```

### Prompt 12 — Step 819（2026-11-11 22:36:15+08:00）：雙模型入論文後中英文文件更新
```text
生成詳細中英文readme.md, 包含所有prompt、執行步驟、系統架構、開發過程、debug記錄及使用方法
詳細開發過程對話紀錄(prompt)，包含專案架構輸出為prompt xx-xxx.md 
詳細除錯過程對話紀錄(prompt)輸出為debug xx-xxx.md
生成詳細readme.md, 包含執行步驟、系統架構、開發過程、prompt
```

### Prompt 13 — Step 843（2026-11-11 22:40:56+08:00）：口試數學式簡化與新增口試應答備註
```text
論文中的數學式太困難，在口試時，我無法記住，一定會被教授問倒，立簡化數學式及新增備註，以利我順利進行口試及回問題
```

### Prompt 14 — Step 876（2026-11-11 23:03:53+08:00）：論文 TeX 與 PDF 重新生成
```text
論文tex和pdf 檔案再次重新生成
```

### Prompt 15 — Step 893（2026-11-11 23:09:05+08:00）：推送新專案至 GitHub
```text
將新專案推送至github
https://github.com/benchen1981/PCW-SCADA-System-Final.git
```

### Prompt 16 — Step 914（2026-11-11 23:12:02+08:00）：最終全週期中英文 README 與 Prompt / Debug 實錄更新
```text
生成詳細中英文readme.md, 包含所有prompt、執行步驟、系統架構、開發過程、debug記錄及使用方法
詳細開發過程對話紀錄(prompt)，包含專案架構輸出為prompt xx-xxx.md 
詳細除錯過程對話紀錄(prompt)輸出為debug xx-xxx.md
生成詳細readme.md, 包含執行步驟、系統架構、開發過程、prompt
```

**主研究規範（Master Prompt §0–§14）**：共 988 行 ([PCW_AI_Coder_Master_Prompt.md](../PCW_AI_Coder_Master_Prompt.md))，核心禁令包含不得造假數據、不得虛構 DOI、不得混淆模擬與工廠現場資料、每支感測器至少 10 次有效測試，以及嚴格遵守 Phase 1 至 Phase 7 工程序列。

---

## 二、 完整重構後專案系統架構（Project & Software Architecture）

### 2.1 五層式軟硬體分層架構

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Layer 5: HMI Presentation Layer (React 19 + TypeScript v2.0) [已徹底重寫驗證]│
│  ├─ 1. Plant Overview         (5 卡全廠 KPI + 8 迴路 PTS/FT/ΔP 即時面板)     │
│  ├─ 2. Live Sensor Data       (SVG 閉迴路 Submain P&ID 圖 + 320 測點矩陣)    │
│  ├─ 3. Historian Trend        (1-min 歷史特徵曲線 + SQLite logs 互動查詢)     │
│  ├─ 4. Live Trend             (1 Hz 即時示波器 + OLS 95% 預測區間投影預覽)    │
│  ├─ 5. Alarm Center           (ISA-18.2: Engineering vs DRIFT vs ERROR 分流) │
│  ├─ 6. System Prediction      (Sensor 320 / Pair 80 / SQLite Log + 預測錐面圖)│
│  ├─ 7. Prediction Tuning      (θ / g% / K_hold / raw_onset=1 or 2 消融切換)  │
│  ├─ 8. Modbus Simulator       (一鍵驗證場景 + 自訂故障注入 + CDAB Hex 監視器)│
│  └─ 9. Prediction Model Info  (Unified V1 公式、L1–L7 與實機基準總表)         │
└───────────────────────────────────────┬──────────────────────────────────────┘
                                        │ SSE Push (GET /api/stream) + REST (/api/*)
┌───────────────────────────────────────▼──────────────────────────────────────┐
│ Layer 4: Integration & Protocol Gateway Layer [本機已實作；廠務 OPC-UA 規劃中]│
│  ├─ EventSource SSE 全廠快照推播 + Event/Alarm 即時同步重算                  │
│  └─ 非同步 Modbus/TCP Server (Port 15020, FC03/06/16, FLOAT32 CDAB 40001..639)│
└───────────────────────────────────────┬──────────────────────────────────────┘
                                        │ Python Evaluate ↔ TypeScript Parity (<1e-9)
┌───────────────────────────────────────▼──────────────────────────────────────┐
│ Layer 3: Inference & Alarm Engine Layer [承襲 Excel 模型並通過雙語言對等驗證] │
│  ├─ Drift Detection (Excel BaseAvg60/M60/M10/N10 -> d_i, N10>=θ, L2 水準偏移) │
│  ├─ Trend Forecast  (Excel Prev5/Recent5/Slope_XL -> 雙向斜率/OLS PI/TTL/L3–7)│
│  └─ Causal Isolation (Past-Only 推論 vs 離線 Actual_T30/T20/T10 Ground Truth)│
└───────────────────────────────────────┬──────────────────────────────────────┘
                                        │ SQLite WAL & 1-min GOOD Aggregation
┌───────────────────────────────────────▼──────────────────────────────────────┐
│ Layer 2: Data Management Layer [本機 SQLite 已實作；廠務 MS-SQL 規劃中]      │
│  ├─ In-memory 1-min Ring Buffer (各測點獨立保留 >= 70 分鐘因果窗口)          │
│  └─ SQLite WAL (`pcw_scada.db`): historian_points / prediction_logs / alarms │
└───────────────────────────────────────┬──────────────────────────────────────┘
                                        │ 1 Hz Tick / Modbus Register Bank Write
┌───────────────────────────────────────▼──────────────────────────────────────┐
│ Layer 1: Data Source Layer [受控模擬器已實作；實體晶圓廠 PLC 未接入]         │
│  ├─ 8 PCW × 10 Submains = 80 對配對，共 320 測點 (160 PT + 80 FT + 80 PDT)    │
│  └─ 情境模擬器 (NORMAL / DRIFT / STEP / SPIKE / BAD_QUALITY / COMM_LOSS)     │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 交付專案目錄結構（`PCW_SCADA_Final_Project/`）

```text
PCW_SCADA_Final_Project/
├── .gitignore                             # 排除 node_modules / __pycache__ / .db-wal / TeX 中繼檔
├── README.md                              # 完整中英文雙語技術與使用說明手冊
├── prompt 01-915.md                       # 完整開發過程對話與系統架構紀錄 (本文件)
├── debug 01-016.md                        # 16 項完整除錯軌跡與根因修復實證
├── audit/                                 # Phase 1 盤點與基線報告 (6 份文件)
├── research/                              # Phase 2 數學定義、偽程式碼與防洩漏稽核 (5 份)
├── system/                                # 徹底重構後全端 Web SCADA v2.0 程式碼
│   ├── backend/app/                       # FastAPI + SSE + Modbus/TCP Server + SQLite + Unified V1
│   ├── backend/data/                      # 本機運行資料庫 (不入版控)
│   ├── frontend/src/                      # 零舊碼殘留之 React 19 + TypeScript + Vite 2.0 UI
│   └── tests/test_unified_system.py       # 6 項獨立隔離整合／協議／雙語言對等測試
├── experiments/                           # 3,840 場對照、480 筆 Excel 比對、壓測與消融腳本/CSV
├── scripts/                               # Chrome/Puppeteer 11m 驗證與 300 DPI 製圖腳本
├── figures/ & tables/                     # 高解析圖表與表格 CSV
├── evidence/                              # raw_inputs, simulator_settings, screenshots, logs, db, checksums
├── reports/                               # TECHNICAL_AUDIT / EXPERIMENT_FINAL / THESIS_REVISION 三大報告
└── thesis/                                # 36 頁 A4 送審與口試印刷版 (main.tex / main.pdf / oral_defense_notes.md)
```

---

## 三、 依時間軸全九階段開發與重構實錄（Steps 000–915+）

1. **Stage 1 · Phase 1 環境探測與既有專案稽核（Steps `001`–`103` · 06:56–07:00）**
   - 產出 `baseline_probe.txt`、`baseline_sha256.txt`、Phase 1 六份稽核文件及 `citation_audit.md`（Crossref API 實查淘汰 6 筆虛構／錯配 DOI）。確立全廠真實規格為 **320 測點**（160 PT + 80 FT + 80 PDT）與 Group 4 = `2.20 bar`。
2. **Stage 2 · Phase 2 數學規格與防洩漏檢查（Steps `104`–`109` · 07:01–07:02）**
   - 定稿 Unified V1 數學式與偽程式碼，移除未實作之 Darcy-Weisbach 與二項檢定內容。
3. **Stage 3 · Phase 3 後端協定整合與核心引擎修復（Steps `110`–`166` · 07:02–07:08）**
   - 完成 FastAPI + 非同步 Modbus/TCP (`:15020`, CDAB) + SQLite WAL `prediction_logs`，修復 `N10 >= theta` 不可達與 L2 持續水準偏移閘門。
4. **Stage 4 · Phase 4–5 離線 3,840 場基準實驗、壓測、消融與初版雙邊 >10 分鐘實測（Steps `167`–`218` · 07:08–07:12）**
   - 完成 Excel `480/480`（max diff `0.0`）、**3,840 場**公平對照、`raw_onset=2` 消融（突波 FAR `25.62% -> 6.88% / 1.25%`）、Apple M5 壓測（單點 `14.53 µs`）、線上 `vercel.app` (`11.12 min`) 與初版 `11.28 min` 驗證。
5. **Stage 5 · Phase 6–7 初版論文重寫與印刷檢查（Steps `219`–`360` · 07:12–20:28）**
   - 產生 300 DPI 圖表，解決 `Overfull \hbox`、18 處 `\t`+`extbf{` 跳脫損毀與遺漏圖表引用。
6. **Stage 6 · 整套專案 v2.0 徹底重構、SSE 即時推播與本機啟動（Steps `405`–`600` · 20:30–20:54）**
   - 徹底刪除 22 份舊專案複製冗餘檔，全面重寫前端 9 頁 UI + `index.css`（SVG P&ID、OLS 95% PI 圓錐圖、SQLite 稽核分頁、`raw_onset=1/2` 控制、一鍵實驗按鈕）、新增原生 SSE `GET /api/stream`（`LIVE STREAM`），並隔離 `pytest` 通訊埠 (`15029`)。
7. **Stage 7 · 針對重構 v2.0 實時執行 11.35 分鐘全 320 測點實測與 UI 修復（Steps `619`–`720` · 21:05–22:25）**
   - 重新啟動 Chrome 自動連至 `http://127.0.0.1:8000/` 進行 **11.35 分鐘**真實時序測試：**320 / 320 支測點**全部執行預警／事件並寫入 SQLite **203,840 筆**紀錄；修復 Card 1 `DP` (`PDT`) 計數顯示並更新論文全套截圖與圖表。
8. **Stage 8 · Excel 驗證模型數學公式入論文暨口試友善簡化與備註補齊（Steps `721`–`888` · 22:24–23:05）**
   - 逐欄解析教授認可之 `PCW_T30_T20_T10_FINAL_ROLLBACK_THESIS_VERIFICATION.xlsx`，於第三章獨立拆解 **偏移偵測模型（Drift Detection）** 與 **趨勢預測模型（Trend Forecast）** 並建置 `表 3` 與 `§4.2` 全 480 列工作簿實測統計；隨後依口試記憶需求將艱澀集合／邏輯／雙重加總符號簡化為工程直覺公式，於正文嵌入五大「【口試備註】」並產出 [oral_defense_notes.md](./thesis/oral_defense_notes.md)，重編輸出 **36 頁**（`3.81 MiB`、`ZERO OVERFULL OR UNDEFINED WARNINGS`）`main.pdf` 與 `35/35 OK` SHA-256。
9. **Stage 9 · Git 版控整理與 GitHub 遠端公開發布（Steps `893`–`915+` · 23:09–23:12+）**
   - 建立 `.gitignore` 隔離運行庫與快取、設定局部 Git 身份 `Benchen1981 <benchen1981@users.noreply.github.com>`、初始提交 **253 份專案檔案**（`53adffd`）並成功推送至 `https://github.com/benchen1981/PCW-SCADA-System-Final.git` (`main` 分支)，隨後同步更新終版雙語文件、`prompt 01-915.md` 與 `debug 01-016.md` 並再次同步推送。
10. **Stage 10 · 混入檔案徹底回滾、雙棟 FAB/CUB 拓撲與 Section 1.1.3 落地暨在地純淨 Word 匯出**
   - 執行 Git 硬回滾徹底清除混入之外部 Codex 檔案；重新落實雙單體建築（FAB 棟 B2F～6F、CUB 棟 B2F～6F、鋼構空橋管廊、地下室開放共通）空間拓撲；重繪 300 DPI 典藏級高解析圖 1；嚴格補齊 Section 1.1.3（四項架構、門檻、目的與四步驟循環程序）；完整保留第三章口試簡化數學式與正文【口試備註】；透過在地 Pandoc + python-docx + textutil 原生匯出純淨 .docx 與 .doc 檔；更新 35/35 SHA-256 驗證全數通過並推送至 GitHub。

