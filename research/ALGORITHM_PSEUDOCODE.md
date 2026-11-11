# 演算法偽程式碼與複雜度分析 (ALGORITHM_PSEUDOCODE)

本文件收錄與實際系統程式 (`drift_forecast.py`, `DriftForecastEngine.ts`, `alarm_engine.py`, `AlarmEngine.ts`, `simulator/engine.py`) 一致之標準演算法偽程式碼。

---

## 演算法 1：1 分鐘資料聚合與 Past-Only 歷史基準視窗建立

- **對應程式**：`SimulatorEngine.processTick()` / `app/simulator/engine.py` + `HistorianStore`
- **輸入**：1 秒周期高頻取樣串流 \((x_{\mathrm{raw}}, q_{\mathrm{raw}})\)、當前分鐘邊界 \(m_{\mathrm{curr}}\)
- **輸出**：每分鐘時間有序歷史序列 \(\mathcal{H}_i\) 與推論輸入視窗 \(\mathcal{W}_i(t)\)
- **邊界條件**：若該分鐘內有效 (`GOOD`) 樣本比率 \(< 50\%\)，則該分鐘紀錄標記為 `BAD` 或 `COMM_LOSS`，避免壞值平均後偽裝成正常點。

```text
Algorithm 1: Minute Aggregation & Past-Only Window Extraction
Input:  Tick sample (v_tick, q_tick) at timestamp t_ms; accumulator Acc[tag]
Output: Time-ordered 1-min historian record and 70-point Past-Only window W[tag]

1.  Acc[tag].total <- Acc[tag].total + 1
2.  Acc[tag].last_q <- q_tick
3.  if q_tick == GOOD then
4.      Acc[tag].sum <- Acc[tag].sum + v_tick
5.      Acc[tag].good <- Acc[tag].good + 1
6.  end if
7.  m_now <- floor(t_ms / 60000)
8.  if m_now != m_curr then                     // Minute boundary crossed
9.      t_stamp <- m_curr * 60000 + 30000       // Center of closed minute
10.     for each tag in AllSensors do
11.         if Acc[tag].total > 0 then
12.             ratio <- Acc[tag].good / Acc[tag].total
13.             if ratio >= 0.5 then
14.                 Historian.append(tag, t_stamp, Acc[tag].sum / Acc[tag].good, GOOD)
15.             else
16.                 q_min <- (Acc[tag].last_q == COMM_LOSS) ? COMM_LOSS : BAD
17.                 Historian.append(tag, t_stamp, v_last[tag], q_min)
18.             end if
19.         end if
20.     end for
21.     Reset Acc; m_curr <- m_now
22. end if
23. W[tag] <- Historian.tail(tag, 70)           // Strictly t < t_now (Past-Only)
24. return W[tag]
```
- **時間與空間複雜度**：單筆 Tick 聚合 \(O(1)\)；每分鐘建立視窗 \(O(W)\)（\(W=70\) 為常數），環形緩衝空間 \(O(C)\)（每測點固定保留 1,440 分鐘）。

---

## 演算法 2：雙視窗異常密度指標與斜率外推 (Dual-Window Drift & Forecast)

- **對應程式**：`evaluateWindow()` (`DriftForecastEngine.ts`) / `evaluate_window()` (`drift_forecast.py`)
- **輸入**：Past-Only 視窗 \(\mathcal{W}\)（70 點）、即時量測 \(x_{\mathrm{now}}\)、工程限值 \((LL, L, H, HH)\)、敏感度 \(\theta\)、跨度閘門 \(g\%\)
- **輸出**：`PredictionResult` (`BaseAvg60`, `M60`, `M10`, `N10`, `Slope`, `SlopeOls`, `R2`, `Fcst10/20/30`, `Band10/20/30`, `TTL`, `State`, `Detector`, `RiskScore`)
- **邊界條件**：資料筆數 \(< 70\)、有效率 \(< 0.80\)、或任一子視窗無有效點 \(\implies\) `INSUFFICIENT_DATA`；`M60=0, M10>0` \(\implies N_{10}=999\)；跨度 \(H-L\) 取 \(\max(10^{-9}, H-L)\)。

