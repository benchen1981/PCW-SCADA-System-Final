# 系統分層架構規格 (SYSTEM_ARCHITECTURE)

本文件區分「已實作並於本機完整驗證之功能」與「需廠務授權現場串接之規劃項目」，嚴格杜絕將規劃中項目宣稱為工廠實機運轉。

## 1. 五層資料與推論架構

1. **Data Source Layer（資料來源層）**
   - *已實作驗證*：本機整合式即時感測器模擬引擎（支援 NORMAL、DRIFT、STEP、SPIKE、BAD_QUALITY、COMM_LOSS 六種物理/故障模式），以及純 Python 非同步 **Modbus TCP Server**（Port `5020`, Unit ID `1`, Function Code `03/06/16`, FLOAT32 CDAB Word-Swap 映射 `40001..40639`）。
   - *規劃中（未接真實廠務設備）*：現場實體 PT/FT/PDT 感測器與廠內 PLC 連線。
2. **Data Management Layer（資料管理與歷史庫層）**
   - *已實作驗證*：記憶體內高頻環形緩衝（1440 分鐘/測點）+ **SQLite Historian** (`data/pcw_scada.db`)，持久化保存 1 分鐘聚合讀值、衍生特徵 (`_BaseAvg60`, `_M60`, `_M10`, `_N10`, `_Slope`, `_Fcst30/20/10`, `_Risk`)、逐感測器預測執行紀錄 (`prediction_logs`) 與操作稽核紀錄 (`audit_log`)。
   - *規劃中*：廠內正式 MS-SQL SCADA Historian。
3. **Inference Layer（即時推論與警報層）**
   - *已實作驗證*：Python (`app/engine/drift_forecast.py`, `alarm_engine.py`) 與 TypeScript (`DriftForecastEngine.ts`, `AlarmEngine.ts`) 雙邊數值完全對等（誤差 `< 1e-9`），每分鐘定期執行並於 Modbus 參數變更、故障注入或跨限事件發生時**即時同步重算**，支援 PT 單點、Submain 供回水配對及 PCW 系統三層級推論。
4. **Result Integration Layer（結果整合與 API 閘道層）**
   - *已實作驗證*：FastAPI REST API (`/api/*`) + WebSocket 即時推流 (`/ws/stream`) + Modbus TCP Holding Registers 回讀驗證。
   - *規劃中*：OPC-UA / SQL-to-SCADA Tag 回寫正式產線 HMI。
5. **HMI Presentation Layer（Web SCADA 操作介面層）**
   - *已實作驗證*：React 19 + TypeScript + Vite + Recharts Web UI，支援高對比黑白印刷風格與 9 大功能頁（含新增配對級診斷視圖與 Modbus 故障注入與紀錄匯出）。

