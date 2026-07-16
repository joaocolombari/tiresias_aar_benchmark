from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from tiresias_benchmark.metrics.audio import normalized_rms_error, si_sdr_db


def run(config: dict) -> dict:
    simultaneous, fs_s = sf.read(Path(config["simultaneous_wav"]), dtype="float32")
    isolated_a, fs_a = sf.read(Path(config["isolated_a_wav"]), dtype="float32")
    isolated_b, fs_b = sf.read(Path(config["isolated_b_wav"]), dtype="float32")
    if len({fs_s, fs_a, fs_b}) != 1:
        raise ValueError("all WAV files must have the same sample rate")
    synthesized = isolated_a[: min(len(isolated_a), len(isolated_b))] + isolated_b[: min(len(isolated_a), len(isolated_b))]
    n = min(len(simultaneous), len(synthesized))
    sim = simultaneous[:n]
    syn = synthesized[:n]
    corr = float(np.corrcoef(np.ravel(sim), np.ravel(syn))[0, 1])
    return {
        "sample_rate_hz": fs_s,
        "correlation": corr,
        "normalized_rms_error": normalized_rms_error(syn, sim),
        "si_sdr_db": si_sdr_db(np.ravel(syn), np.ravel(sim)),
    }
