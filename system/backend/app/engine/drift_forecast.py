"""Unified Dual-Window Drift & Forecast Engine (Python reference matching TypeScript 1:1)."""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Dict, List, Literal, Optional, Sequence, Tuple

from app.config.topology import EngineeringLimits

PredictionState = Literal[
    "NORMAL",
    "T-30",
    "T-20",
    "T-10",
    "EVENT",
    "DISABLED",
    "INSUFFICIENT_DATA",
]

WINDOW = 70
N10_SATURATED = 999.0
MIN_VALID_RATIO = 0.8
T_975_DF8 = 2.306

SEVERITY: Dict[PredictionState, int] = {
    "DISABLED": -2,
    "INSUFFICIENT_DATA": -1,
    "NORMAL": 0,
    "T-30": 1,
    "T-20": 2,
    "T-10": 3,
    "EVENT": 4,
}


def severity_of(state: PredictionState) -> int:
    return SEVERITY.get(state, 0)


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def _js_round(x: float) -> int:
    """Match JavaScript Math.round for non-negative values."""
    return int(math.floor(x + 0.5))


@dataclass(frozen=True)
class WindowPoint:
    v: float
    good: bool = True


@dataclass(frozen=True)
class EngineParams:
    sensitivity: float = 2.0
    slope_gate_pct: float = 5.0


@dataclass
class PredictionResult:
    tag_id: str
    evaluation_time: str
    current_value: float
    base_avg_60: float
    m60: int
    m10: int
    n10: float
    slope: float
    forecast30: float
    forecast20: float
    forecast10: float
    state: PredictionState
    trigger_path: str = ""
    detector: Literal["FORECAST", "DENSITY", "NONE"] = "NONE"
    slope_ols: float = 0.0
    r2: float = 0.0
    band10: float = 0.0
    band20: float = 0.0
    band30: float = 0.0
    ttl_minutes: Optional[float] = None
    ttl_limit: Optional[str] = None
    risk_score: int = 0
    valid_ratio: float = 0.0
    hold_count: int = 0

    def to_camel_dict(self) -> dict:
        return {
            "tagId": self.tag_id,
            "evaluationTime": self.evaluation_time,
            "currentValue": self.current_value,
            "baseAvg60": self.base_avg_60,
            "m60": self.m60,
            "m10": self.m10,
            "n10": self.n10,
            "slope": self.slope,
            "forecast30": self.forecast30,
            "forecast20": self.forecast20,
            "forecast10": self.forecast10,
            "state": self.state,
            "triggerPath": self.trigger_path,
            "detector": self.detector,
            "slopeOls": self.slope_ols,
            "r2": self.r2,
            "band10": self.band10,
            "band20": self.band20,
            "band30": self.band30,
            "ttlMinutes": self.ttl_minutes,
            "ttlLimit": self.ttl_limit,
            "riskScore": self.risk_score,
            "validRatio": self.valid_ratio,
            "holdCount": self.hold_count,
        }


def compute_n10(m60: int, m10: int) -> float:
    if m60 == 0 and m10 > 0:
        return N10_SATURATED
    if m60 == 0:
        return 0.0
    return m10 / (m60 / 6.0)


def ols(y: Sequence[float]) -> dict:
    n = len(y)
    if n < 3:
        return {"slope": 0.0, "intercept": float(y[0]) if n else 0.0, "r2": 0.0, "s": 0.0, "sxx": 0.0, "xbar": 0.0, "n": n}
    xbar = (n - 1) / 2.0
    ybar = sum(y) / n
    sxx = 0.0
    sxy = 0.0
    syy = 0.0
    for i, val in enumerate(y):
        dx = i - xbar
        dy = val - ybar
        sxx += dx * dx
        sxy += dx * dy
        syy += dy * dy
    slope = sxy / sxx if sxx > 0.0 else 0.0
    intercept = ybar - slope * xbar
    sse = sum((y[i] - (intercept + slope * i)) ** 2 for i in range(n))
    r2 = _clamp01(1.0 - sse / syy) if syy > 0.0 else 0.0
    s = math.sqrt(sse / max(1, n - 2))
    return {"slope": slope, "intercept": intercept, "r2": r2, "s": s, "sxx": sxx, "xbar": xbar, "n": n}


