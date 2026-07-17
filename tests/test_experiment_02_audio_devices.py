import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from tiresias_benchmark.cli import load_yaml
from tiresias_benchmark.experiments import experiment_02_audio as audio


CONFIG_PATH = Path("experiments/exp02_brir_measurement/config.yaml")


class FakeCallbackStop(Exception):
    pass


class FakeCallbackTime:
    inputBufferAdcTime = 0.0
    currentTime = 0.0
    outputBufferDacTime = 0.0


class FakeStream:
    def __init__(self, owner, **kwargs):
        self.owner = owner
        self.kwargs = kwargs
        self.latency = (0.01, 0.02)

    def __enter__(self):
        self.owner.stream_calls.append(self.kwargs)
        callback = self.kwargs.get("callback")
        if callback:
            channels = self.kwargs["channels"]
            frames = int(self.kwargs["blocksize"])
            dtype = np.dtype(self.kwargs.get("dtype", "float32"))
            indata = np.zeros((frames, channels[0]), dtype=dtype)
            outdata = np.zeros((frames, channels[1]), dtype=dtype)
            for _ in range(256):
                try:
                    callback(indata, outdata, frames, FakeCallbackTime(), 0)
                except FakeCallbackStop:
                    break
        return self

    def __exit__(self, exc_type, exc, tb):
        return exc_type is FakeCallbackStop


class FakeSoundDevice:
    CallbackStop = FakeCallbackStop

    def __init__(self, hostapis, devices, accepted_dtypes=None):
        self._hostapis = hostapis
        self._devices = devices
        self.accepted_dtypes = set(accepted_dtypes or ["float32", "int32", "int16"])
        self.input_checks = []
        self.output_checks = []
        self.stream_calls = []

    def query_hostapis(self):
        return self._hostapis

    def query_devices(self):
        return self._devices

    def check_input_settings(self, **kwargs):
        self.input_checks.append(kwargs)
        if kwargs.get("dtype") not in self.accepted_dtypes:
            raise RuntimeError("Sample format not supported [PaErrorCode -9994]")

    def check_output_settings(self, **kwargs):
        self.output_checks.append(kwargs)
        if kwargs.get("dtype") not in self.accepted_dtypes:
            raise RuntimeError("Sample format not supported [PaErrorCode -9994]")

    def Stream(self, **kwargs):  # noqa: N802 - mirrors sounddevice API
        if kwargs.get("dtype") not in self.accepted_dtypes:
            raise RuntimeError("Sample format not supported [PaErrorCode -9994]")
        return FakeStream(self, **kwargs)

    def sleep(self, milliseconds):
        self.sleep_ms = milliseconds


def wdm_ks_devices():
    hostapis = [{"name": "Windows WDM-KS", "default_input_device": 26, "default_output_device": 27}]
    devices = [
        {
            "name": "Analogue 1 + 2 (wc4800_8214)",
            "hostapi": 0,
            "max_input_channels": 8,
            "max_output_channels": 0,
            "default_samplerate": 48000.0,
        },
        {
            "name": "Speakers (wr4800_8214)",
            "hostapi": 0,
            "max_input_channels": 0,
            "max_output_channels": 8,
            "default_samplerate": 48000.0,
        },
    ]
    return hostapis, devices


def wdm_ks_config():
    config = load_yaml(CONFIG_PATH)
    config["audio_device"]["preferred_host_api"] = "Windows WDM-KS"
    config["audio_device"]["input_device_name_contains"] = "Analogue 1 + 2"
    config["audio_device"]["output_device_name_contains"] = "Speakers"
    config["audio_device"]["stream_dtype_candidates"] = ["float32", "int32", "int16"]
    return config


def core_audio_devices():
    hostapis = [{"name": "Core Audio", "default_input_device": 0, "default_output_device": 0}]
    devices = [
        {
            "name": "Scarlett 18i8 USB",
            "hostapi": 0,
            "max_input_channels": 8,
            "max_output_channels": 8,
            "default_samplerate": 48000.0,
        }
    ]
    return hostapis, devices


