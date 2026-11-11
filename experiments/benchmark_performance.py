"""Real execution performance benchmarks on Apple M5 / macOS 26.7.3.

Measures:
1. Single-sensor evaluate_window (10,000 calls)
2. Full-plant 320-sensor batch evaluation (500 batches)
3. SQLite prediction_logs 320-row batch insert & query (100 batches)
4. Live Modbus TCP FC03 register read round-trip (100 calls)
"""
from __future__ import annotations

import asyncio
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "system" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.config.topology import build_topology
from app.engine.drift_forecast import DriftForecastEngine, EngineParams, WindowPoint, evaluate_window
from app.modbus.tcp_server import ModbusTcpServer, modbus_tcp_read_registers
from app.simulator.engine import ScadaRuntime


def stats_summary(samples_us: list[float]) -> dict:
    s = sorted(samples_us)
    n = len(s)
    return {
        "samples": n,
        "mean_us": round(statistics.mean(s), 3),
        "median_us": round(statistics.median(s), 3),
        "std_us": round(statistics.stdev(s), 3),
        "p95_us": round(s[int(0.95 * (n - 1))], 3),
        "p99_us": round(s[int(0.99 * (n - 1))], 3),
        "min_us": round(s[0], 3),
        "max_us": round(s[-1], 3),
    }


def main():
    _, _, sensors = build_topology()
    limits = sensors[0].limits
    win = [WindowPoint(1.50 + (0.003 if i % 2 == 0 else -0.003), True) for i in range(60)] + [
        WindowPoint(1.51 + 0.008 * i, True) for i in range(10)
    ]
    params = EngineParams(2.0, 5.0)

    # Warmup
    for _ in range(200):
        evaluate_window("PCW01.Submain01.PTS", win, 1.59, limits, params, "2026-11-11T00:00:00Z")

    # 1. Single-call latency (10,000 calls)
    lat_single = []
    t_all0 = time.perf_counter()
    for _ in range(10_000):
        t0 = time.perf_counter_ns()
        evaluate_window("PCW01.Submain01.PTS", win, 1.59, limits, params, "2026-11-11T00:00:00Z")
        lat_single.append((time.perf_counter_ns() - t0) / 1000.0)
    t_all = time.perf_counter() - t_all0
    single_res = stats_summary(lat_single)
    single_res["throughput_ops_sec"] = round(10_000 / t_all, 1)

    # 2. 320-sensor batch latency (500 batches)
    eng = DriftForecastEngine(release_hold=3)
    lat_batch = []
    t_b0 = time.perf_counter()
    for b in range(500):
        t0 = time.perf_counter_ns()
        for sdef in sensors:
            eng.evaluate(sdef.tag_id, win, 1.59, sdef.limits, params, f"b{b}")
        lat_batch.append((time.perf_counter_ns() - t0) / 1000.0)
    t_b = time.perf_counter() - t_b0
    batch_res = stats_summary(lat_batch)
    batch_res["batch_size"] = 320
    batch_res["throughput_tags_sec"] = round((500 * 320) / t_b, 1)

    # 3. SQLite 320-row write + query latency + 4. Modbus TCP FC03 read latency
    with tempfile.TemporaryDirectory() as tmp:
        rt = ScadaRuntime(db_path=Path(tmp) / "bench.db", seed=123)
        lat_db = []
        for _ in range(100):
            t0 = time.perf_counter_ns()
            rt.evaluate_predictions(record_log=True)
            lat_db.append((time.perf_counter_ns() - t0) / 1000.0)
        db_res = stats_summary(lat_db)

        lat_q = []
        for _ in range(100):
            t0 = time.perf_counter_ns()
            rt.repo.query_prediction_logs(tag_id="PCW01.Submain01.PTS", limit=100)
            lat_q.append((time.perf_counter_ns() - t0) / 1000.0)
        q_res = stats_summary(lat_q)

        async def _bench_modbus():
            srv = ModbusTcpServer(rt.bank, host="127.0.0.1", port=0)
            port = await srv.start()
            lats = []
            try:
                for _ in range(100):
                    t0 = time.perf_counter_ns()
                    await modbus_tcp_read_registers("127.0.0.1", port, 0, 20)
                    lats.append((time.perf_counter_ns() - t0) / 1000.0)
            finally:
                await srv.stop()
            return stats_summary(lats)

        modbus_res = asyncio.run(_bench_modbus())

    out = {
        "single_predict": single_res,
        "batch_320_predict": batch_res,
        "full_320_eval_and_sqlite_insert": db_res,
        "sqlite_query_100_rows": q_res,
        "modbus_tcp_fc03_20regs": modbus_res,
    }
    dest = PROJECT_ROOT / "evidence" / "test_reports" / "performance_benchmarks.json"
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()

