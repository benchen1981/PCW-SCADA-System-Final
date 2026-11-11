# PCW 論文研究系統 Phase 1 基線盤點報告 (PROJECT_BASELINE)

- **稽核時間**：2026-11-11T07:00:54+08:00
- **專案基線目錄**：`/Users/benchen1981/Downloads/Web SCADA Final 20261111/Existing`
- **重構目標目錄**：`/Users/benchen1981/Downloads/Web SCADA Final 20261111/PCW_SCADA_Final_Project`
- **Git Commit (Existing/Code/pcw-poc-v1_merged)**：`4daa3b0e8ce51101a0b60a514af0da8a06736f5c`
- **雜湊清單**：詳見 `evidence/checksums/baseline_sha256.txt`

## 1. 系統與研究元件現況盤點表

| 項目 | 實際狀態 | 證據位置 | 狀態 | 待處理問題 |
|---|---|---|---|---|
| 推論演算法程式 (TS) | React 前端內建 `DriftForecastEngine` (v4, 70 點雙視窗 + L1-L7 硬化) 與 `AlarmEngine` (ISA-18.2 死區/延遲) | `Existing/Code/pcw-poc-v1_merged/frontend/src/services/analytics/DriftForecastEngine.ts`, `AlarmEngine.ts` | PARTIAL | 1) `N10 > theta` 在 `theta=2.0` 且 `M60>=30` 時結構性不可達；2) `SimulatorEngine` 僅於整分邊界更新預測，導致高壓觸發後與警報中心不同步 |
| 推論演算法程式 (Python) | 存在多套未對齊版本：`pcw-poc-v1` (stub)、`2300/app/runtime.py` (10點簡單斜率)、`thesis/experiments/baselines.py` (`ProposedDualWindowEngine`) | `Existing/Output 20261110 2300/work/pcw_submission/app/runtime.py`, `Existing/thesis/experiments/baselines.py` | FAIL | 前後端與實驗腳本未共用同一核心規格，且 `2300` 重構版之 Python API 未接通前端 |
| Excel Reference Model | 含 `Parameters`、`RawData` (PT-1 共 480 列, 2026-08-05 03:01~11:00)、`MinuteInference` (Past-Only 單側正斜率 + Gate30/20/10) | `Existing/PCW_T30_T20_T10_FINAL_ROLLBACK_THESIS_VERIFICATION.xlsx` | PASS | 僅支援單側上漂 (`MAX(0, ...)`) 與輔助門檻 `Gate30/20/10=1.55/1.58/1.62`，未含 L1-L7 硬化層 |
| PT Tag Mapping & 測點配置 | 8 套系統 (PCW01–08) × 10 Submain = 80 配對；每 Submain 含 `PTS`, `FT`, `PTR`, `PDT` 共 320 測點（含 160 PT、80 FT、80 PDT），無 TT | `Existing/Code/pcw-poc-v1_merged/frontend/src/data/sensorDefinitions.ts`, `pcwSubmains.ts`, `modbusRegisterMap.ts` | PARTIAL | 論文第一章誤寫為 160 PT + 80 TT + 16 FT，且表 1-1 Group 4 基準寫 2.10 bar，與系統程式 `2.20 bar` 衝突 |
| Modbus Simulator & 協定 | 前端純瀏覽器記憶體模擬器 + FLOAT32 (CDAB, 2 registers/tag, 40001~40639)；無真實運作中之 Modbus TCP Socket 伺服器與後端連動 | `Existing/Code/pcw-poc-v1_merged/frontend/src/pages/ModbusMonitor.tsx`, `SimulatorEngine.ts` | PARTIAL | 1) UI 未暴露 `DRIFT`/`STEP`/`SPIKE`/`BAD_QUALITY`/`COMM_LOSS` 故障注入控制；2) 修改基準值不會立即重算預測與留存逐筆紀錄 |
| 已部署 Web UI (Vercel) | `https://pcw-scada-system.vercel.app/` (束包 `index-HuaOorlW.js` 與 `pcw-poc-v1_merged/frontend/dist` 完全相同)，9 個頁面均可開啟且無 console error | `https://pcw-scada-system.vercel.app/` | PARTIAL | 存在即時狀態一致性缺陷：`1.72 bar` 越限進入 Alarm Center 後，System Prediction 未同步切換為 `EVENT`；尚未執行 >10 分鐘真實行為偏差連續測試 |
| Database / Historian | 前端使用瀏覽器 `localStorage` + `HistorianStore` typed-array 環形緩衝 (1440點)；`2300` 有 SQLite stub 但未實際掛載於前端 | `Existing/Code/pcw-poc-v1_merged/frontend/src/repositories/HistorianStore.ts`, `MockDatabase.ts` | PARTIAL | 缺少後端資料庫持久化、逐感測器預測警報完整執行稽核紀錄與獨立查詢輸出 |
| 實驗證據與測試套件 | 已有 `E1` (480點歷史回放) 與 `revalidated_1600` (160 PT × 10 場)；但缺乏 320 全感測器矩陣、缺乏 >10 分鐘真實時間 Modbus 基準偏移實驗 | `Existing/thesis/experiments/results/`, `Existing/Output 20261110 2330/PCW_論文實驗重驗證據包_20261110.zip` | PARTIAL | 論文截圖為舊版 (11/08)，尚未更換為最新系統狀態與實驗證明 |
| 論文 LaTeX 與文獻 | `PCW_碩士論文_實測修正版_20261110.tex` 與 `refs 20261109.bib`；經 Crossref API 實測，`refs.bib` 內含 4 筆 404 虛構 DOI 與 2 筆 DOI 內容錯置 | `Existing/Output 20261110 2330/PCW_碩士論文_實測修正版_20261110.tex`, `Existing/thesis/refs 20261109.bib` | FAIL | 1) 第三章仍描述未實作之 Darcy-Weisbach `DW-ADE` 與二項檢定 `p0=0.05`；2) `refs.bib` 含未刪除之虛構書目；3) 圖表與數據需隨重構系統全面重建 |

