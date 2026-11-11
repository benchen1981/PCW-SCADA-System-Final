# 模型規格與系統版本差異盤點表 (MODEL_VERSION_DIFFERENCES)

本表逐一比對專案現存四大來源：**Excel Reference Model** (`PCW_T30_T20_T10_FINAL_ROLLBACK_THESIS_VERIFICATION.xlsx`)、**前端 TS 引擎** (`DriftForecastEngine.ts`)、**實驗腳本 Python 引擎** (`baselines.py`)、**重構草案後端** (`2300/app/runtime.py`) 與 **舊版論文** (`PCW_碩士論文_實測修正版_20261110.tex`)，記錄所有參數與定義衝突。

| 差異項目 | Excel Reference Model | 前端 TS 引擎 (v4) | 實驗腳本 `baselines.py` | 草案後端 `2300/runtime.py` | 舊版論文描述 | 衝突影響與建議採用版本 |
|---|---|---|---|---|---|---|
| **測點總數與命名** | `PT-1` (單點) | 320 測點：`PCW0x.Submainyy.{PTS,FT,PTR,PDT}` (160 PT) | 160 PT (`PCW0x.Submainyy.PT{S,R}`) | 160 PT (`PCW0x.SMxx.PT{S,R}`) | 160 PT + 80 TT + 16 FT | **採用前端 320 測點規範** (`PCW0x.Submainyy.{PTS,FT,PTR,PDT}`)，並同步後端、測試矩陣與論文，消除虛構之 80 TT |
| **Group 4 (PCW07-08) 門檻** | 未分組 (`Alarm=1.70`) | Base `2.20`, L/H `2.00/2.40`, LL/HH `1.90/2.50` | Base `2.20`, L/H `2.00/2.40` | Base `2.10`, L/H `1.96/2.24` | Base `2.10`, L/H `1.90/2.30`, LL/HH `1.80/2.40` | **採用實際系統 `2.20` (LL=1.90, L=2.00, H=2.40, HH=2.50)**，因前端定義與線上部署一致；差異如實記錄 |
| **基準視窗與統計量** | `[t-70, t-10)` 60 點平均 `BaseAvg60` | `[t-70, t-10)` 60 點平均 `baseAvg60` (僅 GOOD 點) | `window[-70:-10]` 60 點平均 | 未使用 60 點基準 | 混用 `W=60` `MAD` 與 `BaseAvg60` | **統一為 `[t-70, t-10)` 60 點算術平均 `BaseAvg60`**（加入 GOOD 品質過濾，Past-Only） |
| **斜率估計方式** | 單側 `max(0, (R5 - P5)/5)` | 雙側 `(mean(R5) - mean(P5))/5` | 雙側 `(mean(R5) - mean(P5))/5` | 10 點端點差 `(y_9 - y_0)/9` | 錯寫為 `W=60` 之 OLS 斜率 | **採用雙側 `(mean(R5) - mean(P5))/5`**，同時支援高壓上升與低壓洩漏/阻塞雙向預警；OLS 僅於近 10 點估計 `slopeOls`, `R^2` 與 95% 預測區間 |
| **N10 判定不等式與觸發** | `N10 > 2.0` **且** `Value >= Gate_{30/20/10}` (`1.55/1.58/1.62`) | `N10 > theta` (`2.0`) **且** `|Slope|*30 >= g%*(H-L)` (`g=5%`) | `N10 >= theta` (`2.0`) **且** `|Slope|*30 >= 5%*(H-L)` | 未使用 `N10` | 錯寫為二項檢定 `P(S_n >= k) < 0.01` | **重大修正**：當對稱雜訊使 `M60 >= 30` 時，`N10_max = 60/M60 <= 2.0`，嚴格不等式 `N10 > 2.0` **數學上不可達**！統一改為 **`N10 >= theta`（預設 `theta = 2.0`）搭配 Span Gate `g = 5%`**，並以敏感度測試呈現 `theta in {1.5, 1.8, 2.0, 2.5}` 影響 |
| **硬化層 (L1–L7)** | 無 | L1 Quality, L2 Span Gate, L3 OLS Band, L4 TTL, L5 EVENT, L6 Hysteresis (`K=3`), L7 Risk Index | 僅實作 L2, L5, L6 | 無 | 錯寫為水錘中位數濾波、Tool Maintenance、VFD 聯鎖 | **前後端與論文全面統一為真實 L1–L7 規格**，移除論文中未實作之虛構硬化層描述 |
| **即時觸發與一致性** | 逐分鐘公式 | 僅在整分邊界 (`minute !== currentMinute`) 重算預測；調整 Modbus 基準時 Alarm Center 立即觸發但 System Prediction 延遲或顯示 `NORMAL` | 離線逐筆 | 即時請求重算 | 附註為已知缺陷 | **全面修復**：Modbus 基準變更、工程限值變更、故障注入或感測器跨限時，立即更新預測狀態並同步 `EVENT` 與 `DRIFT` 警報 |
| **Modbus 暫存器格式** | 無 | FLOAT32 (CDAB Word-Swap, 2 registers/tag, `40001..40639`) | 無 | INT16 (x100, 1 register/tag) | 錯寫為 `40001..40160` INT16 | **統一為 FLOAT32 CDAB (`40001..40639`, 640 holding registers)**，並於後端實作真實 Modbus TCP Server |

