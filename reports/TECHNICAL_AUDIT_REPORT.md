# 技術稽核總報告 (TECHNICAL_AUDIT_REPORT)

- **稽核與重構完成日期**：2026-11-11
- **原專案基線**：`Existing/Code/pcw-poc-v1_merged` (commit `4daa3b0e8ce51101a0b60a514af0da8a06736f5c`) 與 `Existing/Output 20261110 2330`
- **重構專案路徑**：`PCW_SCADA_Final_Project/`

## 1. 重大稽核發現與系統程式改寫明細

| 編號 | 稽核發現項目 | 原系統/論文問題 | 改寫後系統解決方案 | 驗證狀態 |
|---|---|---|---|---|
| F01 | **N10 門檻結構不可達** | `DriftForecastEngine.ts` 使用 `n10 > theta` (`2.0`)，當對稱雜訊使 `M60 >= 30` 時 `N10_max = 60/M60 <= 2.0`，密度指標永遠無法觸發 | Python 與 TS 同步修正為 `n10 >= theta`（`drift_forecast.py` / `DriftForecastEngine.ts`） | `PASS` (`pytest`) |
| F02 | **長時段 (>10 分鐘) 基準偏移失效** | 原 L2 僅檢查 `|Slope|*30`，當基準偏移超過 10 分鐘使 `P` 與 `R` 皆穩定於新水準時，斜率歸零導致預警過早清除 | L2 新增持續水準偏移閘門 `|mean(C) - BaseAvg60| >= g%*(H-L)`，確保 >10 分鐘行為偏差穩定維持預警 | `PASS` (`pytest` + 11.5m run) |
| F03 | **警報中心與預測頁狀態不一致** | `SimulatorEngine.ts` 僅於整分邊界重算預測，且 Modbus 設定變更未觸發重算，造成 `1.72 bar` 時 Alarm Center 顯示 `HIGH` 而 System Prediction 顯示 `NORMAL` | `update_simulator_config`、`inject_fault`、`update_limits` 及每 tick 跨限轉態時即時同步 `predictions` 與 `EVENT` / `DRIFT` | `PASS` (瀏覽器實測 + `pytest`) |
| F04 | **前後端分離與協定缺口** | `pcw-poc-v1_merged` 無後端程式且無真實 Modbus TCP Socket；`2300` 草案後端演算法降級且未接通前端 | 重構 FastAPI + SQLite WAL + 純 Python 非同步 Modbus/TCP Server (`Port 15020`, FC03/06/16, FLOAT32 CDAB) + Web UI | `PASS` (`pytest` 6/6) |
| F05 | **缺乏故障注入 UI 與逐點記錄** | `ModbusMonitor.tsx` 僅能修改 `baseValue`；缺少逐感測器預測警報歷史資料庫與匯出 | 新增 `Behavioral Deviation Scenario` 注入面板、`Pair Level (80)` 配對診斷與 SQLite `prediction_logs` 逐點紀錄及 CSV 匯出 | `PASS` |
| F06 | **論文測點與公式多處不實** | 第一章誤載 160 PT + 80 TT + 16 FT 及 Group 4=2.10；第三章描述未實作之 Darcy-Weisbach 與二項檢定；`refs.bib` 含 6 筆虛構/錯置 DOI | 全面改寫 `thesis/main.tex` 與 `refs.bib`，100% 對齊 320 測點、Group 4=2.20、Unified V1 數學與 Crossref 驗證文獻 | `PASS` |
| F07 | **單點外推面對突波誤報機制** | `Fcst30 = x_now + Slope*30` 與單向 L6 鎖存使單分鐘 `0.30*span` 突波產生 100% 誤報 (`FAR=25.47%`) | 誠實揭露於實驗章節與 `FAILURE_ANALYSIS.md`，並透過 `raw_onset=2` 消融實驗證實可將 `FAR` 降至 `1.25%–6.88%` | `PASS` |

## 2. 尚未驗證與保留範圍 (Honest Scope Boundaries)

1. 本研究尚未接入真實晶圓廠現場 PLC／實體感測器或正式 MS-SQL Historian，所有廠務連線元件於架構圖中明確標示為規劃中項目。
2. 線上 Vercel 網址 (`https://pcw-scada-system.vercel.app/`) 因未授權遠端覆寫部署，仍維持原靜態建置；本報告同時交付「線上舊版實測證據」與「本機完整重構版實測證據」。

