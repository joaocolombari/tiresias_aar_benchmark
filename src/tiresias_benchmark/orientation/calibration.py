"""Head-referenced tare calibration used by the desktop application."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .quaternion import (
    Quaternion,
    quaternion_conjugate,
    quaternion_multiply,
    yaw_from_quaternion,
)


@dataclass
class TareCalibration:
    """Calibrate the first received orientation as the forward direction."""

    tare_quaternion: Quaternion | None = None

    def is_calibrated(self) -> bool:
        return self.tare_quaternion is not None

    def reset(self) -> None:
        self.tare_quaternion = None

    def calibrate_first(self, raw_quaternion: Iterable[float]) -> Quaternion:
        if self.tare_quaternion is None:
            self.tare_quaternion = quaternion_conjugate(raw_quaternion)
        return self.apply(raw_quaternion)

    def apply(self, raw_quaternion: Iterable[float]) -> Quaternion:
        if self.tare_quaternion is None:
            raise RuntimeError("tare calibration has not been initialized")
        return quaternion_multiply(self.tare_quaternion, raw_quaternion)

    def calibrated_yaw_deg(self, raw_quaternion: Iterable[float]) -> float:
        return yaw_from_quaternion(self.calibrate_first(raw_quaternion))
