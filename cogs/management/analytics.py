from __future__ import annotations

import ast
from asyncio import gather
from collections import defaultdict
from datetime import datetime
from io import BytesIO
from typing import TYPE_CHECKING

import numpy as np
from disnake import Forbidden, NotFound, HTTPException, File, ApplicationCommandInteraction
from disnake.ext.commands import command, Context, is_owner
from disnake.ext.tasks import loop

from utils.basic import CogUI, EmbedUI
from utils.handlers.pagination import PaginatorView

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

EMOJI_HEART = '<:Heart:1131438234296123513>'


class Analytics(CogUI):
    def __init__(self, bot: ChisatoBot) -> None:
        self._checked = False

        super().__init__(bot=bot)

    async def cog_load(self) -> None:
        await self.bot.wait_until_first_connect()

        self.reset_temp_data_loop.start()

    def cog_unload(self) -> None:
        self.reset_temp_data_loop.cancel()

    async def generate_analytics_files(self) -> list[File]:
        files: list[File] = []

        analytics_logs_data, analytics_commands_data_per_day = await gather(
            self.bot.databases.admin.get_analytics_logs_data(),
            self.bot.databases.admin.get_analytics_commands_data(per_day=True),
        )

        if analytics_logs_data:
            analytics_logs_data = np.array(analytics_logs_data)
            sorted_data = analytics_logs_data[np.argsort(analytics_logs_data[:, 2].astype(float))]

            typed_dict = defaultdict(int)
            lines = []

            for _, f_type, f_date, f_args in sorted_data:
                typed_dict[f_type] += 1
                unpacked = " | ".join(f"{k}: {v}" for k, v in ast.literal_eval(f_args).items())
                lines.append(f'> {datetime.fromtimestamp(float(f_date))} | {f_type} | ({unpacked})')

            lines.append("-------------------------------------------------------")
            lines.extend(f"{k}: {v}" for k, v in sorted(typed_dict.items(), key=lambda x: x[1], reverse=True))

            files.append(File(BytesIO("\n".join(lines).encode('utf-8')), filename="logs.txt"))

        if analytics_commands_data_per_day:
            files.append(
                File(
                    BytesIO(("\n".join([
                        f'> {i} | /{record[0].replace(".", " ")} - {record[1]}'
                        for i, record in enumerate(sorted(analytics_commands_data_per_day, key=lambda x: x[1]))
                    ]) + "\n").encode("UTF-8")),
                    filename="commands_uses.txt"
                )
            )

        return files

    @loop(minutes=5)
    async def reset_temp_data_loop(self) -> None:
        if not self.bot.databases:
            return

        if datetime.now().hour == 11:
            if not self._checked and (files := await self.generate_analytics_files()):
                await self.bot.webhooks.post(
                    data={
                        'embed': EmbedUI(
                            title=f"{EMOJI_HEART} Статистика за день",
                            description=f"> **Время:** {datetime.now()} | `{datetime.now().timestamp()}`"
                        ),
                        'files': files
                    },
                    type="day_statistic"
                )
                await self.bot.databases.admin.truncate_analytics_per_day()
                self._checked = True
        else:
            if self._checked:
                self._checked = False

    @command(name='command_stats', aliases=['cs'])
    @is_owner()
    async def _check(self, ctx: Context) -> None:
        try:
            await ctx.message.delete()
        except (Forbidden, NotFound, HTTPException):
            pass

        data_per_day = sorted(
            await self.bot.databases.admin.get_analytics_commands_data(per_day=True),
            key=lambda x: x[1]
        )
        data_all_time = sorted(
            await self.bot.databases.admin.get_analytics_commands_data(),
            key=lambda x: x[1]
        )

        embeds: list[EmbedUI] = []
        if data_per_day:
            embeds.append(
                EmbedUI(
                    title=f'{EMOJI_HEART} Статистика за сегодня',
                    description='\n'.join([
                        f'> **/{name.replace(".", " ")}** - `{uses}`'
                        for name, uses in data_per_day
                    ]),
                    timestamp=datetime.now()
                )
            )

        if data_all_time:
            embeds.append(
                EmbedUI(
                    title=f'{EMOJI_HEART} Статистика за все время!',
                    description='\n'.join([
                        f'> **/{name.replace(".", " ")}** - `{uses}`'
                        for name, uses in data_all_time
                    ]),
                    timestamp=datetime.now()
                )
            )

        await ctx.send(
            embed=embeds[0],
            view=PaginatorView(
                embeds=embeds, delete_button=True,
                footer=False, author=ctx.author
            )
        )

    @CogUI.listener('on_application_command')
    async def register_use(
            self, interaction: ApplicationCommandInteraction
    ) -> None:
        try:
            await self.bot.databases.admin.reg_command(
                name=interaction.application_command.qualified_name.replace(' ', '.')
            )
        except OSError:
            pass
        except AttributeError:
            pass


def setup(bot: ChisatoBot) -> None:
    bot.add_cog(Analytics(bot))
