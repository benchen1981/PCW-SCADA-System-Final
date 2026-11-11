"""Comprehensive verification suite for the rewritten unified PCW SCADA system."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("PCW_MODBUS_PORT", "15029")
os.environ.setdefault("PCW_DB_PATH", str(Path(tempfile.gettempdir()) / "pcw_scada_pytest.db"))

import threading
import time
import urllib.request
import pytest
import uvicorn

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
sys.path.insert(0, str(BACKEND_DIR))

from app.config.topology import build_topology, decode_float32_cdab, encode_float32_cdab
from app.engine.drift_forecast import DriftForecastEngine, EngineParams, WindowPoint, evaluate_window
from app.main import app, runtime
from app.modbus.tcp_server import (
    ModbusRegisterBank,
    ModbusTcpServer,
    modbus_tcp_read_registers,
    modbus_tcp_write_registers,
)
from app.simulator.engine import ScadaRuntime


def test_topology_and_cdab_mapping():
    systems, submains, sensors = build_topology()
    assert len(systems) == 8
    assert len(submains) == 80
    assert len(sensors) == 320
    pts = [s for s in sensors if s.measurement_type == "PRESSURE"]
    fts = [s for s in sensors if s.measurement_type == "FLOW"]
    dps = [s for s in sensors if s.measurement_type == "DP"]
    assert len(pts) == 160
    assert len(fts) == 80
    assert len(dps) == 80
    g4 = [s for s in pts if s.system_id in ("PCW07", "PCW08")]
    assert all(s.limits.baseline == 2.20 and s.limits.high == 2.40 and s.limits.low == 2.00 for s in g4)
    assert sensors[0].register_address == 40001
    assert sensors[-1].register_address == 40639

    for val in (1.50, 1.72, 2.20, 180.5, 0.305):
        r1, r2 = encode_float32_cdab(val)
        decoded = decode_float32_cdab(r1, r2)
        assert abs(decoded - val) < 1e-5


def test_n10_reachability_and_l1_to_l7():
    # Base 60 points: exactly 30 above 1.50 and 30 below 1.50 -> M60 = 30
    base_pts = [WindowPoint(1.50 + (0.005 if i % 2 == 0 else -0.005), True) for i in range(60)]
    # Recent 10 points: P=[1.505..1.515], R=[1.525..1.545] -> all 10 > 1.50 -> M10=10, N10=2.0
    p_pts = [WindowPoint(1.505 + 0.002 * i, True) for i in range(5)]
    r_pts = [WindowPoint(1.525 + 0.004 * i, True) for i in range(5)]
    win = base_pts + p_pts + r_pts
    limits = build_topology()[2][0].limits  # PCW01 PT: L=1.30, H=1.70
    res = evaluate_window("PCW01.Submain01.PTS", win, 1.545, limits, EngineParams(2.0, 5.0), "2026-11-11T00:00:00Z")
    assert res.m60 == 30
    assert res.m10 == 10
    assert res.n10 == pytest.approx(2.0)
    assert res.state == "T-30"
    assert res.detector == "DENSITY"

    # L1 quality gate
    bad_win = [WindowPoint(1.50, i < 50) for i in range(70)]
    res_bad = evaluate_window("PCW01.Submain01.PTS", bad_win, 1.50, limits, EngineParams(2.0, 5.0), "2026-11-11T00:00:00Z")
    assert res_bad.state == "INSUFFICIENT_DATA"

    # L6 hysteresis latch
    eng = DriftForecastEngine(release_hold=3)
    s1 = eng.evaluate("T1", win, 1.545, limits, EngineParams(2.0, 5.0), "t1")
    assert s1.state == "T-30"
    normal_win = [WindowPoint(1.50 + (0.002 if i % 2 == 0 else -0.002), True) for i in range(70)]
    assert eng.evaluate("T1", normal_win, 1.50, limits, EngineParams(2.0, 5.0), "t2").state == "T-30"
    assert eng.evaluate("T1", normal_win, 1.50, limits, EngineParams(2.0, 5.0), "t3").state == "T-30"
    assert eng.evaluate("T1", normal_win, 1.50, limits, EngineParams(2.0, 5.0), "t4").state == "NORMAL"


def test_python_typescript_parity():
    """Verify Python evaluate_window matches TypeScript DriftForecastEngine.ts to < 1e-9."""
    limits = build_topology()[2][0].limits
    cases = [
        ("normal", [WindowPoint(1.50 + (0.003 if i % 2 == 0 else -0.003), True) for i in range(70)], 1.501),
        ("drift_up", [WindowPoint(1.50 + (0.002 if i % 2 == 0 else -0.002), True) for i in range(60)] + [WindowPoint(1.51 + 0.008 * i, True) for i in range(10)], 1.59),
        ("drift_down", [WindowPoint(1.50 + (0.002 if i % 2 == 0 else -0.002), True) for i in range(60)] + [WindowPoint(1.49 - 0.008 * i, True) for i in range(10)], 1.41),
        ("event_high", [WindowPoint(1.50, True) for _ in range(70)], 1.72),
        ("bad_quality", [WindowPoint(1.50, i % 2 == 0) for i in range(70)], 1.50),
    ]
    ts_payload = [
        {"name": name, "window": [{"v": p.v, "good": p.good} for p in win], "cur": cur, "limits": limits.to_dict()}
        for name, win, cur in cases
    ]
    node_script = f"""
