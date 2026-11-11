# 論文修訂與正式排版檢查報告 (THESIS_REVISION_REPORT)

- **輸出論文專案**：`PCW_SCADA_Final_Project/thesis/main.tex`、`thesis/refs.bib`、`thesis/main.pdf`
- **編譯器與版本**：Tectonic 0.17.0 (`xelatex` 相容引擎，A4 規格，`kaiu.ttf` + `Times New Roman`，3cm 邊界)

## 1. 主要修訂項目

1. **對齊真實系統規格**：修正第一章測點數量（320 測點：160 PT + 80 FT + 80 PDT，刪除不存在之 80 TT）與 Group 4 基準（$2.20\ \mathrm{bar}$），並將 Modbus 暫存器映射更正為 FLOAT32 CDAB (`40001..40639`)。
2. **重寫第三章研究方法（含 Excel 初版模型數學解析與雙模型分離推導）**：以獲教授認可之 `Existing/PCW_T30_T20_T10_FINAL_ROLLBACK_THESIS_VERIFICATION.xlsx` 為開發基礎，於第三章 §3.3–§3.6 明確拆分並詳列系統解決之兩大核心數學問題——**偏移偵測模型（Drift Detection：`BaseAvg60`, `M60/M10`, `N10`, `Gate30/20/10` 及其雙向泛化 / `N10>=theta` / L2 跨度水準偏移閘門）**與**趨勢預測模型（Trend Forecast：`Prev5Avg/Recent5Avg`, `Slope/min`, `Forecast_h`, `Pred_T30/T20/T10` 及其雙向斜率 / 10 點 OLS 95% 預測區間 / 閉式 TTL / L3–L7）**，新增公式對照表 `表 3-2`（`tab:excel_to_program_map`）與因果隔離/離線評估數學定義；同時移除舊稿未實作之 Darcy-Weisbach 阻力演算法、二項檢定 ($p_0=0.05$) 與虛構濾波描述。
3. **文獻徹底稽核與淨化**：經 Crossref API 實查後刪除 6 筆虛構或 DOI 錯置之書目，僅保留並擴充 7 筆經核驗之真實文獻 (`isa1822016`, `montgomery2020statistical`, `roberts1959control`, `kaufman2012leakage`, `darcy1857recherches`, `colebrook1939turbulent`, `modbus2006spec`)。
4. **全面更換最新圖表與系統截圖**：全篇 14 張圖與 5 張表均於 2026-11-11 重新產生、擷取或數學對照定稿（無任何沿用舊圖），逐張於正文先行引用說明且載明 `figure_table_register.csv`。
5. **排版、公式口試簡化與正式印刷品質檢核**：依口試需求於第三章 `§3.3–§3.6` 全面簡化集合與統計符號、直接嵌入五大「【口試備註】」白話應答解析並另提供 [`thesis/oral_defense_notes.md`](../thesis/oral_defense_notes.md)；同時消除所有 `Overfull \hbox` 跨欄溢位與未定義引用警告，`Abstract` 單頁收斂。最終輸出 `thesis/main.pdf` 共 **36 頁**（`3.81 MiB`，含前頁羅馬編碼與正文，ZERO Overfull/Undefined warnings）。
