"""ISA-18.2 / IEC 62682 aligned alarm state machine for process, quality, and predictive DRIFT alarms."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple

from app.config.topology import EngineeringLimits
from app.engine.drift_forecast import PredictionResult

AlarmType = Literal["HIGH_HIGH", "HIGH", "LOW", "LOW_LOW", "TRIP", "DRIFT", "ERROR"]
AlarmPriority = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
AlarmState = Literal["ACTIVE_UNACK", "ACTIVE_ACK", "CLEARED_UNACK", "CLEARED_ACK", "SHELVED"]
SensorQuality = Literal["GOOD", "UNCERTAIN", "BAD", "COMM_LOSS"]

ALARM_JOURNAL_MAX = 5000
DEFAULT_ON_DELAY_SAMPLES = 3


def is_open_alarm(state: AlarmState) -> bool:
    return state in ("ACTIVE_UNACK", "ACTIVE_ACK", "SHELVED")


@dataclass
class AlarmEvent:
    alarm_id: str
    tag_id: str
    system_id: str
    submain_id: str
    alarm_type: AlarmType
    priority: AlarmPriority
    state: AlarmState
    message: str
    value: float
    limit: float
    unit: str
    activated_at: str
    acknowledged_at: Optional[str] = None
    cleared_at: Optional[str] = None
    acknowledged_by: Optional[str] = None
    source: str = "ALARM_ENGINE"

    def to_camel_dict(self) -> dict:
        return {
            "alarmId": self.alarm_id,
            "tagId": self.tag_id,
            "systemId": self.system_id,
            "submainId": self.submain_id,
            "alarmType": self.alarm_type,
            "priority": self.priority,
            "state": self.state,
            "message": self.message,
            "value": self.value,
            "limit": self.limit,
            "unit": self.unit,
            "activatedAt": self.activated_at,
            "acknowledgedAt": self.acknowledged_at,
            "clearedAt": self.cleared_at,
            "acknowledgedBy": self.acknowledged_by,
            "source": self.source,
        }


@dataclass
class SensorRuntimeState:
    tag_id: str
    display_tag: str
    system_id: str
    submain_id: str
    measurement_type: str
    position: str
    value: float
    unit: str
    limits: EngineeringLimits
    quality: SensorQuality = "GOOD"
    source: str = "MODBUS_SIMULATOR"
    timestamp: str = ""
    status: Literal["NORMAL", "WARNING", "ALARM", "ERROR"] = "NORMAL"
    alarm_state: Literal["NONE", "ACTIVE_UNACK", "ACTIVE_ACK", "SHELVED"] = "NONE"
    alarm_priority: Optional[AlarmPriority] = None

    def to_camel_dict(self) -> dict:
        return {
            "tagId": self.tag_id,
            "displayTag": self.display_tag,
            "systemId": self.system_id,
            "submainId": self.submain_id,
            "measurementType": self.measurement_type,
            "position": self.position,
            "value": self.value,
            "unit": self.unit,
            "quality": self.quality,
            "source": self.source,
            "timestamp": self.timestamp,
            "status": self.status,
            "alarmState": self.alarm_state,
            "alarmPriority": self.alarm_priority,
            "engineeringLimits": self.limits.to_dict(),
        }


class AlarmEngine:
    def __init__(self, on_delay_samples: int = DEFAULT_ON_DELAY_SAMPLES) -> None:
        self.on_delay_samples = max(1, int(on_delay_samples))
        self._seq = 0
        self._pending: Dict[Tuple[str, str], int] = {}
        self._index: Dict[Tuple[str, str], AlarmEvent] = {}

    def reset(self) -> None:
        self._pending.clear()
        self._index.clear()

    def _new_id(self) -> str:
        self._seq += 1
        return f"ALM-{self._seq:06d}"

    def _find_open(self, alarms: List[AlarmEvent], tag_id: str, alarm_type: AlarmType) -> Optional[AlarmEvent]:
        key = (tag_id, alarm_type)
        a = self._index.get(key)
        if a is not None and is_open_alarm(a.state):
            return a
        self._index.pop(key, None)
        for item in reversed(alarms):
            if item.tag_id == tag_id and item.alarm_type == alarm_type and is_open_alarm(item.state):
                self._index[key] = item
                return item
        return None

    def _raise(
        self,
        alarms: List[AlarmEvent],
        s: SensorRuntimeState,
        alarm_type: AlarmType,
        priority: AlarmPriority,
        message: str,
        limit: float,
        ts: str,
        source: str = "ALARM_ENGINE",
    ) -> AlarmEvent:
        evt = AlarmEvent(
            alarm_id=self._new_id(),
            tag_id=s.tag_id,
            system_id=s.system_id,
            submain_id=s.submain_id,
            alarm_type=alarm_type,
            priority=priority,
            state="ACTIVE_UNACK",
            message=message,
            value=s.value,
            limit=limit,
            unit=s.unit,
            activated_at=ts,
            source=source,
        )
        alarms.append(evt)
        self._index[(s.tag_id, alarm_type)] = evt
        if len(alarms) > ALARM_JOURNAL_MAX:
            drop_idx = next((i for i, x in enumerate(alarms) if not is_open_alarm(x.state) and x.state != "CLEARED_UNACK"), 0)
            alarms.pop(drop_idx)
        return evt

    @staticmethod
    def _clear(a: AlarmEvent, ts: str) -> None:
        a.cleared_at = ts
        a.state = "CLEARED_UNACK" if a.state == "ACTIVE_UNACK" else "CLEARED_ACK"

    def evaluate_sensor(self, alarms: List[AlarmEvent], s: SensorRuntimeState, ts: str, immediate_step: bool = False) -> None:
        lim = s.limits
        db = lim.deadband if lim.deadband is not None else max(1e-6, (lim.high - lim.low) * 0.01)
        bad_q = s.quality in ("BAD", "COMM_LOSS")

        q_alarm = self._find_open(alarms, s.tag_id, "ERROR")
        if bad_q and q_alarm is None:
            self._raise(alarms, s, "ERROR", "HIGH", f"{s.tag_id} {s.quality}", 0.0, ts, "QUALITY_MONITOR")
        elif not bad_q and q_alarm is not None:
            self._clear(q_alarm, ts)

        if not bad_q:
            v = s.value
            defs: List[Tuple[AlarmType, bool, bool, float, AlarmPriority, str]] = [
                ("HIGH_HIGH", v >= lim.high_high, v < lim.high_high - db, lim.high_high, "CRITICAL", "HIGH-HIGH"),
                ("HIGH", lim.high <= v < lim.high_high, v < lim.high - db or v >= lim.high_high, lim.high, "HIGH", "HIGH"),
                ("LOW", lim.low_low < v <= lim.low, v > lim.low + db or v <= lim.low_low, lim.low, "HIGH", "LOW"),
                ("LOW_LOW", v <= lim.low_low, v > lim.low_low + db, lim.low_low, "CRITICAL", "LOW-LOW"),
            ]
            req_samples = 1 if immediate_step else self.on_delay_samples
            for atype, on_cond, off_cond, limit_val, prio, label in defs:
                key = (s.tag_id, atype)
                open_a = self._find_open(alarms, s.tag_id, atype)
                if on_cond:
                    if open_a is not None:
                        if open_a.state != "SHELVED":
                            open_a.value = v
                        self._pending.pop(key, None)
                    else:
                        cnt = self._pending.get(key, 0) + 1
                        if cnt >= req_samples:
                            self._raise(alarms, s, atype, prio, f"{s.tag_id} {label}", limit_val, ts)
                            self._pending.pop(key, None)
                        else:
                            self._pending[key] = cnt
                else:
                    self._pending.pop(key, None)
                    if open_a is not None and off_cond:
                        self._clear(open_a, ts)

        active: Optional[AlarmEvent] = None
        for atype in ("HIGH_HIGH", "LOW_LOW", "ERROR", "HIGH", "LOW"):
            cand = self._find_open(alarms, s.tag_id, atype)  # type: ignore[arg-type]
            if cand is not None and cand.state in ("ACTIVE_UNACK", "ACTIVE_ACK"):
                active = cand
                break
        if active is not None:
            s.alarm_state = active.state  # type: ignore[assignment]
            s.status = "ERROR" if active.alarm_type == "ERROR" else "ALARM"
            s.alarm_priority = active.priority
        else:
            s.alarm_state = "NONE"
            s.status = "NORMAL"
            s.alarm_priority = None

    def evaluate_prediction(self, alarms: List[AlarmEvent], s: SensorRuntimeState, p: PredictionResult, ts: str) -> None:
        open_a = self._find_open(alarms, s.tag_id, "DRIFT")
        warn = p.state in ("T-30", "T-20", "T-10")
        if warn:
            prio: AlarmPriority = "HIGH" if p.state == "T-10" else ("MEDIUM" if p.state == "T-20" else "LOW")
            ttl = f" · TTL {p.ttl_minutes:.0f} min -> {p.ttl_limit}" if p.ttl_minutes is not None else ""
            det_lbl = "N10 drift" if p.detector == "DENSITY" else "forecast"
            msg = f"{s.tag_id} PREDICTIVE {p.state} ({det_lbl}){ttl}"
            lim = p.forecast10 if p.state == "T-10" else (p.forecast20 if p.state == "T-20" else p.forecast30)
            if open_a is None:
                self._raise(alarms, s, "DRIFT", prio, msg, lim, ts, "PREDICTION_ENGINE")
            elif open_a.state != "SHELVED":
                rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
                if rank[prio] > rank[open_a.priority]:
                    open_a.priority = prio
                    if open_a.state == "ACTIVE_ACK":
                        open_a.state = "ACTIVE_UNACK"
                open_a.message = msg
                open_a.value = s.value
                open_a.limit = lim
        elif open_a is not None and p.state in ("NORMAL", "EVENT", "DISABLED", "INSUFFICIENT_DATA"):
            self._clear(open_a, ts)

        if warn and s.status == "NORMAL":
            s.status = "WARNING"

