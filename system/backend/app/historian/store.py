"""Per-tag fixed-capacity ring buffers with spike-preserving min/max downsampling."""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Deque, Dict, List, Optional

from app.engine.drift_forecast import WindowPoint

QUALITY_CODE = {"GOOD": 0, "UNCERTAIN": 1, "BAD": 2, "COMM_LOSS": 3}
QUALITY_NAME = ["GOOD", "UNCERTAIN", "BAD", "COMM_LOSS"]


@dataclass(frozen=True)
class SeriesPoint:
    t: int  # epoch ms
    v: float
    q: int  # quality code


def downsample_min_max(points: List[SeriesPoint], max_points: int) -> List[SeriesPoint]:
    if len(points) <= max_points or max_points < 4:
        return points
    buckets = max_points // 2
    size = len(points) / buckets
    out: List[SeriesPoint] = []
    for b in range(buckets):
        start = int(b * size)
        end = min(len(points), int((b + 1) * size))
        if start >= end:
            continue
        p_min = points[start]
        p_max = points[start]
        for i in range(start + 1, end):
            if points[i].v < p_min.v:
                p_min = points[i]
            if points[i].v > p_max.v:
                p_max = points[i]
        if p_min is p_max:
            out.append(p_min)
        elif p_min.t <= p_max.t:
            out.extend((p_min, p_max))
        else:
            out.extend((p_max, p_min))
    return out


class HistorianStore:
    def __init__(self, raw_capacity: int = 1440, feature_capacity: int = 720) -> None:
        self.raw_capacity = raw_capacity
        self.feature_capacity = feature_capacity
        self._series: Dict[str, Deque[SeriesPoint]] = {}

    @staticmethod
    def is_feature_tag(tag_id: str) -> bool:
        return "_" in tag_id

    def _ring(self, tag_id: str) -> Deque[SeriesPoint]:
        ring = self._series.get(tag_id)
        if ring is None:
            cap = self.feature_capacity if self.is_feature_tag(tag_id) else self.raw_capacity
            ring = deque(maxlen=cap)
            self._series[tag_id] = ring
        return ring

    def append(self, tag_id: str, t_ms: int, v: float, quality: str | int = "GOOD") -> None:
        if not math.isfinite(v):
            return
        q = quality if isinstance(quality, int) else QUALITY_CODE.get(quality, 1)
        self._ring(tag_id).append(SeriesPoint(t=int(t_ms), v=float(v), q=q))

    def count(self, tag_id: str) -> int:
        ring = self._series.get(tag_id)
        return len(ring) if ring is not None else 0

    def tail(self, tag_id: str, n: int) -> List[SeriesPoint]:
        ring = self._series.get(tag_id)
        if not ring:
            return []
        if n >= len(ring):
            return list(ring)
        return list(ring)[-n:]

    def window_points(self, tag_id: str, n: int = 70) -> List[WindowPoint]:
        return [WindowPoint(v=p.v, good=(p.q == 0)) for p in self.tail(tag_id, n)]

    def query(self, tag_ids: List[str], start_ms: int, end_ms: int, max_points_per_tag: int = 2000) -> List[dict]:
        out: List[dict] = []
        for tag_id in tag_ids:
            ring = self._series.get(tag_id)
            if not ring:
                continue
            pts = [p for p in ring if start_ms <= p.t <= end_ms]
            for p in downsample_min_max(pts, max_points_per_tag):
                out.append(
                    {
                        "tagId": tag_id,
                        "timestamp": datetime.fromtimestamp(p.t / 1000.0, tz=timezone.utc).isoformat(),
                        "value": p.v,
                        "quality": QUALITY_NAME[p.q] if 0 <= p.q < len(QUALITY_NAME) else "UNCERTAIN",
                    }
                )
        return out

    def clear(self) -> None:
        self._series.clear()

