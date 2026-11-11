"""FastAPI backend + Modbus TCP Server + WebSocket real-time stream for PCW SCADA."""
from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.modbus.tcp_server import ModbusTcpServer
from app.simulator.engine import FaultScenario, ScadaRuntime

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DATA_DB = Path(os.environ.get("PCW_DB_PATH", str(BACKEND_ROOT / "data" / "pcw_scada.db")))
MODBUS_HOST = os.environ.get("PCW_MODBUS_HOST", "127.0.0.1")
MODBUS_PORT = int(os.environ.get("PCW_MODBUS_PORT", "15020"))

runtime = ScadaRuntime(db_path=DATA_DB)
modbus_server = ModbusTcpServer(runtime.bank, host=MODBUS_HOST, port=MODBUS_PORT)
ws_clients: set[WebSocket] = set()
sse_queues: set[asyncio.Queue] = set()
_ticker_task: Optional[asyncio.Task] = None


async def _simulation_loop() -> None:
    while True:
        try:
            if runtime.is_running:
                runtime.process_tick()
                if ws_clients or sse_queues:
                    payload = build_snapshot_payload()
                    payload["type"] = "SNAPSHOT_PUSH"
                    if ws_clients:
                        stale = []
                        for ws in list(ws_clients):
                            try:
                                await ws.send_json(payload)
                            except Exception:
                                stale.append(ws)
                        for ws in stale:
                            ws_clients.discard(ws)
                    if sse_queues:
                        raw_msg = json.dumps(payload)
                        for q in list(sse_queues):
                            if q.full():
                                try:
                                    q.get_nowait()
                                except asyncio.QueueEmpty:
                                    pass
                            await q.put(raw_msg)
            await asyncio.sleep(max(0.1, runtime.update_interval_ms / 1000.0))
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(1.0)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _ticker_task
    await modbus_server.start()
    _ticker_task = asyncio.create_task(_simulation_loop())
    yield
    if _ticker_task:
        _ticker_task.cancel()
        try:
            await _ticker_task
        except asyncio.CancelledError:
            pass
    await modbus_server.stop()


