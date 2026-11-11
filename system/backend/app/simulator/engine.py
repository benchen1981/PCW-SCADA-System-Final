"""Unified Simulator & Inference Runtime connecting Modbus TCP, Historian, AlarmEngine, and DriftForecastEngine."""
from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Literal, Optional

from app.config.topology import (
    GROUP_SPECS,
    EngineeringLimits,
    SensorDefinition,
    SubmainDefinition,
    build_topology,
    decode_float32_cdab,
    encode_float32_cdab,
)
from app.database.sqlite_repo import SqliteRepository
from app.engine.alarm_engine import AlarmEngine, AlarmEvent, SensorQuality, SensorRuntimeState
from app.engine.drift_forecast import (
    DriftForecastEngine,
    EngineParams,
    PredictionResult,
    evaluate_pair,
    severity_of,
)
from app.historian.store import HistorianStore
from app.modbus.tcp_server import ModbusRegisterBank

FaultScenario = Literal["NONE", "DRIFT", "STEP", "SPIKE", "BAD_QUALITY", "COMM_LOSS"]


@dataclass
class SimulatorTagConfig:
    tag_id: str
    base_value: float
    noise: float
    scenario: FaultScenario = "NONE"
    drift_rate_per_min: float = 0.0
    step_offset: float = 0.0
    spike_amplitude: float = 0.0
    spike_probability: float = 0.0
    scenario_started_at_ms: Optional[int] = None

    def to_camel_dict(self) -> dict:
        return {
            "tagId": self.tag_id,
            "baseValue": self.base_value,
            "noise": self.noise,
            "scenario": self.scenario,
            "driftRatePerMin": self.drift_rate_per_min,
            "stepOffset": self.step_offset,
            "spikeAmplitude": self.spike_amplitude,
            "spikeProbability": self.spike_probability,
            "scenarioStartedAt": self.scenario_started_at_ms,
        }


@dataclass
class MinuteAccumulator:
    total: int = 0
    good: int = 0
    value_sum: float = 0.0
    last_quality: SensorQuality = "GOOD"


