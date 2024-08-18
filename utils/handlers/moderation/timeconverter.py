from datetime import datetime, timedelta

from disnake import Member, Embed, Locale

from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load("./cogs/moderation/ban.py")


class BoundEmbedErrorUI(Embed):
    def __init__(self, description: str, member: Member) -> None:
        super().__init__(
            description=f"<:RemoveCircle:1113824544709414984> | **{member.display_name}**, " + description,
            color=0x2b2d31
        )


async def time_converter(
        time: str,
        member: Member,
        timeout: bool = False,
        locale: Locale = Locale.ru
) -> datetime | BoundEmbedErrorUI:
    time_units: dict[str, int] = {'m': 1, 'h': 60, 'd': 1440, 'w': 10080}

    try:
        amount: int = int(time[:-1])
        unit: str = time[-1]

        if unit not in time_units:
            return BoundEmbedErrorUI(_t.get("ban.command.callback.error.format_time", locale=locale), member)

        minutes: int = amount * time_units[unit]
        if timeout is False and minutes > 44640:
            return BoundEmbedErrorUI(_t.get("ban.command.callback.error.more_year", locale=locale), member)

        if timeout is True and minutes > 40320:
            return BoundEmbedErrorUI(
                _t.get("ban.command.callback.error.timeout_more_28_day", locale=locale), member
            )

        return datetime.now() + timedelta(minutes=minutes)

    except ValueError:
        return BoundEmbedErrorUI(_t.get("ban.command.callback.error.format_time", locale=locale), member)