app = FastAPI(title="PCW Predictive Web SCADA API", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class ControlPayload(BaseModel):
    action: str
    intervalMs: Optional[int] = None


class SimConfigPayload(BaseModel):
    tagIds: List[str]
    baseValue: Optional[float] = None
    noise: Optional[float] = None


class FaultPayload(BaseModel):
    tagIds: List[str]
    scenario: FaultScenario
    driftRatePerMin: float = 0.0
    stepOffset: float = 0.0
    spikeAmplitude: float = 0.0
    spikeProbability: float = 0.05


class LimitsPayload(BaseModel):
    tagIds: List[str]
    limits: dict


class PredictionTogglePayload(BaseModel):
    type: str
    id: str
    enabled: bool


class PredictionTuningPayload(BaseModel):
    sensitivity: Optional[float] = None
    slopeGatePct: Optional[float] = None
    releaseHold: Optional[int] = None
    rawOnset: Optional[int] = None
    tagId: Optional[str] = None
    sensorSensitivity: Optional[float] = None


@app.get("/api/health")
def health():
    log_summary = runtime.repo.count_prediction_logs()
    return {
        "status": "ok",
        "version": app.version,
        "modbusHost": MODBUS_HOST,
        "modbusPort": modbus_server.port,
        "sensorCount": len(runtime.sensors),
        "ptCount": sum(1 for d in runtime.sensor_defs if d.measurement_type == "PRESSURE"),
        "predictionConfig": runtime.prediction_config,
        "sqlitePredictionRows": log_summary.get("totalRows", 0),
        "sqliteUniqueTags": log_summary.get("uniqueTags", 0),
        "streamClients": len(ws_clients) + len(sse_queues),
    }


def build_snapshot_payload() -> dict:
    """Build single-roundtrip synchronized SCADA state for WebSocket push and REST snapshot."""
    with runtime.lock:
        return {
            "systems": runtime.get_systems_summary(),
            "submains": [
                {
                    "systemId": sm.system_id,
                    "submainId": sm.submain_id,
                    "canonicalName": sm.canonical_name,
                    "displayName": sm.display_name,
                    "supplyTags": list(sm.supply_tags),
                    "returnTags": list(sm.return_tags),
                    "pressureDifferential": round(
                        runtime.sensors[sm.supply_tags[0]].value - runtime.sensors[sm.return_tags[0]].value, 4
                    ),
                    "status": "NORMAL",
                    "alarmState": "NONE",
                    "lastUpdateTime": runtime._iso(),
                }
                for sm in runtime.submain_defs
            ],
            "pairs": runtime.get_pair_summaries(),
            "sensors": [runtime.sensors[d.tag_id].to_camel_dict() for d in runtime.sensor_defs],
            "alarms": [
                a.to_camel_dict()
                for a in runtime.alarms
                if a.state.startswith("ACTIVE") or a.state in ("CLEARED_UNACK", "SHELVED")
            ],
            "predictions": [runtime.predictions[d.tag_id].to_camel_dict() for d in runtime.sensor_defs],
            "predictionConfig": runtime.prediction_config,
            "modbus": runtime.modbus_meta,
            "modbusMap": [
                {
                    "registerAddress": d.register_address,
                    "tagId": d.tag_id,
                    "dataType": "FLOAT32",
                    "unit": d.unit,
                    "scale": d.scale,
                    "min": d.limits.low_low,
                    "max": d.limits.high_high,
                    "access": "READ_WRITE",
                    "source": "MODBUS_TCP_SERVER",
                }
                for d in runtime.sensor_defs
            ],
            "simulatorConfigs": {k: v.to_camel_dict() for k, v in runtime.sim_configs.items()},
            "simulatorStatus": runtime.get_status(),
            "modbusWriteLog": runtime.modbus_write_log[-100:],
            "sqliteStats": runtime.repo.count_prediction_logs(),
        }


@app.get("/api/snapshot")
def full_snapshot():
    """Single-roundtrip full SCADA state for REST fallback or verification."""
    return build_snapshot_payload()


@app.get("/api/systems")
def get_systems():
    return runtime.get_systems_summary()


@app.get("/api/pairs")
def get_pairs(systemId: Optional[str] = None):
    return runtime.get_pair_summaries(systemId)


@app.get("/api/sensors")
def get_sensors(systemId: Optional[str] = None, measurementType: Optional[str] = None):
    with runtime.lock:
        rows = [runtime.sensors[d.tag_id].to_camel_dict() for d in runtime.sensor_defs]
        if systemId:
            rows = [r for r in rows if r["systemId"] == systemId]
        if measurementType:
            rows = [r for r in rows if r["measurementType"] == measurementType]
        return rows


@app.get("/api/historian")
def get_historian(
    tags: str = Query(..., description="Comma-separated tag IDs"),
    start: str = Query(...),
    end: str = Query(...),
    maxPoints: int = Query(2000, ge=10, le=5000),
):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    start_ms = int(datetime.fromisoformat(start.replace("Z", "+00:00")).timestamp() * 1000)
    end_ms = int(datetime.fromisoformat(end.replace("Z", "+00:00")).timestamp() * 1000)
    return runtime.historian.query(tag_list, start_ms, end_ms, maxPoints)


@app.get("/api/predictions")
def get_predictions(systemId: Optional[str] = None, state: Optional[str] = None):
    with runtime.lock:
        rows = [runtime.predictions[d.tag_id].to_camel_dict() for d in runtime.sensor_defs]
        if systemId:
            rows = [r for r in rows if r["tagId"].startswith(systemId)]
        if state:
            rows = [r for r in rows if r["state"] == state]
        return rows


@app.get("/api/predictions/logs")
def get_prediction_logs(tagId: Optional[str] = None, state: Optional[str] = None, limit: int = Query(500, ge=1, le=5000)):
    return {
        "summary": runtime.repo.count_prediction_logs(),
        "rows": runtime.repo.query_prediction_logs(tag_id=tagId, state=state, limit=limit),
    }


@app.get("/api/alarms")
def get_alarms(activeOnly: bool = True):
    with runtime.lock:
        rows = [a.to_camel_dict() for a in runtime.alarms]
        if activeOnly:
            rows = [r for r in rows if r["state"].startswith("ACTIVE") or r["state"] in ("CLEARED_UNACK", "SHELVED")]
        return rows


@app.post("/api/alarms/{alarm_id}/ack")
def ack_alarm(alarm_id: str, user: str = "HMI_OPERATOR"):
    if not runtime.acknowledge_alarm(alarm_id, user):
        raise HTTPException(404, "Alarm not found")
    return {"ok": True}


@app.post("/api/alarms/ack-all")
def ack_all(user: str = "HMI_OPERATOR"):
    return {"acknowledged": runtime.acknowledge_all(user)}


@app.post("/api/alarms/{alarm_id}/shelve")
def shelve_alarm(alarm_id: str, user: str = "HMI_OPERATOR"):
    if not runtime.shelve_alarm(alarm_id, user):
        raise HTTPException(404, "Alarm not found or inactive")
    return {"ok": True}


@app.post("/api/simulator/control")
def sim_control(payload: ControlPayload):
    act = payload.action.upper()
    if act not in ("START", "PAUSE", "RESET"):
        raise HTTPException(422, "action must be START, PAUSE, or RESET")
    return runtime.set_control(act, payload.intervalMs)  # type: ignore[arg-type]


@app.post("/api/simulator/config")
def sim_config(payload: SimConfigPayload):
    runtime.update_simulator_config(payload.tagIds, payload.baseValue, payload.noise)
    return {"ok": True, "updated": len(payload.tagIds)}


@app.post("/api/simulator/fault")
def sim_fault(payload: FaultPayload):
    runtime.inject_fault(
        payload.tagIds,
        payload.scenario,
        payload.driftRatePerMin,
        payload.stepOffset,
        payload.spikeAmplitude,
        payload.spikeProbability,
    )
    return {"ok": True, "scenario": payload.scenario, "updated": len(payload.tagIds)}


@app.post("/api/simulator/apply-baselines/{system_id}")
def sim_apply_baselines(system_id: str):
    try:
        cnt = runtime.apply_suggested_baselines(system_id)
        return {"ok": True, "systemId": system_id, "updated": cnt}
    except ValueError as err:
        raise HTTPException(404, str(err))


@app.post("/api/simulator/advance")
def sim_advance(minutes: int = Query(1, ge=1, le=120), ticksPerMinute: int = Query(10, ge=1, le=60)):
    runtime.advance_minutes(minutes, ticksPerMinute)
    return {"ok": True, "status": runtime.get_status()}


@app.post("/api/limits")
def update_limits(payload: LimitsPayload):
    try:
        runtime.update_limits(payload.tagIds, payload.limits)
        return {"ok": True}
    except ValueError as err:
        raise HTTPException(422, str(err))


@app.post("/api/prediction/toggle")
def toggle_prediction(payload: PredictionTogglePayload):
    with runtime.lock:
        pcfg = runtime.prediction_config
        if payload.type == "global":
            pcfg["global"] = payload.enabled
        elif payload.type == "system":
            pcfg["systems"][payload.id] = payload.enabled
        elif payload.type == "submain":
            pcfg["submains"][payload.id] = payload.enabled
        elif payload.type == "sensor":
            pcfg["sensors"][payload.id] = payload.enabled
        runtime.evaluate_predictions(record_log=True)
        return pcfg


@app.post("/api/prediction/tuning")
def tune_prediction(payload: PredictionTuningPayload):
    with runtime.lock:
        pcfg = runtime.prediction_config
        if payload.sensitivity is not None and payload.sensitivity > 0:
            pcfg["sensitivity"] = float(payload.sensitivity)
        if payload.slopeGatePct is not None and payload.slopeGatePct >= 0:
            pcfg["slopeGatePct"] = float(payload.slopeGatePct)
        if payload.releaseHold is not None and payload.releaseHold >= 0:
            pcfg["releaseHold"] = int(payload.releaseHold)
        if payload.rawOnset is not None and payload.rawOnset >= 1:
            pcfg["rawOnset"] = min(5, int(payload.rawOnset))
        if payload.tagId is not None:
            if payload.sensorSensitivity is None:
                pcfg["sensorSensitivity"].pop(payload.tagId, None)
            elif payload.sensorSensitivity > 0:
                pcfg["sensorSensitivity"][payload.tagId] = float(payload.sensorSensitivity)
        runtime.evaluate_predictions(record_log=True)
        return pcfg


@app.get("/api/stream")
async def sse_stream():
    """Real-time Server-Sent Events stream pushing synchronized SCADA snapshots."""
    q: asyncio.Queue = asyncio.Queue(maxsize=4)
    sse_queues.add(q)

    async def event_gen():
        try:
            initial = build_snapshot_payload()
            initial["type"] = "SNAPSHOT_PUSH"
            yield f"data: {json.dumps(initial)}\n\n"
            while True:
                msg = await q.get()
                yield f"data: {msg}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            sse_queues.discard(q)

    return StreamingResponse(event_gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.websocket("/ws/stream")
async def websocket_stream(ws: WebSocket):
    await ws.accept()
    ws_clients.add(ws)
    try:
        initial = build_snapshot_payload()
        initial["type"] = "SNAPSHOT_PUSH"
        await ws.send_json(initial)
        while True:
            await ws.receive_text()
    except (WebSocketDisconnect, Exception):
        ws_clients.discard(ws)


FRONTEND_DIST = BACKEND_ROOT.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
