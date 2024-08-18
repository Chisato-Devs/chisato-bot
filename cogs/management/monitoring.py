import asyncio
from typing import Union, TYPE_CHECKING

from aiohttp import ClientSession
from boticordpy import BoticordClient
from disnake.ext.tasks import loop
from loguru import logger

from utils.basic import CogUI
from utils.enviroment import env

if TYPE_CHECKING:
    from utils.basic import ChisatoBot
    from disnake.ext.commands import Bot


class Monitoring(CogUI):
    def __init__(self, bot: Union["ChisatoBot", "Bot"]) -> None:
        self.boticord_client = BoticordClient(
            version=3, token=env.BOTICORD_TOKEN
        )
        self.boti_task = None

        super().__init__(bot)

    async def cog_load(self) -> None:
        await self.bot.wait_until_first_connect()
        await asyncio.sleep(20)

        if self.bot.user.id == env.MAIN_ID:
            self.boti_task = self.boticord_client.autopost() \
                .init_stats(self.get_stats) \
                .start(self.bot.user.id)

            self.sdc_post_loop.start()

    def cog_unload(self) -> None:
        if self.bot.user.id == env.MAIN_ID:
            self.sdc_post_loop.cancel()
            try:
                self.boti_task.cancel()
            except AttributeError:
                pass

    async def get_stats(self) -> dict[str, int]:
        data = {
            "servers": len(self.bot.guilds),
            "shards": self.bot.shard_count,
            "members": len(self.bot.users)
        }
        if self.bot.databases:
            await self.bot.databases.admin.reg_to_analytics(
                f"Статистика на BOTICORD отправлена",
                Servers=len(self.bot.guilds),
                Shards=self.bot.shard_count,
                Members=len(self.bot.users)
            )

        return data

    @loop(minutes=40)
    async def sdc_post_loop(self) -> None:
        async with ClientSession() as session:
            async with session.post(
                    url=f"https://api.server-discord.com/v2/bots/{self.bot.user.id}/stats",
                    headers={"Authorization": "SDC " + env.SDC_TOKEN},
                    data={
                        "servers": len(self.bot.guilds),
                        "shards": len(self.bot.shards)
                    }
            ) as response:
                if response.status != 200:
                    logger.log(
                        "WARN",
                        f"REQUEST ({response.status}) SUBMISSION ERROR! {await response.json()}"
                    )
                    return
                await self.bot.databases.admin.reg_to_analytics(
                    f"Статистика на SDC отправлена",
                    Servers=len(self.bot.guilds),
                    Members=len(self.bot.users)
                )


def setup(bot: Union["ChisatoBot", "Bot"]) -> None:
    return bot.add_cog(Monitoring(bot))
