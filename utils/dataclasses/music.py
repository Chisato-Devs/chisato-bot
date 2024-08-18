from dataclasses import dataclass

from lavamystic import Playable


@dataclass
class CustomPlaylist:
    name: str
    id: int
    owner: int
    closed: bool
    tracks: list[Playable]
    listened: int
