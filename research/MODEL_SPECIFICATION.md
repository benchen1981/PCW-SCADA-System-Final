# 統一統計式早期預警模型規格書 (MODEL_SPECIFICATION)

本文件為重構後統一前後端 (`system/backend/app/engine/drift_forecast.py` 與 `system/frontend/src/services/analytics/DriftForecastEngine.ts`) 之單一權威規格 (Single Source of Truth)，同時定義與 Excel Reference Model 的對照關係。

## 1. 系統與感測器配置規格

- **廠區迴路**：`PCW01`～`PCW08` 共 8 套獨立封閉循環冷卻水系統。
- **次幹管配對**：每套系統 10 組次幹管 (`Submain01`～`Submain10`)，全廠共 80 組 Supply/Return 配對。
- **測點配置**：每組 Submain 含 4 支標準測點，全廠共 **320 支**感測器：
  - `PTS` (Supply Pressure, `bar`)：80 支
  - `PTR` (Return Pressure, `bar`)：80 支（與 `PTS` 合計 **160 支 PT**）
  - `FT` (Supply Flow, `LPM`)：80 支
  - `PDT` (Differential Pressure `PTS - PTR`, `bar`)：80 支
- **四大參數分組 (Engineering Limits)**：

| 分組 | 迴路 | 樓層 | 感測器類型 | Baseline | LoLo (`LL`) | Lo (`L`) | Hi (`H`) | HiHi (`HH`) | 單位 |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| Group 1 | PCW01, PCW02 | 2F Cleanroom | PT (`PTS`/`PTR`) | 1.50 | 1.20 | 1.30 | 1.70 | 1.80 | bar |
| Group 2 | PCW03, PCW04 | 2F Cleanroom | PT (`PTS`/`PTR`) | 1.90 | 1.50 | 1.70 | 2.10 | 2.20 | bar |
| Group 3 | PCW05, PCW06 | 1F Sub-Fab | PT (`PTS`/`PTR`) | 2.50 | 2.20 | 2.30 | 2.70 | 2.80 | bar |
| Group 4 | PCW07, PCW08 | 1F Sub-Fab | PT (`PTS`/`PTR`) | 2.20 | 1.90 | 2.00 | 2.40 | 2.50 | bar |
| Group 1/2 | PCW01–04 | 2F Cleanroom | FT | 180.0 | 150.0 | 160.0 | 200.0 | 220.0 | LPM |
| Group 3 | PCW05–06 | 1F Sub-Fab | FT | 260.0 | 230.0 | 240.0 | 280.0 | 300.0 | LPM |
| Group 4 | PCW07–08 | 1F Sub-Fab | FT | 240.0 | 200.0 | 220.0 | 260.0 | 280.0 | LPM |
| All | PCW01–08 | 1F/2F | PDT | 0.30 | 0.00 | 0.10 | 0.50 | 0.60 | bar |

## 2. 程式變數與資料欄位對照表

| 數學符號 | Python 變數 | TypeScript 變數 | 資料欄位 / 參數來源 | 型別與單位 |
|---|---|---|---|---|
| \(x_i(t)\) | `current_value` | `currentValue` | 即時量測值 (bar / LPM) | `float` |
| \(W\) | `WINDOW = 70` | `WINDOW = 70` | 1 分鐘解析度滑動視窗長度 | `int` (min) |
| \(B_i(t)\) | `base_avg_60` | `baseAvg60` | `[t-70, t-10)` 有效點平均 | `float` |
| \(\bar{x}_{P,i}(t), \bar{x}_{R,i}(t)\) | `mean_p`, `mean_r` | `mean(P)`, `mean(R)` | `[t-10, t-5)` 與 `[t-5, t)` 有效點平均 | `float` |
| \(\hat{\beta}_{\mathrm{diff},i}(t)\) | `slope` | `slope` | 兩視窗有限差分斜率 | `float` (unit/min) |
| \(d_i(t)\) | `up` (`1/-1`) | `up` (`>= 0`) | 漂移方向符號 | `int` |
| \(M_{60,i}(t), M_{10,i}(t)\) | `m60`, `m10` | `m60`, `m10` | 基準與近期方向性偏離計數 | `int` |
| \(N_{10,i}(t)\) | `n10` | `n10` | 方向性異常密度比 | `float` (無因次) |
| \(\theta\) | `sensitivity` (`2.0`) | `params.sensitivity` (`2.0`) | `N10` 漂移敏感度門檻 | `float` |
| \(g\) | `slope_gate_pct` (`5.0`) | `params.slopeGatePct` (`5.0`) | 跨度歸一化斜率門檻百分比 | `float` (%) |
| \(\hat{\beta}_{\mathrm{OLS},i}(t), R^2\) | `slope_ols`, `r2` | `fit.slope`, `fit.r2` | 近 10 點 OLS 擬合斜率與判定係數 | `float` |
| \(\delta_{h,i}(t)\) | `band10/20/30` | `band10/20/30` | Student-\(t_{0.975,8}=2.306\) 95% 預測區間半寬 | `float` |
| \(\mathrm{TTL}_i(t)\) | `ttl_minutes` | `ttlMinutes` | 依當前斜率預估到限剩餘分鐘數 | `float \| None` |
| \(K_{\mathrm{hold}}\) | `release_hold` (`3`) | `releaseHold` (`3`) | 降級解除需連續確認次數 | `int` |
| \(R_i(t)\) | `risk_score` | `riskScore` | 融合風險指標 `[0, 100]` | `int` |
| \(S_i(t)\) | `state` | `state` | `NORMAL / T-30 / T-20 / T-10 / EVENT / INSUFFICIENT_DATA / DISABLED` | `enum` |

## 3. 與 Excel Reference Model 差異說明（V1 統計模型對齊）

1. **雙側對稱檢測**：Excel `MinuteInference` 僅實作 `MAX(0, (R5-P5)/5)` 上限側；統一引擎使用有號斜率 `(mean(R) - mean(P))/5`，同時涵蓋 `HI/HIHI` 與 `LO/LOLO`。
2. **`N10 >= theta` 修正可達性**：解決原 `N10 > 2.0` 在 `M60 >= 30` 時數學上永遠無法成立之結構盲區。
3. **L1–L7 硬化層**：L1 品質閘門 (`validRatio >= 0.80`) 防止壞值污染、L2 跨度閘門取代絕對斜率門檻以支援跨物理量 (`bar` 與 `LPM`)、L5 明確將已超限區分為 `EVENT`、L6 防抖遲滯鎖存降低 Chattering。
4. **即時一致性修復**：當 Modbus 基準設定、故障注入、工程限值更新或感測器即時計測跨越 `H`/`L` 時，系統立即同步更新 `predictions` 與 `DRIFT` 警報狀態，不再出現 Alarm Center 與 System Prediction 矛盾。

