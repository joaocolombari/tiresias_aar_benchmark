"""Monophonic Gaussian attention model adapted from the desktop demo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

import numpy as np

from tiresias_benchmark.orientation.quaternion import (
    euler_to_quaternion,
    quat_rotate,
    source_relative_angle,
)


@dataclass(frozen=True)
class Source:
    name: str
    azimuth_deg: float
    distance_m: float = 1.0

    @property
    def position_xyz(self) -> np.ndarray:
        az = np.radians(self.azimuth_deg)
        return np.array(
            [self.distance_m * np.cos(az), self.distance_m * np.sin(az), 0.0],
            dtype=np.float32,
        )


@dataclass(frozen=True)
class AttentionResult:
    source_name: str
    gain_linear: float
    attention_pct: float
    distance_factor: float
    gain_db: float
    relative_angle_deg: float


def source_from_mapping(item: Mapping[str, object]) -> Source:
    if "azimuth_deg" in item:
        return Source(
            name=str(item.get("name", "source")),
            azimuth_deg=float(item["azimuth_deg"]),
            distance_m=float(item.get("distance_m", 1.0)),
        )
    if "pos" in item:
        pos = np.asarray(item["pos"], dtype=float)
        return Source(
            name=str(item.get("name", "source")),
            azimuth_deg=float(np.degrees(np.arctan2(pos[1], pos[0]))),
            distance_m=float(np.linalg.norm(pos)),
        )
    raise ValueError("source must provide azimuth_deg or pos")


def compute_attention(
    q: Iterable[float],
    sources: Iterable[Source | Mapping[str, object]],
    reference_distance_m: float,
    sigma_deg: float,
    bmax_db: float,
) -> list[AttentionResult]:
    if sigma_deg <= 0:
        raise ValueError("sigma_deg must be positive")
    if reference_distance_m <= 0:
        raise ValueError("reference_distance_m must be positive")

    forward = quat_rotate(q, np.array([1.0, 0.0, 0.0], dtype=float))
    forward = forward / np.linalg.norm(forward)

    values: list[AttentionResult] = []
    for raw_source in sources:
        source = raw_source if isinstance(raw_source, Source) else source_from_mapping(raw_source)
        direction = source.position_xyz.astype(np.float32)
        distance = float(np.linalg.norm(direction))
        direction = direction / distance

        distance_factor = reference_distance_m / max(distance, reference_distance_m)
        angle = float(np.degrees(np.arccos(np.clip(np.dot(forward, direction), -1.0, 1.0))))
        attention_norm = float(np.exp(-(angle**2) / (2.0 * sigma_deg**2)))
        gain_db = float(bmax_db * attention_norm)
        gain_linear = float(distance_factor * 10 ** (gain_db / 20.0))
        relative_angle = source_relative_angle(q, direction)
        values.append(
            AttentionResult(
                source_name=source.name,
                gain_linear=gain_linear,
                attention_pct=attention_norm * 100.0,
                distance_factor=distance_factor,
                gain_db=gain_db,
                relative_angle_deg=relative_angle,
            )
        )
    return values


def compute_attention_from_yaw(
    head_yaw_deg: float,
    sources: Iterable[Source | Mapping[str, object]],
    sigma_deg: float,
    bmax_db: float,
    reference_distance_m: float = 1.0,
) -> list[AttentionResult]:
    q = euler_to_quaternion(0.0, 0.0, head_yaw_deg)
    return compute_attention(q, sources, reference_distance_m, sigma_deg, bmax_db)
