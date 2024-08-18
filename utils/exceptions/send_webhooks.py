import re

import aiohttp
from disnake import Webhook
from loguru import logger

from utils.enviroment import env


class WebhookSender:
    def __init__(self) -> None:
        self._from_type = {
            'command': env.COMMAND_ERROR_WEBHOOK,
            'translation': env.COMMAND_ERROR_WEBHOOK,
            'guild_control': env.GUILD_WEBHOOK,
            'day_statistic': env.DAY_STATISTIC_WEBHOOK,
            'shard_control': env.SHARDS_CONTROL_WEBHOOK
        }
        self._headers = {'Content-Type': 'multipart/form-data'}

    @staticmethod
    def _is_reference(uri: str) -> bool:
        return bool(
            re.compile(r'https?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+').match(uri)
        )

    async def post(self, data: dict, *, type: str) -> bool:
        if not self._is_reference(type):
            try:
                type = self._from_type[type]
            except KeyError:
                logger.error(f'Webhook ({type}) url not found!')
                return False

        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(type, session=session)
            await webhook.send(**data)

        return True
