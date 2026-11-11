# 實驗可重現性操作手冊 (REPRODUCIBILITY)

任何第三方皆可依下列命令於同一環境完整重現本專案所有單元測試、離線 3,840 場基準試驗、效能基準、瀏覽器自動化巡檢與論文編譯。

## 1. 單元、跨語言對等與 Modbus TCP 整合測試
```bash
cd "/Users/benchen1981/Downloads/Web SCADA Final 20261111/PCW_SCADA_Final_Project"
"../Existing/Code/pcw-poc-v1_merged/venv/bin/pytest" -v system/tests/test_unified_system.py
```

## 2. 離線全廠 3,840 場試驗、Excel 比對與消融分析
```bash
PYTHONPATH=".:system/backend" "../Existing/Code/pcw-poc-v1_merged/venv/bin/python" experiments/run_full_experiments.py
PYTHONPATH=".:system/backend" "../Existing/Code/pcw-poc-v1_merged/venv/bin/python" experiments/benchmark_performance.py
PYTHONPATH=".:system/backend" "../Existing/Code/pcw-poc-v1_merged/venv/bin/python" experiments/ablation_and_sensitivity.py
```

## 3. 本機前後端 + Modbus TCP 伺服器與 11.5 分鐘自動化驗證
```bash
# 編譯前端
(cd system/frontend && npm run build)
# 啟動 FastAPI + Modbus TCP (Port 15020)
(cd system/backend && PCW_MODBUS_PORT=15020 "../../../Existing/Code/pcw-poc-v1_merged/venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8000) &
# 執行 11.5 分鐘全自動瀏覽器巡檢與 Modbus 基準偏差試驗
node scripts/verify_local_rewritten_and_11min.mjs
```

## 4. 線上 Vercel 部署系統全自動測試與 11.5 分鐘試驗
```bash
node scripts/verify_deployed_and_10min.mjs
```

## 5. 論文圖表重建與 LaTeX 正式印刷版 PDF 編譯
```bash
"../Existing/Code/pcw-poc-v1_merged/venv/bin/python" scripts/generate_all_figures.py
(cd thesis && tectonic main.tex)
```