def prediction_band(fit: dict, h: float) -> float:
    if fit["n"] < 3 or fit["sxx"] == 0.0:
        return 0.0
    xh = fit["n"] - 1 + h
    return T_975_DF8 * fit["s"] * math.sqrt(1.0 + 1.0 / fit["n"] + ((xh - fit["xbar"]) ** 2) / fit["sxx"])


def classify_limit(val: float, lim: EngineeringLimits) -> Optional[str]:
    if val >= lim.high_high:
        return f"HH ({lim.high_high})"
    if val >= lim.high:
        return f"H ({lim.high})"
    if val <= lim.low_low:
        return f"LL ({lim.low_low})"
    if val <= lim.low:
        return f"L ({lim.low})"
    return None


def time_to_limit(value: float, slope: float, lim: EngineeringLimits, horizon_cap: float = 1440.0) -> Tuple[Optional[float], Optional[str]]:
    if not math.isfinite(slope) or abs(slope) < 1e-12:
        return None, None
    targets = (
        (("H", lim.high), ("HH", lim.high_high))
        if slope > 0.0
        else (("L", lim.low), ("LL", lim.low_low))
    )
    for name, target_val in targets:
        ahead = (value < target_val) if slope > 0.0 else (value > target_val)
        if ahead:
            minutes = (target_val - value) / slope
            return (minutes, name) if minutes <= horizon_cap else (None, None)
    return 0.0, ("HH" if slope > 0.0 else "LL")


