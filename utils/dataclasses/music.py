from dataclasses import dataclass

from harmonize.objects import Track


@dataclass
class CustomPlaylist:
    name: str
    id: int
    owner: int
    closed: bool
    tracks: list[Track]
    listened: int