## 2. 本階段已證實、待確認與阻礙項目

### 已證實 (VERIFIED)
1. 線上部署網址 `https://pcw-scada-system.vercel.app/` 與 `Existing/Code/pcw-poc-v1_merged/frontend/dist` 建置產物 (`index-HuaOorlW.js`, `index-DGervG14.css`) 一致。
2. 專案實際測點為 **320 支**（8 PCW × 10 Submain × 4 感測器），包含 **160 支 PT** (`PTS`, `PTR`)、**80 支 FT** 及 **80 支 PDT**。
3. 實測硬體環境為 **Apple M5 (10 cores, 16 GiB RAM), macOS 26.7.3 (arm64)**，可用 `Python 3.9.6`、`Node v24.14.1`、`Google Chrome 157.0.8103.40`、`Puppeteer 25.13.0`、`Tectonic 0.17.0`。
4. 透過 Crossref REST API 實查 `refs 20261109.bib` 之 8 筆 DOI，確認僅 `kaufman2012leakage` 與 `colebrook1939turbulent` 內容與 DOI 相符；其餘 6 筆含 4 筆 404 不存在 DOI (`caballero2026`, `li2024`, `smith2021`, `wang2025`) 與 2 筆 DOI 對應他篇論文 (`lin2023`, `zhang2022`)。

### 阻礙與風險 (BLOCKED / RISK)
1. Vercel 線上環境為靜態託管 SPA（無雲端權限重推部署之前，線上版本仍維持既有 `index-HuaOorlW.js` 行為），故我們將：
   - 直接連線 `https://pcw-scada-system.vercel.app/` 完成全部 9 頁巡檢、全感測器測試與 >10 分鐘真實行為偏差實驗並如實記錄；
   - 同步於本機重構並啟動完整前後端 + Modbus TCP 系統 (`http://127.0.0.1:8000`)，修正所有已確認缺陷並執行同規格實機驗證與 10+ 分鐘實驗。
2. 全廠真實晶圓廠歷史故障標籤檔仍僅有 `RawData` 中單一測點 `PT-1` (480 分鐘)，故 160/320 測點橫向比較仍屬**合成/受控模擬故障注入**，論文須嚴格區分歷史回放與受控模擬實驗之邊界。

