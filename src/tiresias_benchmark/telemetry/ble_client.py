from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
import time
from pathlib import Path

from tiresias_benchmark.attention.gaussian import Source, compute_attention
from tiresias_benchmark.orientation.calibration import TareCalibration
from tiresias_benchmark.orientation.quaternion import yaw_from_quaternion
from tiresias_benchmark.telemetry.decoder import (
    LEGACY_QUATERNION_CHAR_UUID,
    TELEMETRY_CHAR_UUID,
    decode_packet,
)
from tiresias_benchmark.telemetry.logger import TelemetryCsvLogger


@dataclass(frozen=True)
class BleRecordConfig:
    device_name: str = "Tiresias_DK"
    sigma_deg: float = 20.0
    bmax_db: float = 10.0
    reference_distance_m: float = 1.0
    scan_timeout_s: float = 10.0
    duration_s: float | None = None


async def record_ble_telemetry(
    output_csv: str | Path,
    config: BleRecordConfig,
    sources: list[Source],
) -> Path:
    try:
        from bleak import BleakClient, BleakScanner
    except ImportError as exc:
        raise RuntimeError("BLE recording requires installing the 'ble' optional dependency") from exc

    devices = await BleakScanner.discover(timeout=config.scan_timeout_s)
    device = next((dev for dev in devices if dev.name and config.device_name in dev.name), None)
    if device is None:
        raise RuntimeError(f"BLE device matching {config.device_name!r} not found")

    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    calibration = TareCalibration()
    path = Path(output_csv)

    async with BleakClient(device) as client:
        with TelemetryCsvLogger(path, session_id=session_id, max_sources=len(sources)) as logger:
            loop = asyncio.get_running_loop()
            done = loop.create_future()

            def handler(_sender, data: bytearray) -> None:
                host_time_ns = time.perf_counter_ns()
                telemetry = decode_packet(bytes(data))
                calibrated_q = calibration.calibrate_first(telemetry.quaternion)
                calibrated_yaw = yaw_from_quaternion(calibrated_q)
                attention = compute_attention(
                    calibrated_q,
                    sources,
                    config.reference_distance_m,
                    config.sigma_deg,
                    config.bmax_db,
                )
                logger.write(
                    host_monotonic_timestamp_ns=host_time_ns,
                    telemetry=telemetry,
                    calibrated_yaw_deg=calibrated_yaw,
                    sigma_deg=config.sigma_deg,
                    bmax_db=config.bmax_db,
                    audio_frame_index=None,
                    attention=attention,
                )

            try:
                await client.start_notify(TELEMETRY_CHAR_UUID, handler)
                active_uuid = TELEMETRY_CHAR_UUID
            except Exception:
                await client.start_notify(LEGACY_QUATERNION_CHAR_UUID, handler)
                active_uuid = LEGACY_QUATERNION_CHAR_UUID

            try:
                if config.duration_s is None:
                    await done
                else:
                    await asyncio.sleep(config.duration_s)
            finally:
                await client.stop_notify(active_uuid)
    return path