def evaluate_window(
    tag_id: str,
    window: Sequence[WindowPoint],
    current_value: float,
    limits: EngineeringLimits,
    params: EngineParams,
    now_iso: str,
) -> PredictionResult:
    if len(window) < WINDOW:
        return PredictionResult(
            tag_id=tag_id,
            evaluation_time=now_iso,
            current_value=current_value,
            base_avg_60=0.0,
            m60=0,
            m10=0,
            n10=0.0,
            slope=0.0,
            forecast30=current_value,
            forecast20=current_value,
            forecast10=current_value,
            state="INSUFFICIENT_DATA",
            trigger_path=f"[Hold] INSUFFICIENT_DATA (need {WINDOW} pts, have {len(window)})",
            valid_ratio=0.0,
        )

    w = window[-WINDOW:]
    valid_ratio = sum(1 for p in w if p.good) / WINDOW
    b_vals = [p.v for p in w[0:60] if p.good]
    p_vals = [p.v for p in w[60:65] if p.good]
    r_vals = [p.v for p in w[65:70] if p.good]
    last10 = [p.v for p in w[60:70] if p.good]

    if valid_ratio < MIN_VALID_RATIO or not p_vals or not r_vals or len(b_vals) < 30:
        return PredictionResult(
            tag_id=tag_id,
            evaluation_time=now_iso,
            current_value=current_value,
            base_avg_60=0.0,
            m60=0,
            m10=0,
            n10=0.0,
            slope=0.0,
            forecast30=current_value,
            forecast20=current_value,
            forecast10=current_value,
            state="INSUFFICIENT_DATA",
            trigger_path=f"[Hold] DATA_QUALITY (GOOD ratio {valid_ratio * 100:.0f}% < {MIN_VALID_RATIO * 100:.0f}%)",
            valid_ratio=valid_ratio,
        )

    base_avg_60 = sum(b_vals) / len(b_vals)
    slope = (sum(r_vals) / len(r_vals) - sum(p_vals) / len(p_vals)) / 5.0
    up = slope >= 0.0

    def is_above(x: float) -> bool:
        return x > base_avg_60 if up else x < base_avg_60

    m60 = _js_round((sum(1 for x in b_vals if is_above(x)) * 60.0) / len(b_vals))
    m10 = _js_round((sum(1 for x in last10 if is_above(x)) * 10.0) / len(last10))
    n10 = compute_n10(m60, m10)

    fcst10 = current_value + slope * 10.0
    fcst20 = current_value + slope * 20.0
    fcst30 = current_value + slope * 30.0

    span = max(1e-9, limits.high - limits.low)
    excursion30 = abs(slope) * 30.0
    level_shift = abs((sum(last10) / len(last10)) - base_avg_60)
    gate_val = (params.slope_gate_pct / 100.0) * span
    slope_gate = (excursion30 >= gate_val) or (level_shift >= gate_val)
    # Reachability fix: use >= theta so M10=10, M60=30 (N10=2.0) is reachable at theta=2.0
    is_drifting = (n10 >= params.sensitivity) and slope_gate

    fit = ols(last10)
    band10 = prediction_band(fit, 10.0)
    band20 = prediction_band(fit, 20.0)
    band30 = prediction_band(fit, 30.0)

    ttl_min, ttl_lim = time_to_limit(current_value, slope, limits)

    state: PredictionState = "NORMAL"
    detector: Literal["FORECAST", "DENSITY", "NONE"] = "NONE"
    trigger_path = "Forecasts within limits, no density shift -> STABLE"

    now_hit = current_value >= limits.high or current_value <= limits.low
    hit10 = classify_limit(fcst10, limits)
    hit20 = classify_limit(fcst20, limits)
    hit30 = classify_limit(fcst30, limits)

    if now_hit:
        state = "EVENT"
        detector = "FORECAST"
        trigger_path = f"PV ({current_value:.3f}) beyond {classify_limit(current_value, limits)} -> EVENT"
    elif hit10:
        state = "T-10"
        detector = "FORECAST"
        trigger_path = f"Fcst10 ({fcst10:.3f}) reaches {hit10} -> ALARM"
    elif hit20:
        state = "T-20"
        detector = "FORECAST"
        trigger_path = f"Fcst20 ({fcst20:.3f}) reaches {hit20} -> WARN"
    elif hit30:
        state = "T-30"
        detector = "FORECAST"
        trigger_path = f"Fcst30 ({fcst30:.3f}) reaches {hit30} -> WARN"
    elif is_drifting:
        state = "T-30"
        detector = "DENSITY"
        n_txt = "SAT" if n10 >= N10_SATURATED else f"{n10:.2f}"
        trigger_path = f"N10 {n_txt} >= theta {params.sensitivity} & (|d30| {excursion30:.3f} or |dmu| {level_shift:.3f}) >= {params.slope_gate_pct}% span -> WARN (Behaviour Shift)"

    centre = limits.baseline if limits.baseline is not None else (limits.high + limits.low) / 2.0
    margin_factor = _clamp01(abs(current_value - centre) / (span / 2.0))
    ttl_factor = 0.0 if ttl_min is None else _clamp01(1.0 - ttl_min / 60.0)
    if n10 >= N10_SATURATED:
        density_factor = 1.0 if slope_gate else 0.3
    else:
        density_factor = _clamp01(n10 / max(0.1, params.sensitivity)) * (1.0 if slope_gate else 0.4)
    risk = 100.0 * _clamp01(0.4 * margin_factor + 0.4 * ttl_factor + 0.2 * density_factor)
    floor_map: Dict[PredictionState, float] = {"EVENT": 100.0, "T-10": 85.0, "T-20": 70.0, "T-30": 50.0}
    risk = max(risk, floor_map.get(state, 0.0))
    if state == "NORMAL":
        risk = min(risk, 49.0)

    return PredictionResult(
        tag_id=tag_id,
        evaluation_time=now_iso,
        current_value=current_value,
        base_avg_60=base_avg_60,
        m60=m60,
        m10=m10,
        n10=n10,
        slope=slope,
        forecast30=fcst30,
        forecast20=fcst20,
        forecast10=fcst10,
        state=state,
        trigger_path=trigger_path,
        detector=detector,
        slope_ols=fit["slope"],
        r2=fit["r2"],
        band10=band10,
        band20=band20,
        band30=band30,
        ttl_minutes=ttl_min,
        ttl_limit=ttl_lim,
        risk_score=_js_round(risk),
        valid_ratio=valid_ratio,
        hold_count=0,
    )


