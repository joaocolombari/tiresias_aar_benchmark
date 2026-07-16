from __future__ import annotations

import asyncio
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import threading
import time

from tiresias_benchmark.experiments.experiment_01 import build_reference_sequences
from tiresias_benchmark.orientation.calibration import TareCalibration
from tiresias_benchmark.orientation.quaternion import yaw_from_quaternion
from tiresias_benchmark.telemetry.decoder import (
    LEGACY_QUATERNION_CHAR_UUID,
    TELEMETRY_CHAR_UUID,
    OrientationTelemetry,
    decode_packet,
)
from tiresias_benchmark.telemetry.logger import telemetry_fieldnames


SEGMENT_FIELDS = [
    "run_id",
    "run_type",
    "position_index",
    "reference_angle_commanded_deg",
    "reference_angle_normalized_deg",
    "is_closure_measurement",
    "segment_kind",
    "segment_phase",
    "include_in_analysis",
    "segment_elapsed_s",
    "operator_event",
]


@dataclass
class GuidedOutputs:
    raw_csv: Path
    segmented_csv: Path
    drift_before_csv: Path | None
    drift_after_csv: Path | None


@dataclass
class AcquisitionState:
    run_id: str = ""
    run_type: str = ""
    position_index: int | None = None
    reference_angle_commanded_deg: float | None = None
    reference_angle_normalized_deg: float | None = None
    is_closure_measurement: bool = False
    segment_kind: str = "idle"
    segment_phase: str = "idle"
    include_in_analysis: bool = False
    operator_event: str = ""
    phase_started_ns: int = 0
    latest_calibrated_yaw_deg: float | None = None
    packets_seen: int = 0

    def update_phase(self, phase: str, *, include_in_analysis: bool, operator_event: str = "") -> None:
        self.segment_phase = phase
        self.include_in_analysis = include_in_analysis
        self.operator_event = operator_event
        self.phase_started_ns = time.perf_counter_ns()

    def as_fields(self, now_ns: int) -> dict[str, object]:
        elapsed = ""
        if self.phase_started_ns:
            elapsed = (now_ns - self.phase_started_ns) / 1_000_000_000.0
        return {
            "run_id": self.run_id,
            "run_type": self.run_type,
            "position_index": "" if self.position_index is None else self.position_index,
            "reference_angle_commanded_deg": ""
            if self.reference_angle_commanded_deg is None
            else self.reference_angle_commanded_deg,
            "reference_angle_normalized_deg": ""
            if self.reference_angle_normalized_deg is None
            else self.reference_angle_normalized_deg,
            "is_closure_measurement": str(self.is_closure_measurement).lower(),
            "segment_kind": self.segment_kind,
            "segment_phase": self.segment_phase,
            "include_in_analysis": str(self.include_in_analysis).lower(),
            "segment_elapsed_s": elapsed,
            "operator_event": self.operator_event,
        }