import {{ evaluateWindow }} from './src/services/analytics/DriftForecastEngine.ts';
const cases = {json.dumps(ts_payload)};
const out = cases.map(c => evaluateWindow('PCW01.Submain01.PTS', c.window, c.cur, c.limits, {{ sensitivity: 2, slopeGatePct: 5 }}, '2026-11-11T00:00:00Z'));
console.log(JSON.stringify(out));
"""
    proc = subprocess.run(
        ["node", "--experimental-strip-types", "--input-type=module", "-e", node_script],
        cwd=str(FRONTEND_DIR),
        capture_output=True,
        text=True,
        check=True,
    )
    ts_results = json.loads(proc.stdout.strip())
    for (name, win, cur), ts_r in zip(cases, ts_results):
        py_r = evaluate_window("PCW01.Submain01.PTS", win, cur, limits, EngineParams(2.0, 5.0), "2026-11-11T00:00:00Z")
        assert py_r.state == ts_r["state"], f"State mismatch on {name}"
        assert py_r.detector == ts_r["detector"]
        assert abs(py_r.base_avg_60 - ts_r["baseAvg60"]) < 1e-9
        assert abs(py_r.slope - ts_r["slope"]) < 1e-9
        assert abs(py_r.n10 - ts_r["n10"]) < 1e-9
        assert abs(py_r.forecast30 - ts_r["forecast30"]) < 1e-9
        assert abs(py_r.slope_ols - ts_r.get("slopeOls", 0.0)) < 1e-9
        assert abs(py_r.band30 - ts_r.get("band30", 0.0)) < 1e-9


def test_state_consistency_and_ten_minute_deviation(tmp_path: Path):
    rt = ScadaRuntime(db_path=tmp_path / "test.db", seed=42)
    # 1. Verify immediate consistency when PCW01.Submain01.PTS = 1.72 (> HI=1.70)
    rt.update_simulator_config(["PCW01.Submain01.PTS"], base_value=1.72, noise=0.0)
    high_alarms = [a for a in rt.alarms if a.tag_id == "PCW01.Submain01.PTS" and a.alarm_type == "HIGH" and a.state.startswith("ACTIVE")]
    assert len(high_alarms) == 1
    assert rt.predictions["PCW01.Submain01.PTS"].state == "EVENT"

    # Reset and run 12-minute behavioral deviation on PCW01.Submain02.PTS (base 1.50 -> 1.62, inside HI=1.70)
    rt.set_control("RESET")
    rt.update_simulator_config(["PCW01.Submain02.PTS"], base_value=1.62, noise=0.005)
    rt.advance_minutes(12, ticks_per_minute=10)
    p = rt.predictions["PCW01.Submain02.PTS"]
    assert p.state in ("T-30", "T-20", "T-10")
    drift_alarms = [a for a in rt.alarms if a.tag_id == "PCW01.Submain02.PTS" and a.alarm_type == "DRIFT" and a.state.startswith("ACTIVE")]
    assert len(drift_alarms) == 1
    log_summary = rt.repo.count_prediction_logs()
    assert log_summary["uniqueTags"] == 320
    assert log_summary["totalRows"] >= 320 * 12


def test_modbus_tcp_wire_roundtrip(tmp_path: Path):
    async def _run():
        rt = ScadaRuntime(db_path=tmp_path / "mb.db", seed=7)
        srv = ModbusTcpServer(rt.bank, host="127.0.0.1", port=0)
        port = await srv.start()
        try:
            # Read PCW01.Submain01.PTS (40001 -> offset 0, 2 regs)
            regs = await modbus_tcp_read_registers("127.0.0.1", port, 0, 2)
            val = decode_float32_cdab(regs[0], regs[1])
            assert abs(val - 1.50) < 0.05

            # Write 1.73 via FC16 and verify immediate alarm + prediction sync
            w_regs = list(encode_float32_cdab(1.73))
            await modbus_tcp_write_registers("127.0.0.1", port, 0, w_regs)
            assert abs(rt.sensors["PCW01.Submain01.PTS"].value - 1.73) < 1e-4
            assert rt.predictions["PCW01.Submain01.PTS"].state == "EVENT"
        finally:
            await srv.stop()

    asyncio.run(_run())


def _http_json(url: str, body: dict | None = None) -> dict | list:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if body is not None else "GET")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def test_fastapi_endpoints():
    runtime.set_control("RESET")
    config = uvicorn.Config(app, host="127.0.0.1", port=18088, log_level="error")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    try:
        for _ in range(30):
            try:
                h = _http_json("http://127.0.0.1:18088/api/health")
                break
            except Exception:
                time.sleep(0.1)
        else:
            raise AssertionError("Uvicorn server failed to start")

        assert h["sensorCount"] == 320
        assert h["ptCount"] == 160

        snap = _http_json("http://127.0.0.1:18088/api/snapshot")
        assert len(snap["systems"]) == 8
        assert len(snap["pairs"]) == 80
        assert len(snap["sensors"]) == 320
        assert len(snap["predictions"]) == 320

        _http_json("http://127.0.0.1:18088/api/simulator/config", {"tagIds": ["PCW01.Submain01.PTS"], "baseValue": 1.72, "noise": 0.0})
        preds = _http_json("http://127.0.0.1:18088/api/predictions?systemId=PCW01")
        p_map = {x["tagId"]: x for x in preds}
        alarms = _http_json("http://127.0.0.1:18088/api/alarms")
        assert p_map["PCW01.Submain01.PTS"]["state"] == "EVENT"
        assert any(a["tagId"] == "PCW01.Submain01.PTS" and a["alarmType"] == "HIGH" for a in alarms)
        _http_json("http://127.0.0.1:18088/api/simulator/control", {"action": "RESET"})
    finally:
        server.should_exit = True
        t.join(timeout=3)
