from __future__ import annotations

import secrets
from http.client import HTTPException
from typing import TYPE_CHECKING

from utils.basic import EmbedUI
from utils.handlers.entertainment.music.generators.queue import QueueGenerator
from utils.handlers.pagination import PaginatorView
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from disnake import Embed, Member, Message, NotFound, MessageInteraction

    from harmonize import Queue
    from harmonize.objects import Track

__all__ = (
    "QueuePagination",
)

_t = ChisatoLocalStore.load("./cogs/entertainment/music.py")


class QueuePagination(PaginatorView):
    _cache: dict[str, Message] = {}

    def __init__(self, embeds: list[Embed], author: Member, interaction: MessageInteraction = None) -> None:
        self.cache_id = secrets.token_hex(16)
        self._interaction = interaction
        super().__init__(
            embeds=embeds,
            author=author,
            timeout=120,
            footer=True,
            delete_button=True
        )

    async def on_timeout(self) -> None:
        try:
            if message := self._cache.get(self.cache_id):
                await message.delete()
                self.remove_cache()

            elif self._interaction:
                await self.custom_defer(self._interaction)
        except HTTPException:
            pass
        except NotFound:
            pass
        except AttributeError:
            pass

    @classmethod
    async def generate(
            cls, queue: Queue | list[Track], author: Member, total_time: bool = True
    ) -> tuple[QueuePagination | None, Embed | None]:
        embeds = []
        strokes = []
        for i, track in enumerate(queue, 1):
            strokes.append(QueueGenerator.generate_stroke(i, track=track, max_length=80))

            if i % 20 == 0 or len(queue) == i:
                embed = EmbedUI(
                    title=_t.get(
                        "music.queue.title",
                        locale=author.guild.preferred_locale
                    ),
                    description="\n".join(strokes)
                )

                embeds.append(embed)

                if total_time:
                    embed.description += "\n# <:HourGlass:1239232681292595220>" + _t.get(
                        "music.playlist.queue_length.footer",
                        locale=author.guild.preferred_locale
                    ) + QueueGenerator.to_normal_time(
                        sum(map(lambda x: x.length, queue), 0)
                    )

                strokes.clear()

        return cls(embeds, author) if embeds else None, embeds[0] if embeds else None

    def add_cache(self, message: Message) -> None:
        self._cache[self.cache_id] = message

    def remove_cache(self) -> None:
        if self._cache.get(self.cache_id):
            del self._cache[self.cache_id]