class GuidedExperiment01Logger:
    def __init__(self, outputs: GuidedOutputs, session_id: str):
        self.outputs = outputs
        self.session_id = session_id
        self.fieldnames = telemetry_fieldnames(max_sources=0) + SEGMENT_FIELDS
        self._last_host_time_ns: int | None = None
        self._last_seq: int | None = None

    def __enter__(self) -> "GuidedExperiment01Logger":
        self.outputs.raw_csv.parent.mkdir(parents=True, exist_ok=True)
        self.outputs.segmented_csv.parent.mkdir(parents=True, exist_ok=True)
        self._raw_file = self.outputs.raw_csv.open("w", newline="")
        self._segmented_file = self.outputs.segmented_csv.open("w", newline="")
        self._raw_writer = csv.DictWriter(self._raw_file, fieldnames=self.fieldnames)
        self._segmented_writer = csv.DictWriter(self._segmented_file, fieldnames=self.fieldnames)
        self._raw_writer.writeheader()
        self._segmented_writer.writeheader()
        self._drift_before_file = None
        self._drift_after_file = None
        self._drift_before_writer = None
        self._drift_after_writer = None
        if self.outputs.drift_before_csv:
            self.outputs.drift_before_csv.parent.mkdir(parents=True, exist_ok=True)
            self._drift_before_file = self.outputs.drift_before_csv.open("w", newline="")
            self._drift_before_writer = csv.DictWriter(self._drift_before_file, fieldnames=self.fieldnames)
            self._drift_before_writer.writeheader()
        if self.outputs.drift_after_csv:
            self.outputs.drift_after_csv.parent.mkdir(parents=True, exist_ok=True)
            self._drift_after_file = self.outputs.drift_after_csv.open("w", newline="")
            self._drift_after_writer = csv.DictWriter(self._drift_after_file, fieldnames=self.fieldnames)
            self._drift_after_writer.writeheader()
        return self

    def __exit__(self, *args) -> None:
        for file in (
            self._raw_file,
            self._segmented_file,
            self._drift_before_file,
            self._drift_after_file,
        ):
            if file:
                file.close()

    def write(
        self,
        *,
        host_monotonic_timestamp_ns: int,
        telemetry: OrientationTelemetry,
        calibrated_yaw_deg: float,
        state: AcquisitionState,
    ) -> None:
        receive_interval_ms = ""
        if self._last_host_time_ns is not None:
            receive_interval_ms = (host_monotonic_timestamp_ns - self._last_host_time_ns) / 1_000_000.0
        self._last_host_time_ns = host_monotonic_timestamp_ns

        packet_loss_count = ""
        if telemetry.seq is not None and self._last_seq is not None:
            packet_loss_count = max(0, telemetry.seq - self._last_seq - 1)
        if telemetry.seq is not None:
            self._last_seq = telemetry.seq

        row = {
            "session_id": self.session_id,
            "host_monotonic_timestamp_ns": host_monotonic_timestamp_ns,
            "receive_interval_ms": receive_interval_ms,
            "packet_loss_count": packet_loss_count,
            "device_timestamp_ms": telemetry.device_time_ms if telemetry.device_time_ms is not None else "",
            "seq": telemetry.seq if telemetry.seq is not None else "",
            "packet_format": telemetry.packet_format,
            "packet_version": telemetry.version if telemetry.version is not None else "",
            "flags": telemetry.flags if telemetry.flags is not None else "",
            "ax_m_s2": telemetry.ax_m_s2 if telemetry.ax_m_s2 is not None else "",
            "ay_m_s2": telemetry.ay_m_s2 if telemetry.ay_m_s2 is not None else "",
            "az_m_s2": telemetry.az_m_s2 if telemetry.az_m_s2 is not None else "",
            "gx_rad_s": telemetry.gx_rad_s if telemetry.gx_rad_s is not None else "",
            "gy_rad_s": telemetry.gy_rad_s if telemetry.gy_rad_s is not None else "",
            "gz_rad_s": telemetry.gz_rad_s if telemetry.gz_rad_s is not None else "",
            "qw": telemetry.qw,
            "qx": telemetry.qx,
            "qy": telemetry.qy,
            "qz": telemetry.qz,
            "yaw_deg": telemetry.yaw_deg if telemetry.yaw_deg is not None else "",
            "calibrated_yaw_deg": calibrated_yaw_deg,
            "sigma_deg": "",
            "bmax_db": "",
            "audio_frame_index": "",
            "calibration_state": telemetry.calibration_state
            if telemetry.calibration_state is not None
            else "",
        }
        row.update(state.as_fields(host_monotonic_timestamp_ns))
        self._raw_writer.writerow(row)
        self._raw_file.flush()
        if state.include_in_analysis and state.segment_kind == "angle":
            self._segmented_writer.writerow(row)
            self._segmented_file.flush()
        elif state.include_in_analysis and state.segment_kind == "drift_before" and self._drift_before_writer:
            self._drift_before_writer.writerow(row)
            self._drift_before_file.flush()
        elif state.include_in_analysis and state.segment_kind == "drift_after" and self._drift_after_writer:
            self._drift_after_writer.writerow(row)
            self._drift_after_file.flush()


def default_guided_outputs(config: dict, run_name: str) -> GuidedOutputs:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = Path("experiments/exp01_orientation_characterization")
    raw_csv = base / "raw" / f"exp01_guided_{run_name}_{timestamp}.csv"
    if run_name == "all":
        segmented_csv = Path(config.get("telemetry_csv", base / "processed" / "segmented_orientation.csv"))
    else:
        segmented_csv = base / "processed" / f"segmented_{run_name}_{timestamp}.csv"
    drift = config.get("drift", {})
    return GuidedOutputs(
        raw_csv=raw_csv,
        segmented_csv=segmented_csv,
        drift_before_csv=Path(drift["before_csv"]) if drift.get("before_csv") else base / "processed" / "drift_before.csv",
        drift_after_csv=Path(drift["after_csv"]) if drift.get("after_csv") else base / "processed" / "drift_after.csv",
    )