class ScadaRuntime:
    """Thread-safe full-stack PCW SCADA runtime (320 sensors, 80 pairs, 8 systems)."""

    def __init__(self, db_path: Path, seed: int = 20261111) -> None:
        self.lock = threading.RLock()
        self.rng = random.Random(seed)
        self.repo = SqliteRepository(db_path)
        self.historian = HistorianStore(1440, 720)
        self.bank = ModbusRegisterBank(size=640)
        self.bank.set_write_callback(self._on_external_modbus_write)

        self.system_ids, self.submain_defs, self.sensor_defs = build_topology()
        self.def_by_tag: Dict[str, SensorDefinition] = {d.tag_id: d for d in self.sensor_defs}
        self.tag_by_offset: Dict[int, str] = {d.register_address - 40001: d.tag_id for d in self.sensor_defs}

        self.sensors: Dict[str, SensorRuntimeState] = {}
        self.sim_configs: Dict[str, SimulatorTagConfig] = {}
        self.alarms: List[AlarmEvent] = []
        self.predictions: Dict[str, PredictionResult] = {}
        self.modbus_meta: Dict[int, dict] = {}
        self.modbus_write_log: List[str] = []

        self.prediction_config = {
            "global": True,
            "systems": {s: True for s in self.system_ids},
            "submains": {},
            "sensors": {},
            "sensitivity": 2.0,
            "sensorSensitivity": {},
            "slopeGatePct": 5.0,
            "releaseHold": 3,
            "rawOnset": 1,
        }
        self.is_running = True
        self.iteration = 0
        self.update_interval_ms = 1000

        self.drift_engine = DriftForecastEngine(release_hold=3, raw_onset=1)
        self.alarm_engine = AlarmEngine(on_delay_samples=3)
        self._acc: Dict[str, MinuteAccumulator] = {}
        self._sim_clock_ms = int(time.time() * 1000)
        self._current_minute = self._sim_clock_ms // 60_000

        self._init_state()

    def _iso(self, ms: Optional[int] = None) -> str:
        t = self._sim_clock_ms if ms is None else ms
        return datetime.fromtimestamp(t / 1000.0, tz=timezone.utc).isoformat()

    def _init_state(self) -> None:
        now_iso = self._iso()
        for d in self.sensor_defs:
            base = d.limits.baseline
            span = d.limits.high - d.limits.low
            self.sensors[d.tag_id] = SensorRuntimeState(
                tag_id=d.tag_id,
                display_tag=d.display_tag,
                system_id=d.system_id,
                submain_id=d.submain_id,
                measurement_type=d.measurement_type,
                position=d.position,
                value=base,
                unit=d.unit,
                limits=d.limits,
                quality="GOOD",
                timestamp=now_iso,
            )
            self.sim_configs[d.tag_id] = SimulatorTagConfig(
                tag_id=d.tag_id,
                base_value=base,
                noise=span * 0.02,
            )
            self._write_modbus_register(d, base, "GOOD", now_iso)

        self.backfill(70)
        self.evaluate_predictions(now_iso, record_log=True)

    def _write_modbus_register(self, d: SensorDefinition, value: float, quality: SensorQuality, ts_iso: str) -> None:
        offset = d.register_address - 40001
        r1, r2 = encode_float32_cdab(value * d.scale)
        self.bank.write(offset, [r1, r2], notify=False)
        self.modbus_meta[d.register_address] = {
            "registerAddress": d.register_address,
            "reg1": r1,
            "reg2": r2,
            "rawValue": value * d.scale,
            "engineeringValue": value,
            "quality": quality,
            "lastUpdate": ts_iso,
        }

    def _on_external_modbus_write(self, offset: int, values: List[int]) -> None:
        """Handle FC06/FC16 Modbus TCP write into holding register bank."""
        with self.lock:
            aligned = offset - (offset % 2)
            tag_id = self.tag_by_offset.get(aligned)
            if not tag_id:
                return
            regs = self.bank.read(aligned, 2)
            val = decode_float32_cdab(regs[0], regs[1])
            d = self.def_by_tag[tag_id]
            eng_val = val / d.scale
            now_iso = self._iso()
            self.sim_configs[tag_id].base_value = eng_val
            self.sensors[tag_id].value = eng_val
            self.sensors[tag_id].timestamp = now_iso
            self.modbus_meta[d.register_address] = {
                "registerAddress": d.register_address,
                "reg1": regs[0],
                "reg2": regs[1],
                "rawValue": val,
                "engineeringValue": eng_val,
                "quality": "GOOD",
                "lastUpdate": now_iso,
            }
            self.modbus_write_log.append(f"{now_iso} MODBUS_TCP_WRITE {tag_id} -> {eng_val:.4f}")
            self.alarm_engine.evaluate_sensor(self.alarms, self.sensors[tag_id], now_iso, immediate_step=True)
            self.evaluate_predictions(now_iso, record_log=True)
            self.repo.append_audit(now_iso, "MODBUS_TCP", "REG_WRITE", tag_id, f"val={eng_val:.4f}")

    def backfill(self, min_points: int = 70) -> None:
        with self.lock:
            hist_rows = []
            for d in self.sensor_defs:
                have = self.historian.count(d.tag_id)
                if have >= min_points:
                    continue
                cfg = self.sim_configs[d.tag_id]
                missing = min_points - have
                base_ms = self._current_minute * 60_000 + 30_000
                for i in range(missing, 0, -1):
                    t_ms = base_ms - i * 60_000
                    v = cfg.base_value + (self.rng.random() - 0.5) * cfg.noise
                    self.historian.append(d.tag_id, t_ms, v, "GOOD")
                    hist_rows.append((d.tag_id, t_ms, self._iso(t_ms), v, "GOOD"))
            self.repo.insert_historian_batch(hist_rows)

    def _sample_tag(self, cfg: SimulatorTagConfig, prev_value: float, tick_ms: int) -> tuple[float, SensorQuality]:
        noise = (self.rng.random() - 0.5) * cfg.noise
        v = cfg.base_value + noise
        if cfg.scenario == "DRIFT":
            mins = max(0.0, (tick_ms - (cfg.scenario_started_at_ms or tick_ms)) / 60_000.0)
            v += cfg.drift_rate_per_min * mins
        elif cfg.scenario == "STEP":
            v += cfg.step_offset
        elif cfg.scenario == "SPIKE":
            if self.rng.random() < (cfg.spike_probability or 0.05):
                sign = -1.0 if self.rng.random() < 0.5 else 1.0
                v += sign * cfg.spike_amplitude
        elif cfg.scenario == "BAD_QUALITY":
            return v, "BAD"
        elif cfg.scenario == "COMM_LOSS":
            return prev_value, "COMM_LOSS"
        return v, "GOOD"

    def process_tick(self, tick_ms: Optional[int] = None, force_minute_eval: bool = False) -> None:
        with self.lock:
            if tick_ms is None:
                self._sim_clock_ms = max(self._sim_clock_ms + self.update_interval_ms, int(time.time() * 1000))
                tick_ms = self._sim_clock_ms
            else:
                self._sim_clock_ms = tick_ms

            self.iteration += 1
            now_iso = self._iso(tick_ms)
            need_immediate_sync = False

            for d in self.sensor_defs:
                s = self.sensors[d.tag_id]
                cfg = self.sim_configs[d.tag_id]
                v, q = self._sample_tag(cfg, s.value, tick_ms)
                prev_status = s.status
                s.value = v
                s.quality = q
                if q != "COMM_LOSS":
                    s.timestamp = now_iso
                self._write_modbus_register(d, v, q, now_iso)

                acc = self._acc.get(d.tag_id)
                if acc is None:
                    acc = MinuteAccumulator()
                    self._acc[d.tag_id] = acc
                acc.total += 1
                acc.last_quality = q
                if q == "GOOD":
                    acc.value_sum += v
                    acc.good += 1

                self.alarm_engine.evaluate_sensor(self.alarms, s, now_iso)
                # Detect immediate limit/quality state transition to keep Prediction page consistent
                pred = self.predictions.get(d.tag_id)
                lim = s.limits
                now_over = (v >= lim.high or v <= lim.low) if q == "GOOD" else False
                if (pred and ((now_over and pred.state != "EVENT") or (not now_over and pred.state == "EVENT"))) or (s.status != prev_status):
                    need_immediate_sync = True

            minute = tick_ms // 60_000
            if minute != self._current_minute or force_minute_eval:
                stamp_ms = self._current_minute * 60_000 + 30_000
                stamp_iso = self._iso(stamp_ms)
                self._current_minute = minute
                hist_rows = []
                for d in self.sensor_defs:
                    acc = self._acc.get(d.tag_id)
                    if acc is None or acc.total == 0:
                        continue
                    s = self.sensors[d.tag_id]
                    good_majority = (acc.good / acc.total) >= 0.5
                    q_min: SensorQuality = "GOOD" if good_majority else ("COMM_LOSS" if acc.last_quality == "COMM_LOSS" else "BAD")
                    val_min = (acc.value_sum / acc.good) if good_majority else s.value
                    self.historian.append(d.tag_id, stamp_ms, val_min, q_min)
                    hist_rows.append((d.tag_id, stamp_ms, stamp_iso, val_min, q_min))
                self._acc.clear()
                self.repo.insert_historian_batch(hist_rows)
                self.evaluate_predictions(now_iso, record_log=True)
            elif need_immediate_sync:
                self.evaluate_predictions(now_iso, record_log=True)

            self._persist_alarms()

    def advance_minutes(self, minutes: int, ticks_per_minute: int = 10) -> None:
        """Advance simulated clock deterministically by `minutes` minutes (for accelerated multi-minute testing)."""
        with self.lock:
            step_ms = 60_000 // max(1, ticks_per_minute)
            for _ in range(minutes):
                for _t in range(ticks_per_minute):
                    self.process_tick(self._sim_clock_ms + step_ms)

    def evaluate_predictions(self, now_iso: Optional[str] = None, record_log: bool = True) -> None:
        with self.lock:
            ts = now_iso or self._iso()
            pcfg = self.prediction_config
            self.drift_engine.set_release_hold(int(pcfg.get("releaseHold", 3)))
            self.drift_engine.set_raw_onset(int(pcfg.get("rawOnset", 1)))
            t_ms = self._sim_clock_ms
            pred_log_rows = []

            for d in self.sensor_defs:
                s = self.sensors[d.tag_id]
                enabled = (
                    bool(pcfg["global"])
                    and pcfg["systems"].get(s.system_id, True) is not False
                    and pcfg["submains"].get(s.submain_id, True) is not False
                    and pcfg["sensors"].get(s.tag_id, True) is not False
                )
                if not enabled:
                    self.drift_engine.reset(s.tag_id)
                    p = PredictionResult(
                        tag_id=s.tag_id,
                        evaluation_time=ts,
                        current_value=s.value,
                        base_avg_60=0.0,
                        m60=0,
                        m10=0,
                        n10=0.0,
                        slope=0.0,
                        forecast30=s.value,
                        forecast20=s.value,
                        forecast10=s.value,
                        state="DISABLED",
                        detector="NONE",
                        trigger_path="[Hold] ENGINE_DISABLED (Configured OFF)",
                    )
                else:
                    win = self.historian.window_points(s.tag_id, 70)
                    theta = float(pcfg["sensorSensitivity"].get(s.tag_id, pcfg["sensitivity"]))
                    params = EngineParams(sensitivity=theta, slope_gate_pct=float(pcfg.get("slopeGatePct", 5.0)))
                    p = self.drift_engine.evaluate(s.tag_id, win, s.value, s.limits, params, ts)
                    if p.state != "INSUFFICIENT_DATA":
                        feats = [
                            ("BaseAvg60", p.base_avg_60),
                            ("M60", float(p.m60)),
                            ("M10", float(p.m10)),
                            ("N10", min(p.n10, 99.0)),
                            ("Slope", p.slope),
                            ("Fcst30", p.forecast30),
                            ("Fcst20", p.forecast20),
                            ("Fcst10", p.forecast10),
                            ("Risk", float(p.risk_score)),
                        ]
                        for k, v in feats:
                            self.historian.append(f"{s.tag_id}_{k}", t_ms, v, "GOOD")

                self.predictions[s.tag_id] = p
                self.alarm_engine.evaluate_prediction(self.alarms, s, p, ts)
                if record_log:
                    cfg = self.sim_configs[s.tag_id]
                    pred_log_rows.append(
                        (
                            ts,
                            s.tag_id,
                            s.system_id,
                            s.submain_id,
                            s.measurement_type,
                            cfg.scenario,
                            p.current_value,
                            p.base_avg_60,
                            p.m60,
                            p.m10,
                            p.n10,
                            p.slope,
                            p.slope_ols,
                            p.r2,
                            p.forecast10,
                            p.forecast20,
                            p.forecast30,
                            p.ttl_minutes,
                            p.state,
                            p.detector,
                            p.risk_score,
                            p.trigger_path,
                        )
                    )

            if record_log:
                self.repo.insert_prediction_batch(pred_log_rows)
            self._persist_alarms()

    def _persist_alarms(self) -> None:
        if not self.alarms:
            return
        rows = [
            (
                a.alarm_id,
                a.tag_id,
                a.system_id,
                a.submain_id,
                a.alarm_type,
                a.priority,
                a.state,
                a.message,
                a.value,
                a.limit,
                a.unit,
                a.activated_at,
                a.acknowledged_at,
                a.cleared_at,
                a.acknowledged_by,
                a.source,
            )
            for a in self.alarms
        ]
        self.repo.upsert_alarms(rows)

    def set_control(self, action: Literal["START", "PAUSE", "RESET"], interval_ms: Optional[int] = None) -> dict:
        with self.lock:
            if interval_ms is not None and interval_ms >= 100:
                self.update_interval_ms = int(interval_ms)
            if action == "PAUSE":
                self.is_running = False
            elif action == "START":
                self.is_running = True
            elif action == "RESET":
                self.is_running = False
                self.iteration = 0
                self.alarms.clear()
                self.predictions.clear()
                self.drift_engine.reset()
                self.alarm_engine.reset()
                self._acc.clear()
                self.historian.clear()
                self.repo.clear_runtime_tables()
                self._sim_clock_ms = int(time.time() * 1000)
                self._current_minute = self._sim_clock_ms // 60_000
                self._init_state()
                self.repo.append_audit(self._iso(), "SYSTEM", "SIM_RESET", "ALL", None)
                self.is_running = True
            return self.get_status()

    def update_simulator_config(self, tag_ids: List[str], base_value: Optional[float] = None, noise: Optional[float] = None) -> None:
        with self.lock:
            now_iso = self._iso()
            for tag_id in tag_ids:
                cfg = self.sim_configs.get(tag_id)
                s = self.sensors.get(tag_id)
                d = self.def_by_tag.get(tag_id)
                if not cfg or not s or not d:
                    continue
                if base_value is not None:
                    cfg.base_value = float(base_value)
                    s.value = float(base_value)
                    s.timestamp = now_iso
                    self._write_modbus_register(d, s.value, s.quality, now_iso)
                if noise is not None:
                    cfg.noise = max(0.0, float(noise))
                self.alarm_engine.evaluate_sensor(self.alarms, s, now_iso, immediate_step=True)
            self.evaluate_predictions(now_iso, record_log=True)
            self.repo.append_audit(now_iso, "HMI_OPERATOR", "SIM_CONFIG", f"{len(tag_ids)} tags", f"base={base_value}, noise={noise}")

    def update_limits(self, tag_ids: List[str], patch: dict) -> None:
        with self.lock:
            now_iso = self._iso()
            for tag_id in tag_ids:
                s = self.sensors.get(tag_id)
                if not s:
                    continue
                cur = s.limits
                new_lim = EngineeringLimits(
                    low_low=float(patch.get("lowLow", cur.low_low)),
                    low=float(patch.get("low", cur.low)),
                    high=float(patch.get("high", cur.high)),
                    high_high=float(patch.get("highHigh", cur.high_high)),
                    baseline=float(patch.get("baseline", cur.baseline)),
                    deadband=cur.deadband,
                )
                if not (new_lim.low_low <= new_lim.low < new_lim.high <= new_lim.high_high):
                    raise ValueError(f"Invalid limit order for {tag_id}")
                s.limits = new_lim
                self.alarm_engine.evaluate_sensor(self.alarms, s, now_iso, immediate_step=True)
            self.evaluate_predictions(now_iso, record_log=True)
            self.repo.append_audit(now_iso, "ENGINEER", "LIMIT_CHANGE", f"{len(tag_ids)} tags", str(patch))

    def inject_fault(
        self,
        tag_ids: List[str],
        scenario: FaultScenario,
        drift_rate_per_min: float = 0.0,
        step_offset: float = 0.0,
        spike_amplitude: float = 0.0,
        spike_probability: float = 0.05,
        actor: str = "HMI_OPERATOR",
    ) -> None:
        with self.lock:
            now_ms = self._sim_clock_ms
            now_iso = self._iso(now_ms)
            for tag_id in tag_ids:
                cfg = self.sim_configs.get(tag_id)
                s = self.sensors.get(tag_id)
                d = self.def_by_tag.get(tag_id)
                if not cfg or not s or not d:
                    continue
                cfg.scenario = scenario
                cfg.drift_rate_per_min = drift_rate_per_min
                cfg.step_offset = step_offset
                cfg.spike_amplitude = spike_amplitude
                cfg.spike_probability = spike_probability
                cfg.scenario_started_at_ms = None if scenario == "NONE" else now_ms
                if scenario == "STEP":
                    s.value = cfg.base_value + step_offset
                    self._write_modbus_register(d, s.value, "GOOD", now_iso)
                elif scenario == "BAD_QUALITY":
                    s.quality = "BAD"
                elif scenario == "COMM_LOSS":
                    s.quality = "COMM_LOSS"
                elif scenario == "NONE":
                    s.quality = "GOOD"
                    s.value = cfg.base_value
                    self._write_modbus_register(d, s.value, "GOOD", now_iso)
                self.alarm_engine.evaluate_sensor(self.alarms, s, now_iso, immediate_step=True)
            self.evaluate_predictions(now_iso, record_log=True)
            self.repo.append_audit(now_iso, actor, f"FAULT_{scenario}", f"{len(tag_ids)} tags", f"step={step_offset}, drift={drift_rate_per_min}")

    def apply_suggested_baselines(self, system_id: str) -> int:
        with self.lock:
            if system_id not in GROUP_SPECS:
                raise ValueError(f"Unknown system {system_id}")
            spec = GROUP_SPECS[system_id]
            now_iso = self._iso()
            count = 0
            for d in self.sensor_defs:
                if d.system_id != system_id:
                    continue
                lim = spec.ft if d.measurement_type == "FLOW" else (spec.dp if d.measurement_type == "DP" else spec.pt)
                s = self.sensors[d.tag_id]
                cfg = self.sim_configs[d.tag_id]
                s.limits = lim
                s.value = lim.baseline
                s.quality = "GOOD"
                s.timestamp = now_iso
                cfg.base_value = lim.baseline
                cfg.noise = (lim.high - lim.low) * 0.02
                cfg.scenario = "NONE"
                cfg.drift_rate_per_min = 0.0
                cfg.step_offset = 0.0
                cfg.scenario_started_at_ms = None
                self._write_modbus_register(d, s.value, "GOOD", now_iso)
                self.alarm_engine.evaluate_sensor(self.alarms, s, now_iso, immediate_step=True)
                count += 1
            self.evaluate_predictions(now_iso, record_log=True)
            self.repo.append_audit(now_iso, "ENGINEER", "APPLY_BASELINES", system_id, f"{count} tags")
            return count

    def get_status(self) -> dict:
        return {
            "isRunning": self.is_running,
            "iteration": self.iteration,
            "updateIntervalMs": self.update_interval_ms,
            "simTime": self._iso(),
            "sensorCount": len(self.sensors),
        }

    def get_systems_summary(self) -> List[dict]:
        with self.lock:
            out = []
            now_iso = self._iso()
            for sys_id in self.system_ids:
                sys_sensors = [self.sensors[d.tag_id] for d in self.sensor_defs if d.system_id == sys_id]
                supply_pt = [s.value for s in sys_sensors if s.position == "SUPPLY" and s.measurement_type == "PRESSURE"]
                return_pt = [s.value for s in sys_sensors if s.position == "RETURN" and s.measurement_type == "PRESSURE"]
                dp_vals = [s.value for s in sys_sensors if s.measurement_type == "DP"]
                flow_vals = [s.value for s in sys_sensors if s.measurement_type == "FLOW"]
                open_alarms = [a for a in self.alarms if a.system_id == sys_id and a.state.startswith("ACTIVE")]
                unack = sum(1 for a in open_alarms if a.state == "ACTIVE_UNACK")
                drift_cnt = sum(
                    1
                    for s in sys_sensors
                    if self.predictions.get(s.tag_id) and self.predictions[s.tag_id].state in ("T-30", "T-20", "T-10", "EVENT")
                )
                bad_q = sum(1 for s in sys_sensors if s.quality != "GOOD")
                health = (
                    "CRITICAL"
                    if any(a.priority == "CRITICAL" for a in open_alarms)
                    else ("WARNING" if (open_alarms or drift_cnt > 0) else "HEALTHY")
                )

                def _stats(vals: List[float]) -> dict:
                    if not vals:
                        return {"min": 0.0, "max": 0.0, "avg": 0.0}
                    return {"min": min(vals), "max": max(vals), "avg": sum(vals) / len(vals)}

                out.append(
                    {
                        "systemId": sys_id,
                        "systemName": f"PCW System {sys_id[-2:]}",
                        "description": f"Process Cooling Water Loop {sys_id[-2:]} ({GROUP_SPECS[sys_id].floor})",
                        "status": "ONLINE",
                        "health": health,
                        "communicationStatus": "DISCONNECTED" if (bad_q == len(sys_sensors) and bad_q > 0) else "CONNECTED",
                        "activeAlarmCount": len(open_alarms),
                        "unacknowledgedAlarmCount": unack,
                        "driftSensorCount": drift_cnt,
                        "totalSensorCount": len(sys_sensors),
                        "supplyPressure": _stats(supply_pt),
                        "returnPressure": _stats(return_pt),
                        "differentialPressure": _stats(dp_vals),
                        "supplyTemperature": 22.0,
                        "returnTemperature": 25.0,
                        "flow": sum(flow_vals) / len(flow_vals) if flow_vals else 0.0,
                        "lastUpdateTime": now_iso,
                        "submains": [sm.canonical_name for sm in self.submain_defs if sm.system_id == sys_id],
                    }
                )
            return out

    def get_pair_summaries(self, system_id: Optional[str] = None) -> List[dict]:
        with self.lock:
            out = []
            for sm in self.submain_defs:
                if system_id and sm.system_id != system_id:
                    continue
                pts = self.predictions.get(sm.supply_tags[0])
                ptr = self.predictions.get(sm.return_tags[0])
                if pts and ptr:
                    out.append(evaluate_pair(pts, ptr))
            return out

    def acknowledge_alarm(self, alarm_id: str, user: str = "HMI_OPERATOR") -> bool:
        with self.lock:
            now_iso = self._iso()
            for a in self.alarms:
                if a.alarm_id == alarm_id:
                    a.acknowledged_at = now_iso
                    a.acknowledged_by = user
                    a.state = "ACTIVE_ACK" if a.state == "ACTIVE_UNACK" else ("CLEARED_ACK" if a.state == "CLEARED_UNACK" else a.state)
                    self._persist_alarms()
                    self.repo.append_audit(now_iso, user, "ALARM_ACK", a.tag_id, a.alarm_id)
                    return True
            return False

    def acknowledge_all(self, user: str = "HMI_OPERATOR") -> int:
        with self.lock:
            now_iso = self._iso()
            cnt = 0
            for a in self.alarms:
                if a.state in ("ACTIVE_UNACK", "CLEARED_UNACK"):
                    a.acknowledged_at = now_iso
                    a.acknowledged_by = user
                    a.state = "ACTIVE_ACK" if a.state == "ACTIVE_UNACK" else "CLEARED_ACK"
                    cnt += 1
            if cnt:
                self._persist_alarms()
                self.repo.append_audit(now_iso, user, "ALARM_ACK_ALL", f"{cnt} alarms", None)
            return cnt

    def shelve_alarm(self, alarm_id: str, user: str = "HMI_OPERATOR") -> bool:
        with self.lock:
            now_iso = self._iso()
            for a in self.alarms:
                if a.alarm_id == alarm_id and a.state.startswith("ACTIVE"):
                    a.state = "SHELVED"
                    a.acknowledged_at = a.acknowledged_at or now_iso
                    a.acknowledged_by = a.acknowledged_by or user
                    self._persist_alarms()
                    self.repo.append_audit(now_iso, user, "ALARM_SHELVE", a.tag_id, a.alarm_id)
                    return True
            return False

