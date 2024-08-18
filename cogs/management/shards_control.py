import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

from disnake import ShardInfo
from disnake.ext.commands import Context, is_owner
from disnake.utils import format_dt
from loguru import logger

from utils.basic import CogUI, EmbedUI
from utils.consts import ERROR_EMOJI, SUCCESS_EMOJI
from utils.enviroment import env

if TYPE_CHECKING:
    from utils.basic import ChisatoBot


class ShardsControl(CogUI):

    async def _shard_reconnect_task(self, shard: ShardInfo) -> None:
        while shard.latency == float('inf'):
            logger.warning(f"Shard {shard.id} has infinity latency.")
            await self.bot.webhooks.post(
                data={
                    "embed": EmbedUI(
                        title=f"{ERROR_EMOJI} Бесконечная задержка",
                        description=f"Возникла проблема с шардом!\n\n"
                                    f"> **Рейт-лимит:** `{shard.is_ws_ratelimited()}`\n"
                                    f"> **Время**: {format_dt(datetime.now())} | `{datetime.now()}`\n"
                                    f"> **Шард:** `{shard.id}`\n"
                    )
                },
                type='shard_control'
            )

            try:
                await shard.connect()
                break
            except Exception as e:
                logger.critical(
                    f"An unknown error when connecting shard ({shard.id}): "
                    f"`{type(e).__name__}: {e}`"
                )
                await self.bot.webhooks.post(
                    data={
                        "embed": EmbedUI(
                            title=f"{ERROR_EMOJI} Проблема с подключением",
                            description=f"Возникла проблема с шардом!\n\n"
                                        f"> **Рейт-лимит:** `{shard.is_ws_ratelimited()}`\n"
                                        f"> **Время**: {format_dt(datetime.now())} | `{datetime.now()}`\n"
                                        f"> **Шард:** `{shard.id}`\n"
                        )
                    },
                    type='shard_control'
                )

            await asyncio.sleep(2)

    @CogUI.listener()
    async def on_shard_connect(self, shard_id: int) -> None:
        logger.info(f'Shard {shard_id} logged in as {self.bot.user}')
        await self.send_connected_webhook(self.bot.get_shard(shard_id))

    @CogUI.listener()
    async def on_shard_disconnect(self, shard_id: int) -> None:
        shard = self.bot.get_shard(shard_id)

        if self.bot.user and self.bot.user.id == env.MAIN_ID:
            try:
                await asyncio.wait_for(asyncio.create_task(self._shard_reconnect_task(shard)), timeout=20)
            except asyncio.TimeoutError:
                logger.warning(f"Shard {shard.id} has been disconnected.")
                await self.bot.webhooks.post(
                    data={
                        "embed": EmbedUI(
                            title=f"{ERROR_EMOJI} Отключение шарда",
                            description=f"Шард отключен!\n\n"
                                        f"> **Рейт-лимит:** `{shard.is_ws_ratelimited()}`\n"
                                        f"> **Время**: {format_dt(datetime.now())} | `{datetime.now()}`\n"
                                        f"> **Шард:** `{shard.id}`\n"
                        )
                    },
                    type='shard_control'
                )
            else:
                return None

            await self.bot.databases.admin.reg_to_analytics(
                "Проблема с шардом",
                Id=shard.id,
                Rate=shard.is_ws_ratelimited(),
                Closed=shard.is_closed(),
                Automatize=True
            )

    async def send_connected_webhook(self, shard: ShardInfo) -> None:
        if self.bot.user and self.bot.user.id != env.MAIN_ID:
            return

        latency = round(shard.latency * 1000) if shard.latency != float('inf') else 'Infinity'
        await self.bot.webhooks.post(
            data={
                "embed": EmbedUI(
                    title=f"{SUCCESS_EMOJI} Шард подключен",
                    description=f"> **Время:** {format_dt(datetime.now())} | `{datetime.now()}`\n"
                                f"> **Задержка:** `{latency}ms`\n"
                                f"> **Рейт-лимит:** `{shard.is_ws_ratelimited()}`\n"
                                f"> **Шард:** `{shard.id}`"
                )
            },
            type='shard_control'
        )

        if self.bot.databases:
            await self.bot.databases.admin.reg_to_analytics(
                f"Успешное подключение шарда",
                Id=shard.id,
                Rate=shard.is_ws_ratelimited(),
                Closed=shard.is_closed(),
                Automatize=True
            )

    @CogUI.context_command(name="shard_load", aliases=["sl"])
    @is_owner()
    async def shard_load(self, ctx: Context, shard_id: int) -> None:
        await self.bot.databases.admin.reg_to_analytics(
            f"Вызвана команда загрузки шарда",
            Id=shard_id,
            UserId=ctx.author.id,
            UserName=str(ctx.author)
        )

        if not (shard := self.bot.get_shard(shard_id)):
            await ctx.send("Такого шард(а) не существует!")
            return

        if shard.is_closed():
            await shard.connect()
            await ctx.send("Успешно загружен шард!")
            return

        await ctx.send("Данный шард не закрыт!")

    @CogUI.context_command(name="shard_reload", aliases=["sr"])
    @is_owner()
    async def shard_reload(self, ctx: Context, shard_id: int) -> None:
        await self.bot.databases.admin.reg_to_analytics(
            f"Вызвана команда перезагрузки шарда",
            Id=shard_id,
            UserId=ctx.author.id,
            UserName=str(ctx.author)
        )

        if not (shard := self.bot.get_shard(shard_id)):
            await ctx.send("Такого шард(а) не существует!")
            return

        await shard.reconnect()
        await self.send_connected_webhook(shard)
        await ctx.send("Успешно перегружен шард!")

    @CogUI.context_command(name="shard_statistic", aliases=["ss"])
    @is_owner()
    async def shard_statistic(self, ctx: Context) -> None:
        await self.bot.databases.admin.reg_to_analytics(
            f"Вызвана команда шард статистики",
            UserId=ctx.author.id,
            UserName=str(ctx.author)
        )

        formatted = []
        for shard_id, shard in self.bot.shards.items():
            latency = round(shard.latency * 1000) if shard.latency != float('inf') else 'Infinity'
            formatted.append(
                f"Shard {shard_id}\n"
                f"> Rate-Limited: {shard.is_ws_ratelimited()}\n"
                f"> Latency: {latency}\n"
            )

        await ctx.send("\n".join(formatted))


def setup(bot: "ChisatoBot") -> None:
    bot.add_cog(ShardsControl(bot))
