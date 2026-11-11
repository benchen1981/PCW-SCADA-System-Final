# 正式數學定義與推導 (MATHEMATICAL_FORMULATION)

本文件嚴格依據實際實作程式碼 (`DriftForecastEngine.ts` 與 `drift_forecast.py`) 定義所有數學符號、單位、邊界條件與三層彙整規則，未包含任何未實作公式。

## 1. 時間序列與因果滑動視窗 (Past-Only Window)

令第 \(i \in \{1,\dots,320\}\) 個感測器於離散分鐘時間步 \(t \in \mathbb{Z}\)（取樣間隔 \(\Delta t = 1\ \mathrm{min}\)）的 1 分鐘聚合量測值為：
\[
x_i(t) \in \mathbb{R}, \qquad q_i(t) \in \{\mathrm{GOOD}, \mathrm{UNCERTAIN}, \mathrm{BAD}, \mathrm{COMM\_LOSS}\}
\]
其中 \(x_i(t)\) 為該分鐘區間 \([t-1, t)\) 內所有 `GOOD` 高頻樣本之算術平均；若 `GOOD` 比例低於 \(50\%\)，則該分鐘品質標記為 `BAD` 或 `COMM_LOSS`。

在推論時刻 \(t\)，定義長度 \(W = 70\) 分鐘之 **Past-Only 因果視窗**（不含未來資料 \(t+\tau, \tau > 0\)）：
\[
\mathcal{W}_i(t) = \bigl\{\, (x_i(t-k),\, q_i(t-k)) \;\big|\; k = 1, 2, \dots, 70 \,\bigr\}
\]
（註：為與 0-based 陣列索引一致，將舊至新排列之 70 點記為 \(w_0, w_1, \dots, w_{69}\)，並切分為三個互斥子區間）：
- 歷史基準視窗：\(\mathcal{B}_i(t) = \{w_k : 0 \le k \le 59 \land q(w_k)=\mathrm{GOOD}\}\)（對應 \([t-70, t-10)\)）
- 前期局部視窗：\(\mathcal{P}_i(t) = \{w_k : 60 \le k \le 64 \land q(w_k)=\mathrm{GOOD}\}\)（對應 \([t-10, t-5)\)）
- 近期局部視窗：\(\mathcal{R}_i(t) = \{w_k : 65 \le k \le 69 \land q(w_k)=\mathrm{GOOD}\}\)（對應 \([t-5, t)\)）
- 近期合併視窗：\(\mathcal{C}_i(t) = \mathcal{P}_i(t) \cup \mathcal{R}_i(t)\)

### Layer 1: 品質閘門 (Quality Gate)
定義整體視窗有效率 \(\rho_{\mathrm{valid}}(t) = \frac{|\mathcal{B}_i(t)| + |\mathcal{C}_i(t)|}{70}\)。若滿足下列任一條件：
\[
|\mathcal{W}_i(t)| < 70 \quad\lor\quad \rho_{\mathrm{valid}}(t) < 0.80 \quad\lor\quad |\mathcal{B}_i(t)| < 30 \quad\lor\quad |\mathcal{P}_i(t)| = 0 \quad\lor\quad |\mathcal{R}_i(t)| = 0
\]
則模型判定為 `INSUFFICIENT_DATA`（停止推論與報警，避免垃圾進、垃圾出）。

## 2. 歷史基準統計量與方向性斜率估計

歷史基準平均值 \(B_i(t)\) 定義為歷史視窗內有效點之算術平均：
\[
B_i(t) = \frac{1}{|\mathcal{B}_i(t)|} \sum_{x \in \mathcal{B}_i(t)} x
\]

