# Web SCADA UI 全頁面功能稽核報告 (UI_FUNCTION_AUDIT)

本報告涵蓋對 **線上部署版 (`https://pcw-scada-system.vercel.app/`)** 與 **本機重構版 (`http://127.0.0.1:8000/`)** 全部 9 大功能頁之瀏覽器實測巡檢結果（Google Chrome 157.0.8103.40 + Puppeteer 25.13.0）。

## 1. 全頁面巡檢對照表

| 頁面路由 | 頁面名稱 | 線上部署版 (`vercel.app`) 實測狀態 | 本機重構版 (`127.0.0.1:8000`) 實測狀態 | 稽核證據截圖 |
|---|---|---|---|---|
| `/` | 1. Plant Overview | 正常載入 PCW01–PCW08 8 張迴路卡片，無 console error | 正常載入，且即時同步 Alarm / Prediction / Drift 數量 | `deployed_01_overview.png`, `local_01_overview.png` |
| `/sensors` | 2. Live Sensor Data | 正常顯示 Process P&ID 與 320 測點列表 | 正常顯示，所有數值由 FastAPI + Modbus TCP 即時讀取 | `deployed_02_sensors.png`, `local_02_sensors_pid.png` |
| `/historian` | 3. Historian Trend | 可選取原測點與 8 項衍生特徵查詢圖表 | 支援查詢 10+ 分鐘真實 SQLite/RingBuffer 歷史曲線 | `deployed_03_historian.png`, `local_11min_historian_trend.png` |
| `/live-trend` | 4. Live Trend | 正常繪製 30 分鐘即時趨勢線與工程上下限 | 正常繪製即時串流趨勢，無 console error | `deployed_04_live_trend.png`, `local_04_live_trend.png` |
| `/alarms` | 5. Alarm Center | 正確觸發 `HIGH`/`LOW` 與 ACK/Shelve；`1.72 bar` 測試即刻產生 `ACTIVE_UNACK` | 同步產生 `HIGH`/`LOW` 與 `DRIFT` 早期預警警報並寫入 SQLite | `deployed_11_defect_alarm.png`, `local_10_consistent_alarm.png` |
| `/t30` | 6. System Prediction | **缺陷 (PARTIAL)**：`1.72 bar` 時仍顯示 `NORMAL`；僅於整分邊界重算 | **已修復 (PASS)**：即時同步為 `EVENT`；新增 `Pair Level (80)` 配對診斷與 CSV 匯出 | `deployed_12_defect_prediction.png`, `local_11_consistent_prediction.png`, `local_11min_pair_diagnostics.png` |
| `/settings` | 7. Prediction Tuning | 可調整全域與單點 N10 門檻 | 可調整敏感度並立即重算全廠推論與記錄 | `deployed_07_tuning.png`, `local_07_tuning.png` |
| `/modbus` | 8. Modbus Simulator | 顯示 320 測點暫存器，可改 Base/Noise/Limits，但無故障情境注入按鈕 | 顯示 640 暫存器 (`40001..40639` CDAB) 與 Scenario 欄位，整合 `DRIFT/STEP/SPIKE/BAD_QUALITY/COMM_LOSS` 故障注入器 | `deployed_10_simulator.png`, `local_08_modbus_monitor.png`, `local_11min_fault_injector.png` |
| `/model-info` | 9. Prediction Model Info | 文字公式與實際 `L1–L7` / 雙側斜率不完全一致 | 全面改寫與實際程式 100% 對齊之數學定義與 L1–L7 說明 | `deployed_09_model_info.png`, `local_09_model_info.png` |

## 2. 狀態一致性實測對照 (`PCW01.Submain01.PTS` = 1.72 bar, HI = 1.70 bar)

- **線上舊版 (`vercel.app`)**：`Alarm Center` 顯示 `PCW01.Submain01.PTS HIGH ACTIVE_UNACK`，同一秒切換至 `System Prediction` 顯示 `1.723` 但 `State = NORMAL` (`Forecasts within limits`) —— **確認為實機狀態不一致缺陷**。
- **本機重構版 (`127.0.0.1:8000`)**：`Alarm Center` 顯示 `PCW01.Submain01.PTS HIGH ACTIVE_UNACK`，同一秒切換至 `System Prediction` 顯示 `1.720`、`State = EVENT`、`Risk = 100` (`PV (1.720) beyond H (1.7) -> EVENT`) —— **狀態 100% 一致**。

