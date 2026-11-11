# Phase 1 — 全面系統與論文稽核報告 (PHASE1_AUDIT_REPORT)

## 1. 實際執行項目
- 盤點 `/Users/benchen1981/Downloads/Web SCADA Final 20261111/Existing` 全部程式碼 (`pcw-poc-v1`, `pcw-poc-v1_merged`, `Output 20261110 2300/work/pcw_submission`)、Excel Reference Model (`PCW_T30_T20_T10_FINAL_ROLLBACK_THESIS_VERIFICATION.xlsx`)、實驗腳本與 `PCW_碩士論文_實測修正版_20261110.tex`。
- 探測本機硬體與工具鏈版本 (`evidence/environment/baseline_probe.txt`) 並計算基線檔案 SHA-256 (`evidence/checksums/baseline_sha256.txt`)。
- 透過無頭 Chrome (`Puppeteer 25.13.0`) 連線至 `https://pcw-scada-system.vercel.app/` 確認線上運行版本與前端建置一致性。
- 透過 Crossref REST API 逐筆核驗 `refs 20261109.bib` 中 8 筆 DOI 之真實性。

## 2. 執行環境
- **主機硬體**：Apple M5 (10 cores, 16 GiB RAM)
- **作業系統**：macOS 26.7.3 (Build 25G342, arm64)
- **執行環境**：Python 3.9.6, Node.js v24.14.1, Tectonic 0.17.0, Google Chrome 157.0.8103.40
- **Git 基線**：`4daa3b0e8ce51101a0b60a514af0da8a06736f5c`

## 3. 實際結果與重大發現
1. **程式碼分裂與未對齊**：`pcw-poc-v1_merged` 僅有純前端模擬器，`2300` 草案後端未與前端接軌且演算法被降級為簡單 10 點差分。
2. **數學引擎與一致性缺陷**：
   - `DriftForecastEngine.ts` 之 `n10 > theta` (`theta=2.0`) 在常態對稱雜訊 `M60 >= 30` 下結構性不可達 (`N10_max = 60/M60 <= 2.0`)。
   - `SimulatorEngine.ts` 僅在整分邊界計算預測，造成 Modbus 修改設定或感測器超限 (`1.72 bar >= 1.70`) 時，`Alarm Center` 立刻顯示 `HIGH`，但 `System Prediction` 仍停留在 `NORMAL`。
   - `ModbusMonitor.tsx` 缺少故障注入 (`DRIFT`, `STEP`, `SPIKE`, `BAD_QUALITY`, `COMM_LOSS`) 與逐感測器預測警報執行紀錄匯出功能。
3. **論文與系統嚴重脫節**：
   - 舊版論文第一章誤載 160 PT + 80 TT + 16 FT（實為 160 PT + 80 FT + 80 PDT = 320 測點）及 Group 4 `2.10 bar`（實為 `2.20 bar`）。
   - 舊版論文第三章仍保留未實作之 Darcy-Weisbach `DW-ADE`、二項分布檢定 `p0=0.05` 與 7 層虛構硬體濾波流程。
   - `refs 20261109.bib` 存在 4 筆不存在的假 DOI 與 2 筆 DOI 張冠李戴書目，必須全面清除。
4. **時間尺度驗證缺口**：既往所有線上模擬與壓測皆未執行「調整 Modbus 基準使其行為偏差並持續觀察 10 分鐘以上」之真實時序驗證。

## 4. 證據位置
- `audit/PROJECT_BASELINE.md`
- `audit/CLAIMS_EVIDENCE_REGISTER.csv`
- `audit/MODEL_VERSION_DIFFERENCES.md`
- `evidence/environment/baseline_probe.txt`
- `evidence/checksums/baseline_sha256.txt`

## 5. 問題與風險
- 線上 Vercel 部署 (`https://pcw-scada-system.vercel.app/`) 仍為舊版靜態前端（未修復即時同步缺陷）；在本機無遠端自動部署憑證下，線上測試將如實記錄其現況與 10+ 分鐘行為偏差結果，同時於本機完成整套重構系統之全功能、Modbus TCP 與瀏覽器全自動驗證。

## 6. 狀態
`PASS`（Phase 1 稽核與可追溯基線建立完成，所有重大差異已定位）

## 7. 下一步
進入 **Phase 2 — Model Verification & Mathematical Alignment**：建立正式數學規格 (`research/`)、資料洩漏稽核 (`audit/DATA_LEAKAGE_AUDIT.md`)，並設計統一的前後端與 Modbus TCP 系統架構。