兩視窗有限差分斜率（單位：\(\mathrm{bar/min}\) 或 \(\mathrm{LPM/min}\)）：
\[
\bar{x}_{P,i}(t) = \frac{1}{|\mathcal{P}_i(t)|}\sum_{x \in \mathcal{P}_i(t)} x, \qquad
\bar{x}_{R,i}(t) = \frac{1}{|\mathcal{R}_i(t)|}\sum_{x \in \mathcal{R}_i(t)} x
\]
\[
\hat{\beta}_i(t) = \frac{\bar{x}_{R,i}(t) - \bar{x}_{P,i}(t)}{5}
\]
其餘兩個視窗中心距為 5 分鐘，相較相鄰單點一階差分 \(x_i(t)-x_i(t-1)\)，五點均差可將獨立高斯雜訊標準差縮減 \(\sqrt{2/5} \approx 0.632\) 倍。

定義方向指示變數 \(d_i(t) \in \{+1, -1\}\)：
\[
d_i(t) = \begin{cases} +1, & \text{if } \hat{\beta}_i(t) \ge 0 \\ -1, & \text{if } \hat{\beta}_i(t) < 0 \end{cases}
\]

## 3. 雙視窗異常密度指標 (Anomaly Density Ratio, \(N_{10}\))

計算相對於歷史基準 \(B_i(t)\) 的同向偏移計數（當部分資料遭品質閘門剔除時，依比例還原至滿窗尺度 60 與 10）：
\[
M_{60,i}(t) = \operatorname{round}\!\left(\frac{60}{|\mathcal{B}_i(t)|}\sum_{x \in \mathcal{B}_i(t)} \mathbb{I}\!\bigl(d_i(t)\cdot(x - B_i(t)) > 0\bigr)\right)
\]
\[
M_{10,i}(t) = \operatorname{round}\!\left(\frac{10}{|\mathcal{C}_i(t)|}\sum_{x \in \mathcal{C}_i(t)} \mathbb{I}\!\bigl(d_i(t)\cdot(x - B_i(t)) > 0\bigr)\right)
\]
標準化異常密度比 \(N_{10,i}(t)\) 定義為近期 10 分鐘同向偏離次數相對於過去 60 分鐘每 10 分鐘期望偏離次數 \((M_{60,i}(t)/6)\) 之比值：
\[
N_{10,i}(t) = \begin{cases}
\dfrac{M_{10,i}(t)}{M_{60,i}(t) / 6}, & M_{60,i}(t) > 0 \\[8pt]
999, & M_{60,i}(t) = 0 \land M_{10,i}(t) > 0 \\
0, & M_{60,i}(t) = 0 \land M_{10,i}(t) = 0
\end{cases}
\]

### Layer 2: 跨度歸一化漂移閘門 (Span-Normalized Drift Gate)
令工程正常操作跨度 \(S_i = H_i - L_i > 0\)，近期 10 分鐘平均偏移量 \(\Delta \mu_{10,i}(t) = \left|\frac{1}{|\mathcal{C}_i(t)|}\sum_{x \in \mathcal{C}_i(t)} x - B_i(t)\right|\)。為同時捕捉斜坡變化與長達 10 分鐘以上之持續性基準偏移（Level Shift），且確保各物理單位具備一致尺度不變性，要求 30 分鐘預期趨勢偏移或近期水準偏移任一項達到跨度比例 \(g\%\)（預設 \(g = 5\%\)）：
\[
\mathrm{Excursion}_{30,i}(t) = |\hat{\beta}_i(t)| \cdot 30, \qquad
\mathrm{Gate}_i(t) \iff \left(\mathrm{Excursion}_{30,i}(t) \ge \frac{g}{100} S_i\right) \lor \left(\Delta \mu_{10,i}(t) \ge \frac{g}{100} S_i\right)
\]
\[
\mathrm{IsDrifting}_i(t) \iff \bigl(N_{10,i}(t) \ge \theta\bigr) \land \mathrm{Gate}_i(t)
\]
（註：採用 \(N_{10,i}(t) \ge \theta\) 修正當對稱雜訊使 \(M_{60}=30\) 時 \(N_{10}=2.0\) 不可達之問題。）

## 4. 多視域外推、OLS 信賴區間與到限時間 (TTL)

