from asyncio import sleep
from random import choice

from disnake import Status, Activity, ActivityType, HTTPException
from disnake.ext.tasks import loop
from loguru import logger

from utils.basic import CogUI, ChisatoBot, IntFormatter
from utils.basic.services.draw import DrawService
from utils.basic.services.draw.types import ContentType


class EditProfile(CogUI):
    STATUSES = [Status.online, Status.dnd, Status.idle]
    DESCRIPTIONS = [
        "❤️ Thanks for using Chisato!",
        "✨ Something unimaginably cool",
        "🤍 Check my profile!",
        "💫 Version V2.3.2"
    ]

    def cog_unload(self) -> None:
        self.edit_profile_loop.cancel()

    async def cog_load(self) -> None:
        await self.bot.wait_until_first_connect()
        await sleep(5)
        self.edit_profile_loop.start()

    async def change_presence(self, activity_name: str) -> None:
        await self.bot.change_presence(
            status=choice(self.STATUSES),
            activity=Activity(
                type=ActivityType.watching,
                name=activity_name
            )
        )

    async def change_my_banner(self) -> None:
        async with DrawService(self.bot.session) as ir:
            _b = await ir.draw_image(
                "discord_banner",
                guildCount=IntFormatter(len(self.bot.guilds)).format_number(),
                usersCount=IntFormatter(len(self.bot.users)).format_number(),
                content_type=ContentType.BYTES
            )
        await self.bot.user.edit(banner=_b)

    @loop(minutes=10)
    async def edit_profile_loop(self):
        try:
            if await DrawService(self.bot.session).get_status():
                await self.change_my_banner()
        except HTTPException:
            logger.warning("Can't edit profile yet")
        await self.change_presence(choice(self.DESCRIPTIONS))


def setup(bot: ChisatoBot) -> None:
    return bot.add_cog(EditProfile(bot))
