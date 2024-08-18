from typing import Final

from lavamystic import Filters

FILTERS: Final[dict[str, Filters]] = {
    "boost": Filters(
        data={
            "equalizer": [
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
            ]
        }
    ),
    "metal": Filters(
        data={
            "equalizer": [
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
            ]
        }
    ),
    "nightcore": Filters(
        data={
            "timescale": {
                "pitch": 1.2,
                "speed": 1.2,
                "rate": 1
            }
        }
    ),
    "slowed": Filters(
        data={
            "timescale": {
                "pitch": .9,
                "speed": .8,
                "rate": 1
            }
        }
    ),
    "karaoke": Filters(
        data={
            "karaoke": {
                "level": 1,
                "monoLevel": 1,
                "filterBand": 220,
                "filterWidth": 100
            }
        }
    ),
    "clear": Filters()
}

FROM_FILTER: Final[dict[Filters, str]] = {v: k for k, v in FILTERS.copy().items()}
