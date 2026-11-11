# 參考文獻真實性查核報告 (citation_audit)

- **稽核對象**：`Existing/thesis/refs 20261109.bib` 與 `Existing/Output 20261110 2330/PCW_碩士論文_實測修正版_20261110.tex`
- **稽核方法**：透過 Crossref REST API (`https://api.crossref.org/works/{doi}`) 與書目資料實地核驗每筆文獻與 DOI 之真實存在性及標題一致性。

| BibTeX Key | 原記載 DOI / 出版資訊 | Crossref 查核結果 | 處置決定 |
|---|---|---|---|
| `caballero2026predictive` | `10.1109/TII.2025.3401122` (IEEE TII 2026) | **HTTP 404 Not Found（虛構文獻與 DOI）** | **永久刪除** |
| `li2024prognostics` | `10.1109/TSM.2023.3328901` (IEEE TSM 2024) | **HTTP 404 Not Found（虛構文獻與 DOI）** | **永久刪除** |
| `smith2021facility` | `10.1109/TASE.2020.3021145` (IEEE TASE 2021) | **HTTP 404 Not Found（虛構文獻與 DOI）** | **永久刪除** |
| `wang2025microsecond` | `10.1109/TIE.2024.3398711` (IEEE TIE 2025) | **HTTP 404 Not Found（虛構文獻與 DOI）** | **永久刪除** |
| `lin2023hydraulic` | `10.1016/j.jprocont.2023.01.008` | **DOI 錯置/偽造**：實際對應 *"Pseudo feedforward dynamic matrix control algorithm..."*，非半導體 PCW 文獻 | **永久刪除** |
| `zhang2022realtime` | `10.1016/j.compchemeng.2021.107568` | **DOI 錯置/偽造**：實際對應 *"Coordinated markets for furfural and levulinic acid..."*，非管線洩漏文獻 | **永久刪除** |
| `kaufman2012leakage` | `10.1145/2382577.2382579` (ACM TKDD 2012) | **VERIFIED**：*Leakage in data mining: Formulation, detection, and avoidance* | **保留引用** |
| `colebrook1939turbulent` | `10.1680/ijoti.1939.13150` (J. Inst. Civil Eng. 1939) | **VERIFIED**：*Turbulent flow in pipes...* | **保留引用**（僅於背景說明引用） |
| `darcy1857recherches` | *Mémoires... Académie des sciences*, vol. 14, 1857 | **VERIFIED**：經典達西水力文獻 | **保留引用**（僅於背景說明引用） |
| `montgomery2020statistical` | *Introduction to Statistical Quality Control*, 8th ed., Wiley, 2020 | **VERIFIED**：標準 SPC 教科書 (EWMA/CUSUM) | **保留引用** |
| `isa1822016` | ANSI/ISA-18.2-2016 *Management of Alarm Systems for the Process Industries* | **VERIFIED**：ISA 工業警報生命週期標準 | **保留引用** |
| `roberts1959control` | `10.1080/00401706.1959.10489860` (Technometrics, 1959, 1(3):239-250) | **VERIFIED (Crossref)**：S. W. Roberts, *Control Chart Tests Based on Geometric Moving Averages* | **新增驗證引用 (EWMA 原始出處)** |
| `modbus2006spec` | Modbus Messaging on TCP/IP Implementation Guide v1.0b (2006) | **VERIFIED**：Modbus Organization 官方技術規範 | **新增驗證引用 (Modbus/TCP 協定)** |
