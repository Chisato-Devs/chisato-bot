from __future__ import annotations

import string
import traceback
from random import choices
from typing import TYPE_CHECKING

import aiofiles
from disnake import File, ApplicationCommandInteraction, MessageInteraction

from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import EmbedUI

_t = ChisatoLocalStore.load("./cogs/management/errors.py")


class Trace:

    @staticmethod
    async def create_traceback_file(path: str, *, exception: Exception) -> None:
        tb_list = traceback.format_exception(type(exception), exception, exception.__traceback__)
        async with aiofiles.open(path, 'w', encoding='utf-8') as f:
            for trace in tb_list:
                for line in trace:
                    await f.write(line)

    @classmethod
    async def generate(
            cls,
            exception: Exception,
            interaction: ApplicationCommandInteraction | MessageInteraction,
            embed: EmbedUI = None
    ) -> None:
        from utils.basic import ChisatoBot

        files = []

        file_path = f'_cache/{"".join(choices(string.ascii_letters + string.digits, k=21)) + ".log"}'
        await cls.create_traceback_file(file_path, exception=exception)
        files.append(File(file_path))

        content = (
            f"User: `{interaction.author}` "
            f"| Guild: `{interaction.guild} [{interaction.guild.id}]`"
        )

        if isinstance(interaction, ApplicationCommandInteraction):
            content += f" | Command: `{interaction.application_command.name}` "
            filled_options = ""
            for filled_option in interaction.filled_options.items():
                filled_options += f"{filled_option[0]} - {repr(filled_option[1])}\n"

            content += f"\n\nOptions: \n{filled_options}\n"

        if isinstance(interaction, MessageInteraction):
            file_path = f'_cache/{"".join(choices(string.ascii_letters + string.digits, k=21)) + ".log"}'
            async with (aiofiles.open(file_path, 'w', encoding="utf-8") as f):
                await f.write("Items: \n")
                for component in interaction.message.components:
                    await f.write(f"{component.type} - {repr(component)}\n")

                await f.write(f"\nSelected item: \n{interaction.component.type} - {repr(interaction.component)}\n")

            files.append(File(file_path))

        data = {'files': files, 'content': content}
        if embed:
            data['embed'] = embed

        await ChisatoBot.from_cache().webhooks.post(data, type='command')