對未來視域 \(h \in \{10, 20, 30\}\ \mathrm{min}\)，以當前即時值 \(x_i^{\mathrm{now}}\) 外推：
\[
\hat{x}_i(t + h) = x_i^{\mathrm{now}} + \hat{\beta}_i(t) \cdot h
\]

### Layer 3: 近 10 點 OLS 線性趨勢與 95% 預測區間
令近期有效觀測序列 \(Y = (y_0, \dots, y_{n-1})\)，\(n = |\mathcal{C}_i(t)|\)，時間索引 \(\bar{u} = (n-1)/2\)：
\[
S_{uu} = \sum_{k=0}^{n-1}(k - \bar{u})^2, \qquad
\hat{\beta}_{\mathrm{OLS}} = \frac{\sum_{k=0}^{n-1}(k - \bar{u})(y_k - \bar{y})}{S_{uu}}, \qquad
\hat{\alpha}_{\mathrm{OLS}} = \bar{y} - \hat{\beta}_{\mathrm{OLS}}\bar{u}
\]
\[
\mathrm{SSE} = \sum_{k=0}^{n-1}\bigl(y_k - (\hat{\alpha}_{\mathrm{OLS}} + \hat{\beta}_{\mathrm{OLS}}k)\bigr)^2, \qquad
R^2 = \operatorname{clamp}_{[0,1]}\!\left(1 - \frac{\mathrm{SSE}}{\mathrm{SST}}\right), \qquad
s_e = \sqrt{\frac{\mathrm{SSE}}{\max(1, n-2)}}
\]
當 \(n \ge 3\) 且 \(S_{uu} > 0\)，第 \(h\) 分鐘之 Student-\(t\)（雙尾 95%，自由度 \(n-2=8\) 時 \(t_{0.975,8}=2.306\)）預測區間半寬為：
\[
\delta_h = t_{0.975,8} \cdot s_e \sqrt{1 + \frac{1}{n} + \frac{(n - 1 + h - \bar{u})^2}{S_{uu}}}
\]

### Layer 4: 預估到限時間 (Time-To-Limit, TTL)
定義斜率閾值 \(|\hat{\beta}_i(t)| \ge 10^{-12}\)。若 \(\hat{\beta}_i(t) > 0\) 朝上限序列 \((H_i, HH_i)\) 移動，或 \(\hat{\beta}_i(t) < 0\) 朝下限序列 \((L_i, LL_i)\) 移動，取第一個尚未跨越的目標界限 \(U^*\)：
\[
\mathrm{TTL}_i(t) = \begin{cases}
\dfrac{U^* - x_i^{\mathrm{now}}}{\hat{\beta}_i(t)}, & \text{若 } 0 < \dfrac{U^* - x_i^{\mathrm{now}}}{\hat{\beta}_i(t)} \le 1440\ \mathrm{min} \\[8pt]
0, & \text{若方向上所有界限皆已跨越} \\
\mathrm{null}, & \text{若斜率為零、大於 1440 分鐘或方向背離}
\end{cases}
\]

## 5. 狀態判定、遲滯鎖存與融合風險指標

### Layer 5: 預警與工程事件分離
1. **已超限事件 (`EVENT`)**：若 \(x_i^{\mathrm{now}} \ge H_i\) 或 \(x_i^{\mathrm{now}} \le L_i\)，直接判定 `EVENT`（非早期預警，供計算 KPI 時嚴格區分預警與硬警報）。
2. **預警分級**：若未超限，依 \(\hat{x}_i(t+10)\) 觸及 \(H_i/L_i/HH_i/LL_i \implies \text{T-10}\)；否則 \(\hat{x}_i(t+20)\) 觸及 \(\implies \text{T-20}\)；否則 \(\hat{x}_i(t+30)\) 觸及 \(\implies \text{T-30}\)；否則 \(\mathrm{IsDrifting}_i(t) \implies \text{T-30}\)（行為偏移）；其餘為 `NORMAL`。

