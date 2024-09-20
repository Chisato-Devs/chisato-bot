from harmonize import Player
from harmonize.objects import Track
from loguru import logger

from utils.basic import EmbedUI, ChisatoBot
from utils.basic.services.draw import DrawBadRequest, DrawService
from utils.handlers.entertainment.music import SEPARATOR_URI, NODE_ICON, WARN_ICON
from utils.handlers.entertainment.music.enums import FromSourceEmoji
from utils.handlers.entertainment.music.filters import FROM_FILTER
from utils.handlers.entertainment.music.tools import ConvertTime
from utils.i18n import ChisatoLocalStore
from .queue import QueueGenerator

_t = ChisatoLocalStore.load("./cogs/entertainment/music.py")


class PlayerEmbed:
    bot: ChisatoBot = ChisatoBot.from_cache()

    @classmethod
    async def generate(cls, player: Player) -> list[EmbedUI]:
        embeds = []
        locale = player.guild.preferred_locale
        current: Track = player.queue.current

        embed = EmbedUI(
            title=_t.get("music.player.title", locale=locale),
            description=(
                f"{getattr(FromSourceEmoji, current.source_name).value} ` [{ConvertTime.format(current.duration)}] `"
                f"[`{current.title} - {current.author}`]({current.uri})\n\n"
            ),
        ).set_footer(
            icon_url="https://i.ibb.co/ZXzW6K2/record.gif",
            text=_t.get("music.player.footer", locale=locale, values=(player.node.identifier,))
        )

        async with DrawService(cls.bot.session) as ir:
            if await ir.get_status():
                try:
                    file = await ir.draw_image(
                        "music_card",
                        musicArtwork=current.artwork_url or "None",
                        musicName=current.title,
                        musicArtistName=current.author,
                        musicSource=current.source_name.lower(),
                        musicFilter=FROM_FILTER.get(player.filters[0] if player.filters else None, "clear"),
                    )
                    embed.set_image(file=file)
                except DrawBadRequest as e:
                    logger.warning(f"{e.__class__.__name__}: {e}")

        volume_warning = " <:warn:1114365034999578634>" if player.volume > 100 else ""
        embed.description += (
                _t.get(
                    "music.player.volume.part", locale=locale, values=(str(player.volume),)
                ) + volume_warning + "\n"
        )

        if current.plugin_info and (
                album_name := current.plugin_info.get("albumName", "")
        ):
            album_name = f" `{album_name}`" if album_name else ""
            album_with_url = f" [{album_name}]({u})" if (u := current.plugin_info.get("albumUrl")) else album_name
            embed.description += _t.get("music.player.album.part", locale=locale) + album_with_url

        if player.queue.items:
            queue = list(player.queue.items.copy())

            total, tracks = QueueGenerator.slice_queue(10, queue=queue)
            embeds.append(EmbedUI(
                title=_t.get("music.title.next_tracks", locale=locale),
                description="\n".join(
                    QueueGenerator.generate(tracks, max_length=80)
                ) + ("\n`. . .`" if total > 10 else ""),
            ).set_image(
                SEPARATOR_URI
            ).set_footer(
                icon_url=NODE_ICON,
                text=_t.get(
                    "music.queue_length.footer", locale=locale
                ) + QueueGenerator.get_time_from_queue(player.queue.items),
            ))

        embeds.append(embed)

        if player.fetch_user_data("karaoke"):
            embeds.append(EmbedUI(
                title=_t.get("music.karaoke.title", locale=locale),
                description="\n".join(
                    f"# {line['line']}" if i == 1 else f"**{line['line']}**"
                    for i, line in enumerate(player.fetch_user_data('karaoke_need_lines'))
                    if line.get("line")
                )
            ).set_image(
                SEPARATOR_URI
            ).set_footer(
                icon_url=WARN_ICON,
                text=_t.get("music.karaoke.warn.footer", locale=locale),
            ))

        return embeds
