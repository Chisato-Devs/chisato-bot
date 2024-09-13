from __future__ import annotations

from typing import Final, TYPE_CHECKING

from harmonize.objects import Equalizer, Timescale, Karaoke

if TYPE_CHECKING:
    from harmonize.abstract import Filter

FILTERS: Final[dict[str, Filter]] = {
    "boost": Equalizer([
        {"band": 0, "gain": -.075},
        {"band": 1, "gain": .125},
        {"band": 2, "gain": .125},
        {"band": 3, "gain": .1},
        {"band": 4, "gain": .1},
        {"band": 5, "gain": .05},
        {"band": 6, "gain": .075},
        {"band": 7, "gain": .0},
        {"band": 8, "gain": .0},
        {"band": 9, "gain": .0},
        {"band": 10, "gain": .0},
        {"band": 11, "gain": .0},
        {"band": 12, "gain": .125},
        {"band": 13, "gain": .15},
        {"band": 14, "gain": .05}
    ]),
    "metal": Equalizer([
        {'band': 0, 'gain': 0.0},
        {'band': 1, 'gain': 0.1},
        {'band': 2, 'gain': 0.1},
        {'band': 3, 'gain': 0.15},
        {'band': 4, 'gain': 0.13},
        {'band': 5, 'gain': 0.1},
        {'band': 6, 'gain': 0.0},
        {'band': 7, 'gain': 0.125},
        {'band': 8, 'gain': 0.175},
        {'band': 9, 'gain': 0.175},
        {'band': 10, 'gain': 0.125},
        {'band': 11, 'gain': 0.125},
        {'band': 12, 'gain': 0.1},
        {'band': 13, 'gain': 0.075},
        {'band': 14, 'gain': 0.0}
    ]),
    "nightcore": Timescale(**{
        "pitch": 1.2,
        "speed": 1.2,
        "rate": 1
    }),
    "slowed": Timescale(**{
        "pitch": .9,
        "speed": .8,
        "rate": 1
    }),
    "karaoke": Karaoke(**{
        "level": 1,
        "mono_level": 1,
        "filter_band": 220,
        "filter_width": 100
    })
}

FROM_FILTER: Final[dict[Filter, str]] = {v: k for k, v in FILTERS.copy().items()}