class DriftForecastEngine:
    """Stateful wrapper adding optional raw-onset confirmation and L6 hysteresis latch per tag."""

    def __init__(self, release_hold: int = 3, raw_onset: int = 1) -> None:
        self.release_hold = max(0, int(release_hold))
        self.raw_onset = max(1, int(raw_onset))
        self._latch: Dict[str, dict] = {}
        self._onset_streak: Dict[str, int] = {}

    def set_release_hold(self, n: int) -> None:
        self.release_hold = max(0, int(n))

    def set_raw_onset(self, n: int) -> None:
        self.raw_onset = max(1, int(n))

    def reset(self, tag_id: Optional[str] = None) -> None:
        if tag_id:
            self._latch.pop(tag_id, None)
            self._onset_streak.pop(tag_id, None)
        else:
            self._latch.clear()
            self._onset_streak.clear()

    def evaluate(
        self,
        tag_id: str,
        window: Sequence[WindowPoint],
        current_value: float,
        limits: EngineeringLimits,
        params: EngineParams,
        now_iso: str,
    ) -> PredictionResult:
        raw = evaluate_window(tag_id, window, current_value, limits, params, now_iso)
        if raw.state in ("INSUFFICIENT_DATA", "DISABLED"):
            self._latch.pop(tag_id, None)
            self._onset_streak.pop(tag_id, None)
            return raw

        prev = self._latch.get(tag_id)
        was_active = prev is not None and severity_of(prev["state"]) >= 1

        # Optional pre-latch onset debounce for predictive states (EVENT never delayed)
        if raw.state in ("T-30", "T-20", "T-10"):
            streak = self._onset_streak.get(tag_id, 0) + 1
            self._onset_streak[tag_id] = streak
            if self.raw_onset > 1 and not was_active and streak < self.raw_onset:
                intended = raw.state
                raw.trigger_path = f"[Onset {streak}/{self.raw_onset} confirming {intended}] {raw.trigger_path}"
                raw.state = "NORMAL"
                raw.detector = "NONE"
                raw.risk_score = min(raw.risk_score, 45)
                self._latch[tag_id] = {"state": "NORMAL", "hold": 0, "lower_streak": 0}
                return raw
        else:
            if raw.state == "NORMAL":
                self._onset_streak[tag_id] = 0

        if prev is None or severity_of(raw.state) >= severity_of(prev["state"]):
            hold = prev["hold"] + 1 if (prev is not None and prev["state"] == raw.state) else 1
            self._latch[tag_id] = {"state": raw.state, "hold": hold, "lower_streak": 0}
            raw.hold_count = 0 if raw.state == "NORMAL" else hold
            return raw

        # Hysteresis latch unless release_hold consecutive normal evaluations confirm recovery.
        lower_streak = prev["lower_streak"] + 1
        if lower_streak >= self.release_hold:
            self._latch[tag_id] = {"state": raw.state, "hold": 1, "lower_streak": 0}
            raw.hold_count = 0 if raw.state == "NORMAL" else 1
            return raw

        new_hold = prev["hold"] + 1
        self._latch[tag_id] = {"state": prev["state"], "hold": new_hold, "lower_streak": lower_streak}
        raw.trigger_path = f"[Latched {prev['state']} {lower_streak}/{self.release_hold}] {raw.trigger_path}"
        raw.state = prev["state"]
        raw.hold_count = new_hold
        raw.risk_score = max(raw.risk_score, 50)
        return raw


def evaluate_pair(pts_pred: PredictionResult, ptr_pred: PredictionResult) -> dict:
    """Supply/Return Pair-level aggregation per Submain (no water-stealing assumption)."""
    s_sev = severity_of(pts_pred.state)
    r_sev = severity_of(ptr_pred.state)
    pair_state = pts_pred.state if s_sev >= r_sev else ptr_pred.state
    s_warn = s_sev >= 1
    r_warn = r_sev >= 1
    if s_warn and r_warn:
        coupling = "COUPLED_DRIFT"
    elif s_warn:
        coupling = "SUPPLY_ONLY"
    elif r_warn:
        coupling = "RETURN_ONLY"
    else:
        coupling = "NORMAL"

    parts = pts_pred.tag_id.split(".")
    return {
        "systemId": parts[0],
        "submainId": parts[1],
        "supplyTag": pts_pred.tag_id,
        "returnTag": ptr_pred.tag_id,
        "supplyPressure": round(pts_pred.current_value, 4),
        "returnPressure": round(ptr_pred.current_value, 4),
        "pairDeltaP": round(pts_pred.current_value - ptr_pred.current_value, 4),
        "supplyState": pts_pred.state,
        "returnState": ptr_pred.state,
        "pairState": pair_state,
        "couplingMode": coupling,
        "pairRiskScore": max(pts_pred.risk_score, ptr_pred.risk_score),
    }
