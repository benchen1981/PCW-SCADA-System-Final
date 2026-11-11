"""Canonical PCW plant topology, engineering limits, and Modbus FLOAT32 CDAB mapping."""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Tuple

MeasurementType = Literal["PRESSURE", "FLOW", "DP"]
PositionType = Literal["SUPPLY", "RETURN"]


@dataclass(frozen=True)
class EngineeringLimits:
    low_low: float
    low: float
    high: float
    high_high: float
    baseline: float
    deadband: float | None = None

    def to_dict(self) -> dict:
        return {
            "lowLow": self.low_low,
            "low": self.low,
            "high": self.high,
            "highHigh": self.high_high,
            "baseline": self.baseline,
            "deadband": self.deadband,
        }


@dataclass(frozen=True)
class SensorDefinition:
    tag_id: str
    display_tag: str
    system_id: str
    submain_id: str
    measurement_type: MeasurementType
    position: PositionType
    unit: str
    limits: EngineeringLimits
    register_address: int
    scale: float = 1.0


@dataclass(frozen=True)
class SubmainDefinition:
    system_id: str
    submain_id: str
    canonical_name: str
    display_name: str
    supply_tags: Tuple[str, str]
    return_tags: Tuple[str, str]


@dataclass(frozen=True)
class SystemGroupSpec:
    group_id: str
    floor: str
    pt: EngineeringLimits
    ft: EngineeringLimits
    dp: EngineeringLimits


GROUP_SPECS: Dict[str, SystemGroupSpec] = {
    "PCW01": SystemGroupSpec(
        group_id="Group 1",
        floor="2F Cleanroom",
        pt=EngineeringLimits(1.20, 1.30, 1.70, 1.80, 1.50),
        ft=EngineeringLimits(150.0, 160.0, 200.0, 220.0, 180.0),
        dp=EngineeringLimits(0.00, 0.10, 0.50, 0.60, 0.30),
    ),
    "PCW02": SystemGroupSpec(
        group_id="Group 1",
        floor="2F Cleanroom",
        pt=EngineeringLimits(1.20, 1.30, 1.70, 1.80, 1.50),
        ft=EngineeringLimits(150.0, 160.0, 200.0, 220.0, 180.0),
        dp=EngineeringLimits(0.00, 0.10, 0.50, 0.60, 0.30),
    ),
    "PCW03": SystemGroupSpec(
        group_id="Group 2",
        floor="2F Cleanroom",
        pt=EngineeringLimits(1.50, 1.70, 2.10, 2.20, 1.90),
        ft=EngineeringLimits(150.0, 160.0, 200.0, 220.0, 180.0),
        dp=EngineeringLimits(0.00, 0.10, 0.50, 0.60, 0.30),
    ),
    "PCW04": SystemGroupSpec(
        group_id="Group 2",
        floor="2F Cleanroom",
        pt=EngineeringLimits(1.50, 1.70, 2.10, 2.20, 1.90),
        ft=EngineeringLimits(150.0, 160.0, 200.0, 220.0, 180.0),
        dp=EngineeringLimits(0.00, 0.10, 0.50, 0.60, 0.30),
    ),
    "PCW05": SystemGroupSpec(
        group_id="Group 3",
        floor="1F Sub-Fab",
        pt=EngineeringLimits(2.20, 2.30, 2.70, 2.80, 2.50),
        ft=EngineeringLimits(230.0, 240.0, 280.0, 300.0, 260.0),
        dp=EngineeringLimits(0.00, 0.10, 0.50, 0.60, 0.30),
    ),
    "PCW06": SystemGroupSpec(
        group_id="Group 3",
        floor="1F Sub-Fab",
        pt=EngineeringLimits(2.20, 2.30, 2.70, 2.80, 2.50),
        ft=EngineeringLimits(230.0, 240.0, 280.0, 300.0, 260.0),
        dp=EngineeringLimits(0.00, 0.10, 0.50, 0.60, 0.30),
    ),
    "PCW07": SystemGroupSpec(
        group_id="Group 4",
        floor="1F Sub-Fab",
        pt=EngineeringLimits(1.90, 2.00, 2.40, 2.50, 2.20),
        ft=EngineeringLimits(200.0, 220.0, 260.0, 280.0, 240.0),
        dp=EngineeringLimits(0.00, 0.10, 0.50, 0.60, 0.30),
    ),
    "PCW08": SystemGroupSpec(
        group_id="Group 4",
        floor="1F Sub-Fab",
        pt=EngineeringLimits(1.90, 2.00, 2.40, 2.50, 2.20),
        ft=EngineeringLimits(200.0, 220.0, 260.0, 280.0, 240.0),
        dp=EngineeringLimits(0.00, 0.10, 0.50, 0.60, 0.30),
    ),
}


def encode_float32_cdab(value: float) -> Tuple[int, int]:
    """Encode IEEE-754 float32 into two 16-bit registers using CDAB (word swap)."""
    raw = struct.pack(">f", float(value))
    ab, cd = struct.unpack(">HH", raw)
    return cd, ab


def decode_float32_cdab(reg1: int, reg2: int) -> float:
    """Decode two 16-bit CDAB registers back into an IEEE-754 float32."""
    raw = struct.pack(">HH", reg2 & 0xFFFF, reg1 & 0xFFFF)
    return float(struct.unpack(">f", raw)[0])


def build_topology() -> Tuple[List[str], List[SubmainDefinition], List[SensorDefinition]]:
    systems = [f"PCW{i:02d}" for i in range(1, 9)]
    submains: List[SubmainDefinition] = []
    sensors: List[SensorDefinition] = []
    addr = 40001

    for sys_id in systems:
        spec = GROUP_SPECS[sys_id]
        for j in range(1, 11):
            sub_id = f"Submain{j:02d}"
            canonical = f"{sys_id}.{sub_id}"
            pts = f"{canonical}.PTS"
            ft = f"{canonical}.FT"
            ptr = f"{canonical}.PTR"
            pdt = f"{canonical}.PDT"
            submains.append(
                SubmainDefinition(
                    system_id=sys_id,
                    submain_id=sub_id,
                    canonical_name=canonical,
                    display_name=f"SM-{j:02d}",
                    supply_tags=(pts, ft),
                    return_tags=(ptr, pdt),
                )
            )
            entries: List[Tuple[str, str, MeasurementType, PositionType, str, EngineeringLimits]] = [
                (pts, "PTS", "PRESSURE", "SUPPLY", "bar", spec.pt),
                (ft, "FT", "FLOW", "SUPPLY", "LPM", spec.ft),
                (ptr, "PTR", "PRESSURE", "RETURN", "bar", spec.pt),
                (pdt, "PDT", "DP", "RETURN", "bar", spec.dp),
            ]
            for tag_id, disp, mtype, pos, unit, lim in entries:
                sensors.append(
                    SensorDefinition(
                        tag_id=tag_id,
                        display_tag=disp,
                        system_id=sys_id,
                        submain_id=sub_id,
                        measurement_type=mtype,
                        position=pos,
                        unit=unit,
                        limits=lim,
                        register_address=addr,
                    )
                )
                addr += 2
    return systems, submains, sensors

