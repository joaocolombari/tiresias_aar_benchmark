from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv

import numpy as np
import soundfile as sf


@dataclass(frozen=True)
class BrirRecord:
    head_yaw_deg: float
    source_name: str
    source_azimuth_deg: float
    left_ir_path: Path
    right_ir_path: Path


class BrirDataset:
    def __init__(self, records: list[BrirRecord], sample_rate_hz: int):
        self.records = records
        self.sample_rate_hz = sample_rate_hz

    @classmethod
    def from_manifest(cls, path: str | Path) -> "BrirDataset":
        manifest = Path(path)
        records: list[BrirRecord] = []
        sample_rate_hz: int | None = None
        with manifest.open(newline="") as file:
            for row in csv.DictReader(file):
                if sample_rate_hz is None:
                    sample_rate_hz = int(row["sample_rate_hz"])
                records.append(
                    BrirRecord(
                        head_yaw_deg=float(row["head_yaw_deg"]),
                        source_name=row["source_name"],
                        source_azimuth_deg=float(row["source_azimuth_deg"]),
                        left_ir_path=(manifest.parent / row["left_ir_path"]).resolve(),
                        right_ir_path=(manifest.parent / row["right_ir_path"]).resolve(),
                    )
                )
        if sample_rate_hz is None:
            raise ValueError("empty BRIR manifest")
        return cls(records, sample_rate_hz)

    def available_angles(self) -> list[float]:
        return sorted({record.head_yaw_deg for record in self.records})

    def nearest_record(self, source_name: str, head_yaw_deg: float) -> BrirRecord:
        candidates = [record for record in self.records if record.source_name == source_name]
        if not candidates:
            raise KeyError(f"source {source_name!r} not found in BRIR dataset")
        return min(candidates, key=lambda record: abs(record.head_yaw_deg - head_yaw_deg))

    def bracket_records(self, source_name: str, head_yaw_deg: float) -> tuple[BrirRecord, BrirRecord, float]:
        candidates = sorted(
            [record for record in self.records if record.source_name == source_name],
            key=lambda record: record.head_yaw_deg,
        )
        if not candidates:
            raise KeyError(f"source {source_name!r} not found in BRIR dataset")
        angles = np.array([record.head_yaw_deg for record in candidates], dtype=float)
        if head_yaw_deg <= angles[0]:
            return candidates[0], candidates[0], 0.0
        if head_yaw_deg >= angles[-1]:
            return candidates[-1], candidates[-1], 0.0
        hi = int(np.searchsorted(angles, head_yaw_deg, side="right"))
        lo = hi - 1
        weight = (head_yaw_deg - angles[lo]) / (angles[hi] - angles[lo])
        return candidates[lo], candidates[hi], float(weight)


def load_stereo_ir(record: BrirRecord) -> tuple[np.ndarray, np.ndarray, int]:
    left, fs_l = sf.read(record.left_ir_path, dtype="float32")
    right, fs_r = sf.read(record.right_ir_path, dtype="float32")
    if fs_l != fs_r:
        raise ValueError("left and right IR sample rates differ")
    if left.ndim > 1:
        left = left[:, 0]
    if right.ndim > 1:
        right = right[:, 0]
    return left, right, fs_l