async def run_guided_experiment_01(
    config: dict,
    *,
    run_name: str = "all",
    outputs: GuidedOutputs | None = None,
    device_name: str | None = None,
    include_drift: bool = True,
) -> GuidedOutputs:
    try:
        from bleak import BleakClient, BleakScanner
    except ImportError as exc:
        raise RuntimeError("exp01-guided-acquire requires installing the 'ble' optional dependency") from exc

    if run_name != "all" and run_name not in {"ascending", "descending", "randomized"}:
        raise ValueError("run_name must be all, ascending, descending or randomized")

    outputs = outputs or default_guided_outputs(config, run_name)
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    record_config = config.get("acquisition", {})
    drift_config = config.get("drift", {})
    settling_time_s = float(record_config.get("settling_time_s", 3.0))
    discard_initial_s = float(record_config.get("discard_initial_s", 2.0))
    analyzed_s = float(record_config.get("analyzed_stationary_interval_s", 8.0))
    drift_duration_s = float(drift_config.get("duration_s", 120.0))
    device_name = device_name or config.get("device_name", "Tiresias_DK")

    state = AcquisitionState()
    state_lock = threading.Lock()
    calibration = TareCalibration()
    tare_done = asyncio.Event()
    loop = asyncio.get_running_loop()

    await _prompt(
        "\nColoque a plataforma no 0 graus fisico, aguarde estabilizar e pressione Enter "
        "para conectar e tarar no primeiro pacote BLE."
    )
    print(f"Procurando dispositivo BLE com nome contendo {device_name!r}...")
    devices = await BleakScanner.discover(timeout=10.0)
    device = next((dev for dev in devices if dev.name and device_name in dev.name), None)
    if device is None:
        raise RuntimeError(f"BLE device matching {device_name!r} not found")
    print(f"Encontrado: {device.name} ({device.address})")

    with GuidedExperiment01Logger(outputs, session_id=session_id) as logger:
        async with BleakClient(device) as client:
            print("Conectou ao Tiresias.")

            def handler(_sender, data: bytearray) -> None:
                host_time_ns = time.perf_counter_ns()
                telemetry = decode_packet(bytes(data))
                calibrated_q = calibration.calibrate_first(telemetry.quaternion)
                calibrated_yaw = yaw_from_quaternion(calibrated_q)
                with state_lock:
                    state.latest_calibrated_yaw_deg = calibrated_yaw
                    state.packets_seen += 1
                    snapshot = AcquisitionState(**state.__dict__)
                logger.write(
                    host_monotonic_timestamp_ns=host_time_ns,
                    telemetry=telemetry,
                    calibrated_yaw_deg=calibrated_yaw,
                    state=snapshot,
                )
                if not tare_done.is_set():
                    loop.call_soon_threadsafe(tare_done.set)

            try:
                await client.start_notify(TELEMETRY_CHAR_UUID, handler)
                active_uuid = TELEMETRY_CHAR_UUID
                print(f"Assinou characteristic de telemetria: {TELEMETRY_CHAR_UUID}")
            except Exception as exc:
                print(f"Telemetria v1 indisponivel ({exc}); tentando quaternion legado.")
                await client.start_notify(LEGACY_QUATERNION_CHAR_UUID, handler)
                active_uuid = LEGACY_QUATERNION_CHAR_UUID
                print(f"Assinou characteristic legada: {LEGACY_QUATERNION_CHAR_UUID}")

            try:
                await asyncio.wait_for(tare_done.wait(), timeout=15.0)
                print("Tarou: primeiro pacote recebido no 0 graus fisico.")
                await _print_status_for(state, state_lock, "Estado apos tare")

                if include_drift and run_name == "all" and drift_config.get("measure_before", True):
                    await _record_drift(
                        state,
                        state_lock,
                        kind="drift_before",
                        duration_s=drift_duration_s,
                        label="deriva inicial em 0 graus",
                    )

                sequences = build_reference_sequences(config)
                selected_runs = ["ascending", "descending", "randomized"] if run_name == "all" else [run_name]
                for selected in selected_runs:
                    print(f"\n=== Iniciando serie {selected} ===")
                    for item in sequences[selected]:
                        await _record_angle_position(
                            state,
                            state_lock,
                            item=item,
                            settling_time_s=settling_time_s,
                            discard_initial_s=discard_initial_s,
                            analyzed_s=analyzed_s,
                        )

                if include_drift and run_name == "all" and drift_config.get("measure_after", True):
                    await _prompt("\nRetorne fisicamente a plataforma para 0 graus e pressione Enter.")
                    await _record_drift(
                        state,
                        state_lock,
                        kind="drift_after",
                        duration_s=drift_duration_s,
                        label="deriva final em 0 graus",
                    )
            finally:
                with state_lock:
                    state.update_phase("stopping", include_in_analysis=False, operator_event="stop_notify")
                await client.stop_notify(active_uuid)
                print("\nNotificacoes BLE encerradas.")

    print("\nAquisicao guiada concluida.")
    print(f"CSV bruto: {outputs.raw_csv}")
    print(f"CSV segmentado para metricas: {outputs.segmented_csv}")
    if outputs.drift_before_csv:
        print(f"Deriva inicial: {outputs.drift_before_csv}")
    if outputs.drift_after_csv:
        print(f"Deriva final: {outputs.drift_after_csv}")
    return outputs