### Layer 6: 防抖遲滯鎖存 (Hysteresis Latch, ISA-18.2 精神)
令嚴重度排序 \(\operatorname{rank}(\mathrm{NORMAL})=0 < \mathrm{T\text{-}30}=1 < \mathrm{T\text{-}20}=2 < \mathrm{T\text{-}10}=3 < \mathrm{EVENT}=4\)。
- **升級即時**：若 \(\operatorname{rank}(S_{\mathrm{raw}}) \ge \operatorname{rank}(S_{\mathrm{prev}})\)，立即輸出 \(S_{\mathrm{raw}}\) 並重置降級計數器 `lowerStreak = 0`。
- **降級延遲**：若 \(\operatorname{rank}(S_{\mathrm{raw}}) < \operatorname{rank}(S_{\mathrm{prev}})\)，僅當連續 `releaseHold`（預設 3）次評估皆低於鎖存狀態時才解除，否則維持原鎖存狀態，防止邊界抖動。

### Layer 7: 融合風險指標 \(R_i(t) \in [0, 100]\)
令中心點 \(c_i = \mathrm{baseline}_i\)，則：
\[
f_{\mathrm{margin}} = \operatorname{clamp}_{[0,1]}\!\left(\frac{|x_i^{\mathrm{now}} - c_i|}{S_i / 2}\right), \quad
f_{\mathrm{TTL}} = \begin{cases} \operatorname{clamp}_{[0,1]}(1 - \mathrm{TTL}_i/60), & \mathrm{TTL}_i \ne \mathrm{null} \\ 0, & \text{otherwise} \end{cases}
\]
\[
f_{\mathrm{density}} = \operatorname{clamp}_{[0,1]}\!\left(\frac{N_{10,i}}{\theta}\right)\cdot \mathbb{I}_{\mathrm{gate}}, \qquad
R_i(t) = \operatorname{round}\!\Bigl(\max\bigl(\mathrm{floor}(S_i),\; 100\,(0.4 f_{\mathrm{margin}} + 0.4 f_{\mathrm{TTL}} + 0.2 f_{\mathrm{density}})\bigr)\Bigr)
\]
其中狀態保底分數 \(\mathrm{floor} = \{\mathrm{EVENT}:100,\, \mathrm{T\text{-}10}:85,\, \mathrm{T\text{-}20}:70,\, \mathrm{T\text{-}30}:50,\, \mathrm{NORMAL}:0\}\)，且 `NORMAL` 狀態上界截斷為 `49`。

## 6. 三層彙整定義 (PT Sensor / Pair / PCW System)

1. **PT Sensor Level**：單點 `PTS` 或 `PTR` 依上述公式獨立輸出 `PredictionResult`。
2. **Supply / Return Pair Level (`Submain` 層級)**：對同一分支 `PCWxx.Submainyy` 之供水 \(P_S\) (`PTS`) 與回水 \(P_R\) (`PTR`)：
   - 量測壓差 \(\Delta P_{\mathrm{pair}} = P_S - P_R\)
   - 分支預警嚴重度 \(S_{\mathrm{pair}} = \arg\max_{s \in \{\mathrm{PTS}, \mathrm{PTR}\}} \operatorname{rank}(S_s)\)
   - 協同診斷標籤：`COUPLED_DRIFT`（供回水雙側同時出現非 NORMAL 偏移或預警）、`SUPPLY_ONLY`（僅供水側偏移）、`RETURN_ONLY`（僅回水側偏移）、`NORMAL`（雙側正常）。不假設「供回水搶水」。
3. **PCW System Level (`PCW01`–`PCW08`)**：彙整所屬 10 組 Submain 與 40 支感測器：
   - 統計供/回水壓力 `(min, avg, max)`、平均壓差 \(\overline{\Delta P}\)、預警感測器數 `driftSensorCount`、作用中工程警報數 `activeAlarmCount`。
   - 系統健康度：`CRITICAL`（含任何 `CRITICAL` 警報）、`WARNING`（含活動警報或任一測點處於 `T-30`/`T-20`/`T-10`/`EVENT`）、其餘為 `HEALTHY`。
