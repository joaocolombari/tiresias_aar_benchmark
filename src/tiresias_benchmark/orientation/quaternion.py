"""Quaternion helpers preserving the desktop application's scalar-first convention.

The original host application uses `(qw, qx, qy, qz)`, converts Euler angles in
degrees, and treats the +X axis as the forward direction.
"""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np

Quaternion = tuple[float, float, float, float]


def normalize_quaternion(q: Iterable[float]) -> Quaternion:
    w, x, y, z = (float(v) for v in q)
    norm = math.sqrt(w * w + x * x + y * y + z * z)
    if norm == 0.0:
        raise ValueError("zero-length quaternion")
    return (w / norm, x / norm, y / norm, z / norm)


def quaternion_to_euler(w: float, x: float, y: float, z: float) -> tuple[float, float, float]:
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    sinp = 2 * (w * y - z * x)
    if abs(sinp) >= 1:
        pitch = math.copysign(math.pi / 2, sinp)
    else:
        pitch = math.asin(sinp)

    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    return math.degrees(roll), math.degrees(pitch), math.degrees(yaw)


def yaw_from_quaternion(q: Iterable[float]) -> float:
    return quaternion_to_euler(*normalize_quaternion(q))[2]


def euler_to_quaternion(roll_deg: float, pitch_deg: float, yaw_deg: float) -> Quaternion:
    r, p, y = math.radians(roll_deg), math.radians(pitch_deg), math.radians(yaw_deg)
    cy = math.cos(y * 0.5)
    sy = math.sin(y * 0.5)
    cp = math.cos(p * 0.5)
    sp = math.sin(p * 0.5)
    cr = math.cos(r * 0.5)
    sr = math.sin(r * 0.5)

    qw = cr * cp * cy + sr * sp * sy
    qx = sr * cp * cy - cr * sp * sy
    qy = cr * sp * cy + sr * cp * sy
    qz = cr * cp * sy - sr * sp * cy
    return normalize_quaternion((qw, qx, qy, qz))


def quaternion_conjugate(q: Iterable[float]) -> Quaternion:
    w, x, y, z = normalize_quaternion(q)
    return (w, -x, -y, -z)


def quaternion_multiply(q1: Iterable[float], q2: Iterable[float]) -> Quaternion:
    w1, x1, y1, z1 = normalize_quaternion(q1)
    w2, x2, y2, z2 = normalize_quaternion(q2)
    return normalize_quaternion(
        (
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        )
    )


def quat_rotate(q: Iterable[float], vector: Iterable[float]) -> np.ndarray:
    w, x, y, z = normalize_quaternion(q)
    v = np.asarray(vector, dtype=float)
    qvec = np.array([x, y, z], dtype=float)
    uv = np.cross(qvec, v)
    uuv = np.cross(qvec, uv)
    return v + 2.0 * (w * uv + uuv)


def quaternion_to_matrix(q: Iterable[float]) -> np.ndarray:
    w, x, y, z = normalize_quaternion(q)
    return np.array(
        [
            [1 - 2 * y * y - 2 * z * z, 2 * x * y - 2 * z * w, 2 * x * z + 2 * y * w, 0],
            [2 * x * y + 2 * z * w, 1 - 2 * x * x - 2 * z * z, 2 * y * z - 2 * x * w, 0],
            [2 * x * z - 2 * y * w, 2 * y * z + 2 * x * w, 1 - 2 * x * x - 2 * y * y, 0],
            [0, 0, 0, 1],
        ],
        dtype=np.float32,
    )


def source_relative_angle(q: Iterable[float], source_position_xyz: Iterable[float]) -> float:
    q_inv = quaternion_conjugate(q)
    source = np.asarray(source_position_xyz, dtype=np.float32)
    norm = np.linalg.norm(source)
    if norm == 0.0:
        raise ValueError("source position must be non-zero")
    source = source / norm
    relative = quat_rotate(q_inv, source)
    return float(np.degrees(np.arctan2(relative[1], relative[0])))


def wrap_angle_deg(angle_deg: float) -> float:
    """Wrap angle to [-180, 180)."""

    return float((angle_deg + 180.0) % 360.0 - 180.0)


def angular_distance_deg(a_deg: float, b_deg: float) -> float:
    return abs(wrap_angle_deg(a_deg - b_deg))
