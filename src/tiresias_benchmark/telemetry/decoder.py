"""BLE telemetry packet decoding.

Supports the original 16-byte quaternion characteristic and the observed 64-byte
experiment telemetry characteristic. Missing fields are explicit `None` values.
"""

from __future__ import annotations

from dataclasses import dataclass
import struct

TELEMETRY_CHAR_UUID = "12345678-1234-5678-1234-56789abcdef2"
LEGACY_QUATERNION_CHAR_UUID = "12345678-1234-5678-1234-56789abcdef1"
TELEMETRY_VERSION = 1
TELEMETRY_PACKET_SIZE = 64
_TELEMETRY_STRUCT = struct.Struct("<BBHII11fBBHI")
_LEGACY_STRUCT = struct.Struct("<ffff")


@dataclass(frozen=True)
class OrientationTelemetry:
    packet_format: str
    version: int | None
    flags: int | None
    payload_size: int
    seq: int | None
    device_time_ms: int | None
    ax_m_s2: float | None
    ay_m_s2: float | None
    az_m_s2: float | None
    gx_rad_s: float | None
    gy_rad_s: float | None
    gz_rad_s: float | None
    qw: float
    qx: float
    qy: float
    qz: float
    yaw_deg: float | None
    calibration_state: int | None

    @property
    def quaternion(self) -> tuple[float, float, float, float]:
        return (self.qw, self.qx, self.qy, self.qz)


def decode_telemetry_packet(data: bytes) -> OrientationTelemetry:
    if len(data) != TELEMETRY_PACKET_SIZE:
        raise ValueError(f"expected {TELEMETRY_PACKET_SIZE} bytes, got {len(data)}")
    values = _TELEMETRY_STRUCT.unpack(data)
    version, flags, payload_size, seq, device_time_ms = values[:5]
    floats = values[5:16]
    calibration_state = values[16]
    if version != TELEMETRY_VERSION:
        raise ValueError(f"unsupported telemetry version {version}")
    if payload_size != TELEMETRY_PACKET_SIZE:
        raise ValueError(f"unexpected telemetry payload size {payload_size}")
    return OrientationTelemetry(
        packet_format="telemetry_v1",
        version=version,
        flags=flags,
        payload_size=payload_size,
        seq=seq,
        device_time_ms=device_time_ms,
        ax_m_s2=floats[0],
        ay_m_s2=floats[1],
        az_m_s2=floats[2],
        gx_rad_s=floats[3],
        gy_rad_s=floats[4],
        gz_rad_s=floats[5],
        qw=floats[6],
        qx=floats[7],
        qy=floats[8],
        qz=floats[9],
        yaw_deg=floats[10],
        calibration_state=calibration_state,
    )


def decode_legacy_quaternion(data: bytes) -> OrientationTelemetry:
    if len(data) != _LEGACY_STRUCT.size:
        raise ValueError(f"expected {_LEGACY_STRUCT.size} bytes, got {len(data)}")
    qw, qx, qy, qz = _LEGACY_STRUCT.unpack(data)
    return OrientationTelemetry(
        packet_format="legacy_quaternion",
        version=None,
        flags=None,
        payload_size=_LEGACY_STRUCT.size,
        seq=None,
        device_time_ms=None,
        ax_m_s2=None,
        ay_m_s2=None,
        az_m_s2=None,
        gx_rad_s=None,
        gy_rad_s=None,
        gz_rad_s=None,
        qw=qw,
        qx=qx,
        qy=qy,
        qz=qz,
        yaw_deg=None,
        calibration_state=None,
    )


def decode_packet(data: bytes) -> OrientationTelemetry:
    if len(data) == TELEMETRY_PACKET_SIZE:
        return decode_telemetry_packet(data)
    if len(data) == _LEGACY_STRUCT.size:
        return decode_legacy_quaternion(data)
    raise ValueError(f"unsupported orientation packet length {len(data)}")
