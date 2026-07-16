from __future__ import annotations

from typing import Iterable

from .gaussian import Source
from tiresias_benchmark.orientation.quaternion import angular_distance_deg


def uniform_gains(sources: Iterable[Source], gain_linear: float = 1.0) -> dict[str, float]:
    return {source.name: float(gain_linear) for source in sources}


def hard_selection_gains(
    head_yaw_deg: float,
    sources: Iterable[Source],
    selected_gain_linear: float,
    unselected_gain_linear: float = 1.0,
) -> dict[str, float]:
    source_list = list(sources)
    nearest = min(source_list, key=lambda src: angular_distance_deg(src.azimuth_deg, head_yaw_deg))
    return {
        source.name: float(selected_gain_linear if source == nearest else unselected_gain_linear)
        for source in source_list
    }
