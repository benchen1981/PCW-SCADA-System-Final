# 完整實驗與測試計畫書 (TEST_PLAN)

## 1. 測試範圍與目標

1. **全系統測點覆蓋**：涵蓋 `PCW01`–`PCW08` 共 8 套系統、80 組 `Submain` 配對、**320 支感測器**（含 **160 支 PT** 壓力測點、`80 支 FT` 流量測點與 `80 支 PDT` 壓差測點）。
2. **單點最小測試次數要求**：每個 PT 測點至少執行 10 次獨立有效測試（本計畫執行 **12 種獨立情境**，故 160 PT 合計 **1,920 場**，全廠 320 感測器合計 **3,840 場**，遠超最低門檻）。
3. **跨實作一致性驗證**：
   - Excel Reference Model (`RawData` 480 筆) vs 程式逐筆比對（容許誤差 `1e-9`）。
   - Python 統一引擎 (`drift_forecast.py`) vs TypeScript 前端引擎 (`DriftForecastEngine.ts`) 跨語言數值對等驗證（誤差 `< 1e-9`）。
4. **線上部署與本機重構系統瀏覽器自動化巡檢**：
   - 自動連線 `https://pcw-scada-system.vercel.app/` 巡檢全部 9 個功能頁、測試 `1.72 bar` 一致性缺陷、執行所有 160 PT 感測器預測驗證，並進行 **>10 分鐘真實時間（11.5 分鐘）** Modbus 基準行為偏差試驗。
   - 自動連線本機重構系統 (`http://127.0.0.1:8000` + Modbus TCP `15020`) 進行同樣 **11.5 分鐘真實時間**試驗，驗證缺陷修復、SQLite 持久化紀錄與所有 320 感測器執行留存。

## 2. 12 種受控測試情境設計（每顆感測器獨立種子）

- **異常情境（8 類，目標觸發預警或事件，`expected_fault = 1`）**：
  1. `DRIFT_UP_SLOW` (+1.8% span/min)
  2. `DRIFT_UP_MOD` (+3.0% span/min)
  3. `DRIFT_UP_FAST` (+4.5% span/min)
  4. `DRIFT_DOWN_SLOW` (-1.8% span/min)
  5. `DRIFT_DOWN_MOD` (-3.0% span/min)
  6. `DRIFT_DOWN_FAST` (-4.5% span/min)
  7. `SUDDEN_STEP_UP` (+55% span 階躍越限)
  8. `SUDDEN_STEP_DOWN` (-55% span 階躍越限)
- **非異常干擾與品質情境（4 類，目標維持 NORMAL 或 INSUFFICIENT_DATA，`expected_fault = 0`）**：
  9. `NORMAL_STABLE` (常態高斯雜訊)
  10. `TRANSIENT_SPIKE` (單分鐘 ±30% span 瞬態突波)
  11. `HIGH_FREQ_OSCILLATION` (週期 4 min、±10% span 高頻震盪)
  12. `BAD_QUALITY_FROZEN` (連續 16 分鐘品質異常/數值凍結，測試 L1 Quality Gate)

## 3. 邊界案例功能測試 (`TEST_CASES.csv`)

涵蓋 12 項邊界案例：`TC-01` 常態、`TC-02/03` 雙向慢漂、`TC-04` 10 分鐘持續基準偏移、`TC-05/06` 逼近 HI/LO 界限、`TC-07/08` 已超限 `EVENT`、`TC-09` L1 品質過濾、`TC-10` 資料不足、`TC-11` 零變異靜止點、`TC-12` 趨勢反轉。