```text
Algorithm 2: Dual-Window Anomaly Density, Slope Extrapolation & L1-L7 Hardening
Input:  W[0..69], x_now, Limits(LL, L, H, HH, base), Params(theta, g_pct)
Output: PredictionResult

1.  if |W| < 70 then return INSUFFICIENT_DATA
2.  B <- [p.v for p in W[0..59]  if p.good]
3.  P <- [p.v for p in W[60..64] if p.good]
4.  R <- [p.v for p in W[65..69] if p.good]
5.  C <- P + R
6.  valid_ratio <- (|B| + |C|) / 70.0
7.  if valid_ratio < 0.80 or |B| < 30 or |P| == 0 or |R| == 0 then
8.      return INSUFFICIENT_DATA
9.  end if
10. base_avg <- mean(B)
11. slope <- (mean(R) - mean(P)) / 5.0
12. d <- +1 if slope >= 0 else -1
13. m60 <- round( count(x in B : d * (x - base_avg) > 0) * 60 / |B| )
14. m10 <- round( count(x in C : d * (x - base_avg) > 0) * 10 / |C| )
15. if m60 == 0 then n10 <- (999 if m10 > 0 else 0) else n10 <- m10 / (m60 / 6.0)
16. fcst10 <- x_now + slope * 10; fcst20 <- x_now + slope * 20; fcst30 <- x_now + slope * 30
17. span <- max(1e-9, H - L); gate_val <- (g_pct / 100.0) * span
18. slope_gate <- (abs(slope) * 30.0 >= gate_val) or (abs(mean(C) - base_avg) >= gate_val)
19. is_drifting <- (n10 >= theta) and slope_gate
20. (slope_ols, r2, band10, band20, band30) <- OLS_95PI(C)
21. ttl <- TimeToLimit(x_now, slope, Limits)
22. if x_now >= H or x_now <= L then state <- EVENT; detector <- FORECAST
23. else if HitsLimit(fcst10, Limits) then state <- T-10; detector <- FORECAST
24. else if HitsLimit(fcst20, Limits) then state <- T-20; detector <- FORECAST
25. else if HitsLimit(fcst30, Limits) then state <- T-30; detector <- FORECAST
26. else if is_drifting then state <- T-30; detector <- DENSITY
27. else state <- NORMAL; detector <- NONE
28. risk <- FusedRiskIndex(x_now, Limits, ttl, n10, theta, slope_gate, state)
29. return PredictionResult
```
- **時間與空間複雜度**：單測點推論 \(O(W)\)（\(W=70\) 固定，無巢狀動態規劃或矩陣反轉），空間 \(O(W)\)。320 測點批次為 \(320 \times O(W) = O(M)\)。

---

## 演算法 3：防抖遲滯鎖存與三層彙整 + 警報狀態機同步

- **對應程式**：`DriftForecastEngine.evaluate()` + `AlarmEngine.evaluatePrediction()` + `evaluatePair()` + `aggregateSystems()`
- **輸入**：各單點原始推論結果、前次鎖存狀態 `latch[tag]`、現有警報清單 `alarms`
- **輸出**：遲滯後狀態、配對狀態、系統健康度及同步更新之 `DRIFT` / `LIMIT` 警報記錄

```text
Algorithm 3: Hysteresis Latch, Pair/System Aggregation & Immediate Sync
Input:  raw_pred, latch[tag], alarms, release_hold=3
Output: latched_pred, pair_summaries, system_summaries

1.  if raw_pred.state in {INSUFFICIENT_DATA, DISABLED} then
2.      delete latch[tag]; return raw_pred
3.  end if
4.  prev <- latch[tag]
5.  if prev is null or rank(raw_pred.state) >= rank(prev.state) then
6.      hold <- (prev.hold + 1) if (prev and prev.state == raw_pred.state) else 1
7.      latch[tag] <- (raw_pred.state, hold, lower_streak=0)
8.      out <- raw_pred
9.  else
10.     streak <- prev.lower_streak + 1
11.     if streak >= release_hold then
12.         latch[tag] <- (raw_pred.state, hold=1, lower_streak=0); out <- raw_pred
13.     else
14.         latch[tag] <- (prev.state, hold=prev.hold+1, lower_streak=streak)
15.         out <- override_state(raw_pred, prev.state)
16.     end if
17. end if
18. AlarmEngine.evaluatePrediction(alarms, sensor, out, ts_now)  // Raise/Escalate/Clear DRIFT
19. On every Modbus config/limit/fault change or tick threshold-crossing:
20.     Sync PredictionResult immediately so Alarm Center & System Prediction remain consistent
21. Aggregate PairLevel (PTS vs PTR per Submain) and SystemLevel (PCW01..PCW08)
22. return (out, pair_summaries, system_summaries)
```
- **時間複雜度**：警報查表透過 Hash Index 為 \(O(1)\)；三層彙整對 80 配對與 8 系統線性掃描 \(O(M)\)（\(M=320\)）。