async def _record_angle_position(
    state: AcquisitionState,
    state_lock: threading.Lock,
    *,
    item: dict,
    settling_time_s: float,
    discard_initial_s: float,
    analyzed_s: float,
) -> None:
    commanded = item["reference_angle_commanded_deg"]
    normalized = item["reference_angle_normalized_deg"]
    closure = item["is_closure_measurement"]
    run_type = item["run_type"]
    position_index = item["position_index"]
    closure_text = "SIM" if closure else "nao"
    with state_lock:
        state.run_id = run_type
        state.run_type = run_type
        state.position_index = position_index
        state.reference_angle_commanded_deg = commanded
        state.reference_angle_normalized_deg = normalized
        state.is_closure_measurement = closure
        state.segment_kind = "angle"
        state.update_phase("move", include_in_analysis=False, operator_event="move_to_angle")
    await _prompt(
        f"\n[{run_type} #{position_index:02d}] Mova ate {commanded} graus "
        f"(normalizado {normalized:.0f}; fechamento: {closure_text}). "
        "Pressione Enter quando estiver alinhado."
    )
    with state_lock:
        state.update_phase("settling", include_in_analysis=False, operator_event="settling")
    print(f"Estabilizando por {settling_time_s:.1f} s. Nao toque na base.")
    await _wait_with_status(settling_time_s, state, state_lock)

    with state_lock:
        state.update_phase("discard", include_in_analysis=False, operator_event="discard_transient")
    print(f"Medindo. Nao mova. Descartando transiente inicial por {discard_initial_s:.1f} s.")
    await _wait_with_status(discard_initial_s, state, state_lock)

    with state_lock:
        state.update_phase("stationary", include_in_analysis=True, operator_event="analyzed_stationary")
    print(f"Medindo intervalo analisado por {analyzed_s:.1f} s. NAO MOVA.")
    await _wait_with_status(analyzed_s, state, state_lock)

    with state_lock:
        state.update_phase("complete", include_in_analysis=False, operator_event="position_complete")
    await _print_status_for(state, state_lock, "Posicao armazenada")


async def _record_drift(
    state: AcquisitionState,
    state_lock: threading.Lock,
    *,
    kind: str,
    duration_s: float,
    label: str,
) -> None:
    with state_lock:
        state.run_id = kind
        state.run_type = kind
        state.position_index = 0
        state.reference_angle_commanded_deg = 0
        state.reference_angle_normalized_deg = 0
        state.is_closure_measurement = False
        state.segment_kind = kind
        state.update_phase("stationary", include_in_analysis=True, operator_event=kind)
    print(f"\nRegistrando {label} por {duration_s:.1f} s. Nao toque na plataforma.")
    await _wait_with_status(duration_s, state, state_lock)
    with state_lock:
        state.update_phase("complete", include_in_analysis=False, operator_event=f"{kind}_complete")


async def _wait_with_status(duration_s: float, state: AcquisitionState, state_lock: threading.Lock) -> None:
    start = time.perf_counter()
    next_print = 0.0
    while True:
        elapsed = time.perf_counter() - start
        if elapsed >= duration_s:
            break
        await asyncio.sleep(min(0.25, duration_s - elapsed))
        elapsed = time.perf_counter() - start
        if elapsed >= next_print or elapsed >= duration_s:
            await _print_status_for(
                state,
                state_lock,
                f"{min(elapsed, duration_s):5.1f}/{duration_s:.1f} s",
            )
            next_print += 1.0


async def _print_status_for(state: AcquisitionState, state_lock: threading.Lock, prefix: str) -> None:
    with state_lock:
        yaw = state.latest_calibrated_yaw_deg
        packets = state.packets_seen
        phase = state.segment_phase
    yaw_text = "indisponivel" if yaw is None else f"{yaw:8.2f} deg"
    print(f"{prefix} | fase={phase} | yaw_calibrado={yaw_text} | pacotes={packets}")


async def _prompt(message: str) -> None:
    await asyncio.to_thread(input, message + "\n> ")
