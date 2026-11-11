# 實驗軟硬體與執行環境規格 (ENVIRONMENT)

所有資訊均於 **2026-11-11** 透過系統指令探測並記錄於 `evidence/environment/baseline_probe.txt`。

| 類別 | 實測規格與版本 | 驗證指令 / 來源 |
|---|---|---|
| **Hardware** | Apple M5 (10 cores), 16 GiB RAM (`17,179,869,184` bytes), Apple ARM64 | `sysctl -n machdep.cpu.brand_string hw.ncpu hw.memsize` |
| **OS** | macOS 26.7.3 (Build 25G342), Darwin Kernel 25.6.0 (`arm64`) | `sw_vers && uname -a` |
| **Runtime (Python)** | Python 3.9.6 (CPython 64-bit), FastAPI 0.115.0, Uvicorn 0.30.6, NumPy 2.0.2, OpenPyXL 3.1.5, Matplotlib 3.9.4, Pytest 8.3.3 | `venv/bin/python --version`, `venv/bin/pip list` |
| **Runtime (Node/TS)** | Node.js v24.14.1, npm 11.11.0, TypeScript ~6.0.2, Vite 8.3.0 | `node --version`, `npm --version` |
| **Frontend** | React 19.2.8, React Router DOM 7.18.4, Zustand 5.0.15, Recharts 3.10.1 | `system/frontend/package.json` |
| **Database** | SQLite 3 (WAL mode, `system/backend/data/pcw_scada.db`) + 記憶體內環形緩衝 `HistorianStore` (1,440 raw / 720 feature) | `system/backend/app/database/sqlite_repo.py` |
| **Protocol** | Modbus/TCP (IPv4 `127.0.0.1:15020`, Unit ID 1, FC03/FC06/FC16, IEEE-754 FLOAT32 CDAB Word-Swap, 640 registers `40001..40639`) | `system/backend/app/modbus/tcp_server.py` |
| **Dataset 1 (歷史回放)** | `PCW_T30_T20_T10_FINAL_ROLLBACK_THESIS_VERIFICATION.xlsx` (`RawData` 工作表, `PT-1`, 480 分鐘, 2026-08-05 03:01–11:00) | `Existing/PCW_T30_T20_T10_FINAL_ROLLBACK_THESIS_VERIFICATION.xlsx` |
| **Dataset 2 (全廠受控注入)** | 320 測點 (`160 PT + 80 FT + 80 PDT`) × 12 情境 = 3,840 場固定種子受控時間序列（含 160 PT × 12 = 1,920 場） | `experiments/run_full_experiments.py` |
| **Web Verification** | Google Chrome 157.0.8103.40 + Puppeteer 25.13.0，連線至線上版 `https://pcw-scada-system.vercel.app/` 與本機重構版 `http://127.0.0.1:8000/` | `scripts/verify_deployed_and_10min.mjs`, `scripts/verify_local_rewritten_and_11min.mjs` |
| **Typesetting** | Tectonic 0.17.0 (`xelatex` 相容引擎, `kaiu.ttf` + `Times New Roman`) | `tectonic --version` |

