from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias

from utils.handlers.entertainment.music.enums import FromSourceEmoji
from utils.handlers.entertainment.music.tools import ConvertTime

if TYPE_CHECKING:
    from harmonize.objects import Track, PlaylistInfo

    QUEUE_TYPE: TypeAlias = list[Track | dict[str, PlaylistInfo | list[Track]]]

__all__ = (
    "QueueGenerator",
)

PLAYLIST_ICON: str = "<:playlist:1209962868930519100>"


class QueueGenerator:

    @classmethod
    def to_normal_time(cls, milliseconds: int) -> str:
        seconds = milliseconds // 1000
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @classmethod
    def get_time_from_queue(cls, queue: QUEUE_TYPE) -> str:
        return cls.to_normal_time(sum(
            sum(track.duration for track in obj["tracks"]) if isinstance(obj, dict) else obj.duration
            for obj in queue
        ))

    @classmethod
    def slice_queue(
            cls,
            count: int, /, *,
            queue: QUEUE_TYPE
    ) -> tuple[int, QUEUE_TYPE]:
        sliced = []
        tracks_count = 0

        for item in queue:
            if isinstance(item, dict) and "tracks" in item:
                trimmed_tracks = []
                for track in item["tracks"]:
                    if tracks_count < count:
                        trimmed_tracks.append(track)
                        tracks_count += 1
                    else:
                        break
                sliced.append({"tracks": trimmed_tracks, "playlist": item["playlist"]})
            elif tracks_count < count:
                sliced.append(item)
                tracks_count += 1

            if tracks_count >= count:
                break

        return (
            tracks_count,
            sliced
        )

    @classmethod
    def generate(
            cls,
            queue: QUEUE_TYPE,
            max_length: int = 80
    ) -> list[str]:
        return [
            cls.generate_playlist(i, data=track, max_length=max_length)
            if isinstance(track, dict) else
            cls.generate_stroke(i, track=track, max_length=max_length)

            for i, track in enumerate(queue, 1)
        ]

    @classmethod
    def generate_stroke(cls, i: int, *, track: Track, max_length: int = 80) -> str:
        return (
            (stroke[:max_length] + "..." + "`")
            if len(
                stroke := (
                    f"`{i}) `{getattr(FromSourceEmoji, track.source_name).value}"
                    f"` [{ConvertTime.format(track.duration)}] {track.title} - {track.author}`"
                )
            ) > max_length
            else stroke
        )

    @classmethod
    def generate_playlist(
            cls, i: int, *,
            data: dict[str, list[Track] | PlaylistInfo],
            max_length: int = 80
    ) -> str:
        stroke = (st[:max_length] + "..." + "`") if (
                len(st := f"`{i}) `{PLAYLIST_ICON}` {data["playlist"].name}`") > max_length) else st

        for e, track in enumerate(data["tracks"], 1):
            stroke += (
                f"\n` ` <:Minus:1126911673245106217> {cls.generate_stroke(e, track=track, max_length=80)[len(str(e)) + 4:]}"
            )

        return stroke
