from __future__ import annotations

from pathlib import Path

import soundfile as sf

from tiresias_benchmark.acoustics.deconvolution import (
    regularized_deconvolution,
    trim_response_around_peak,
)


def run(config: dict) -> dict:
    recorded_wav = Path(config["recorded_wav"])
    reference_wav = Path(config["reference_wav"])
    output_wav = Path(config["output_ir_wav"])
    response_length_samples = int(config.get("response_length_samples", 14_400))
    recorded, fs_r = sf.read(recorded_wav, dtype="float32")
    reference, fs_x = sf.read(reference_wav, dtype="float32")
    if fs_r != fs_x:
        raise ValueError("recorded and reference WAV sample rates differ")
    if recorded.ndim > 1:
        recorded = recorded[:, int(config.get("recorded_channel", 0))]
    if reference.ndim > 1:
        reference = reference[:, int(config.get("reference_channel", 0))]
    response = regularized_deconvolution(recorded, reference)
    response = trim_response_around_peak(response, length_samples=response_length_samples)
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    sf.write(output_wav, response, fs_r)
    return {"output_ir_wav": str(output_wav), "sample_rate_hz": fs_r, "samples": len(response)}
