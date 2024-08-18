from __future__ import annotations

from typing import TYPE_CHECKING

from disnake.ext.commands import Context, is_owner

from utils.basic import CogUI

if TYPE_CHECKING:
    from utils.basic import ChisatoBot


class ModulesSetting(CogUI):

    @CogUI.context_command(name="reload", aliases=["cr"])
    @is_owner()
    async def reload(self, ctx: Context, folder: str, cog_name: str) -> None:
        try:
            self.bot.reload_extension(cog_path := f"cogs.{folder}.{cog_name}")
            await ctx.send("Успешная перезагрузка кога!")

            await self.bot.databases.admin.reg_to_analytics(
                "Перезагрузка кога",
                CogPath=cog_path,
                UserId=ctx.author.id,
                UserName=str(ctx.author)
            )
        except Exception as e:
            await ctx.send(str(e))

    @CogUI.context_command(name="load", aliases=["cl"])
    @is_owner()
    async def load(self, ctx: Context, folder: str, cog_name: str) -> None:
        try:
            self.bot.load_extension(cog_path := f"cogs.{folder}.{cog_name}")
            await ctx.send("Успешная загрузка кога!")

            await self.bot.databases.admin.reg_to_analytics(
                "Загрузка кога",
                CogPath=cog_path,
                UserId=ctx.author.id,
                UserName=str(ctx.author)
            )
        except Exception as e:
            await ctx.send(str(e))

    @CogUI.context_command(name="unload", aliases=["cu"])
    @is_owner()
    async def unload(self, ctx: Context, folder: str, cog_name: str) -> None:
        try:
            self.bot.unload_extension(cog_path := f"cogs.{folder}.{cog_name}")
            await ctx.send("Успешная выгрузка кога!")

            await self.bot.databases.admin.reg_to_analytics(
                "Выгрузка кога",
                CogPath=cog_path,
                UserId=ctx.author.id,
                UserName=str(ctx.author)
            )
        except Exception as e:
            await ctx.send(str(e))


def setup(bot: ChisatoBot) -> None:
    return bot.add_cog(ModulesSetting(bot))