class Experiment02AudioDeviceTests(unittest.TestCase):
    def test_default_config_selects_core_audio_scarlett(self):
        config = load_yaml(CONFIG_PATH)
        hostapis, devices = core_audio_devices()
        pair = audio.select_audio_device_pair_from_query(config, hostapis, devices)

        self.assertEqual(pair.input_device_index, 0)
        self.assertEqual(pair.output_device_index, 0)
        self.assertEqual(pair.host_api_name, "Core Audio")

    def test_selects_separate_wdm_ks_input_output_pair(self):
        config = wdm_ks_config()
        hostapis, devices = wdm_ks_devices()
        pair = audio.select_audio_device_pair_from_query(config, hostapis, devices)

        self.assertEqual(pair.input_device_index, 0)
        self.assertEqual(pair.output_device_index, 1)
        self.assertEqual(pair.host_api_name, "Windows WDM-KS")
        self.assertEqual(pair.requested_input_channels, 4)
        self.assertEqual(pair.requested_output_channels, 4)

    def test_list_classifies_directions_and_candidate_pairs(self):
        config = wdm_ks_config()
        fake = FakeSoundDevice(*wdm_ks_devices())
        with patch.object(audio, "_require_sounddevice", return_value=fake):
            result = audio.list_audio_devices(config)

        self.assertEqual(result["devices"][0]["direction"], "input-only")
        self.assertEqual(result["devices"][1]["direction"], "output-only")
        self.assertTrue(result["candidate_pairs"][0]["supports_requested_settings"])

    def test_rejects_host_api_mismatch(self):
        config = wdm_ks_config()
        config["audio_device"]["preferred_host_api"] = ""
        hostapis, devices = wdm_ks_devices()
        hostapis.append({"name": "ASIO", "default_input_device": -1, "default_output_device": -1})
        devices[1] = {**devices[1], "hostapi": 1}

        with self.assertRaisesRegex(RuntimeError, "host API mismatch"):
            audio.select_audio_device_pair_from_query(config, hostapis, devices)

    def test_rejects_insufficient_input_channels(self):
        config = wdm_ks_config()
        hostapis, devices = wdm_ks_devices()
        devices[0] = {**devices[0], "max_input_channels": 2}

        with self.assertRaisesRegex(RuntimeError, "insufficient input channels"):
            audio.select_audio_device_pair_from_query(config, hostapis, devices)

    def test_rejects_insufficient_output_channels(self):
        config = wdm_ks_config()
        hostapis, devices = wdm_ks_devices()
        devices[1] = {**devices[1], "max_output_channels": 2}

        with self.assertRaisesRegex(RuntimeError, "insufficient output channels"):
            audio.select_audio_device_pair_from_query(config, hostapis, devices)

    def test_single_full_duplex_device_remains_supported(self):
        config = load_yaml(CONFIG_PATH)
        config["audio_device"]["input_device_name_contains"] = "Scarlett"
        config["audio_device"]["output_device_name_contains"] = "Scarlett"
        hostapis = [{"name": "ASIO", "default_input_device": 0, "default_output_device": 0}]
        devices = [
            {
                "name": "Focusrite USB ASIO Scarlett",
                "hostapi": 0,
                "max_input_channels": 8,
                "max_output_channels": 8,
                "default_samplerate": 48000.0,
            }
        ]
        config["audio_device"]["preferred_host_api"] = "ASIO"
        pair = audio.select_audio_device_pair_from_query(config, hostapis, devices)

        self.assertEqual(pair.input_device_index, 0)
        self.assertEqual(pair.output_device_index, 0)

    def test_asio_can_select_by_host_api_when_name_filters_are_blank(self):
        config = load_yaml(CONFIG_PATH)
        config["audio_device"]["preferred_host_api"] = "ASIO"
        config["audio_device"]["input_device_name_contains"] = ""
        config["audio_device"]["output_device_name_contains"] = ""
        hostapis = [{"name": "ASIO", "default_input_device": 0, "default_output_device": 0}]
        devices = [
            {
                "name": "Focusrite USB Audio",
                "hostapi": 0,
                "max_input_channels": 8,
                "max_output_channels": 8,
                "default_samplerate": 48000.0,
            }
        ]

        pair = audio.select_audio_device_pair_from_query(config, hostapis, devices)

        self.assertEqual(pair.input_device_index, 0)
        self.assertEqual(pair.output_device_index, 0)
        self.assertEqual(pair.host_api_name, "ASIO")

    def test_preflight_opens_single_stream_with_device_pair_and_4x4_channels(self):
        config = wdm_ks_config()
        fake = FakeSoundDevice(*wdm_ks_devices())
        with patch.object(audio, "_require_sounddevice", return_value=fake):
            result = audio.preflight_audio(config, duration_s=0.01, open_stream=True)

        self.assertTrue(result["passed"])
        self.assertEqual(fake.input_checks[0]["device"], 0)
        self.assertEqual(fake.output_checks[0]["device"], 1)
        self.assertEqual(fake.stream_calls[0]["device"], (0, 1))
        self.assertEqual(fake.stream_calls[0]["channels"], (4, 4))

    def test_format_probe_falls_back_when_float32_is_rejected(self):
        config = wdm_ks_config()
        fake = FakeSoundDevice(*wdm_ks_devices(), accepted_dtypes=["int16"])
        with patch.object(audio, "_require_sounddevice", return_value=fake):
            result = audio.probe_audio_formats(config, duration_s=0.01, open_stream=True)

        self.assertEqual(result["selected_stream_dtype"], "int16")
        by_dtype = {item["stream_dtype"]: item for item in result["candidates"]}
        self.assertFalse(by_dtype["float32"]["passed"])
        self.assertTrue(by_dtype["int16"]["passed"])

    def test_preflight_uses_selected_fallback_dtype(self):
        config = wdm_ks_config()
        fake = FakeSoundDevice(*wdm_ks_devices(), accepted_dtypes=["int16"])
        with patch.object(audio, "_require_sounddevice", return_value=fake):
            result = audio.preflight_audio(config, duration_s=0.01, open_stream=True)

        self.assertTrue(result["passed"])
        self.assertEqual(result["stream_dtype"], "int16")
        self.assertEqual(fake.stream_calls[-1]["dtype"], "int16")

    def test_real_record_metadata_registers_both_devices_with_fake_stream(self):
        config = wdm_ks_config()
        fake = FakeSoundDevice(*wdm_ks_devices(), accepted_dtypes=["int16"])
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(audio, "_require_sounddevice", return_value=fake):
                result = audio.record_probe(
                    config=config,
                    speaker="A",
                    session_id="fake_hw",
                    output_root=tmp,
                    armed=True,
                )
            metadata = json.loads(result.metadata_json.read_text())

        self.assertEqual(metadata["audio_selection"]["input_device_name"], "Analogue 1 + 2 (wc4800_8214)")
        self.assertEqual(metadata["audio_selection"]["output_device_name"], "Speakers (wr4800_8214)")
        self.assertEqual(metadata["stream_dtype"], "int16")
        self.assertEqual(metadata["storage_dtype"], "float32")
        self.assertEqual(fake.stream_calls[0]["device"], (0, 1))

    def test_dry_run_simulation_still_works_without_sounddevice(self):
        config = load_yaml(CONFIG_PATH)
        with tempfile.TemporaryDirectory() as tmp:
            result = audio.record_probe(
                config=config,
                speaker="A",
                session_id="sim",
                output_root=tmp,
                simulate=True,
            )
            self.assertTrue(result.raw_input_wav.exists())


if __name__ == "__main__":
    unittest.main()
