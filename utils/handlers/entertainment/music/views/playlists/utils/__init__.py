from disnake import SelectOption

from utils.basic import ChisatoBot
from utils.dataclasses.music import CustomPlaylist

__all__ = (
    "Utils"
)


class Utils:

    @staticmethod
    def _dump_playlist(
            position: int,
            playlist: CustomPlaylist,
            to_add: dict[str, CustomPlaylist]
    ) -> str:
        to_add[str(position)] = playlist
        return str(position)

    @classmethod
    def generate_options(
            cls, data: list[CustomPlaylist], to_add: dict[str, CustomPlaylist]
    ) -> list[SelectOption]:
        return [
            SelectOption(
                label=playlist.name,
                emoji="<:playlist:1209962868930519100>",
                value=cls._dump_playlist(i, playlist, to_add)
            )

            for i, playlist in enumerate(data, 1)
        ]

    @classmethod
    async def get_author(cls, playlist: CustomPlaylist) -> str:
        user = await ChisatoBot.from_cache().getch_user(playlist.owner)
        return str(user) if user else "Unknown"
