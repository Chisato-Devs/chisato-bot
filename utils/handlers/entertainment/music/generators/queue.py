from __future__ import annotations

from typing import TYPE_CHECKING

from utils.handlers.entertainment.music.enums import FromSourceEmoji
from utils.handlers.entertainment.music.tools import ConvertTime

if TYPE_CHECKING:
    from harmonize.objects import Track

__all__ = (
    "QueueGenerator",
)


class QueueGenerator:

    @classmethod
    def to_normal_time(cls, milliseconds: int) -> str:
        seconds = milliseconds // 1000
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @classmethod
    def generate(cls, queue: list[Track], max_length: int = 80) -> list[str]:
        return [
            (stroke[:max_length] + "..." + "`")
            if len(
                stroke := (
                    f"`{i}) `{getattr(FromSourceEmoji, track.source_name).value}"
                    f"` [{ConvertTime.format(track.duration)}] {track.title} - {track.author}`"
                )
            ) > max_length
            else stroke

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
