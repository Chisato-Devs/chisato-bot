import asyncio
import base64
import json
import secrets
from datetime import datetime
from inspect import Traceback
from io import BytesIO
from json import JSONDecodeError
from typing import Final

from aiohttp import ClientSession, ClientConnectorError
from disnake import File

from utils.abstract import AbstractService
from utils.basic import EmbedUI
from utils.basic.chisato import ChisatoBot
from utils.basic.services.draw.cache import Cache
from utils.basic.services.draw.exceptions import DrawBadRequest
from utils.basic.services.draw.types import ContentType
from utils.consts import ERROR_EMOJI
from utils.enviroment import env


class DrawService(AbstractService):
    __cache: Cache = Cache()
    BASE: Final[str] = env.DSU + "/v1"

    def __init__(self, client: ClientSession = None) -> None:
        self._client = client or ClientSession()
        self._loop = asyncio.get_running_loop()
        self._custom_client = True if client else False

    async def __aexit__(self, exc_type: type, exc_val: Exception, exc_tb: Traceback) -> None:
        if not self._custom_client:
            await self._client.close()

    @classmethod
    def __encode_key(cls, **kwargs: any) -> str:
        data = json.dumps(kwargs)
        return base64.b64encode(data.encode()).decode()

    @classmethod
    def _decode_image(
            cls, encode_base64: str, content_type: ContentType
    ) -> File | bytes:
        if content_type == ContentType.FILE:
            buffer = BytesIO(base64.b64decode(encode_base64))
            buffer.seek(0)

            file = File(buffer, f"{secrets.token_hex(6)}.png")

            buffer.close()
            return file
        elif content_type == ContentType.BYTES:
            return base64.b64decode(encode_base64)

    async def draw_image(
            self,
            image_name: str, /,
            content_type: ContentType = ContentType.FILE,
            cache: bool = True,
            **kwargs
    ) -> File | bytes:
        if _selected := self.__cache.get(
                self.__encode_key(image_name=image_name, **kwargs)
        ):
            try:
                return self._decode_image(_selected, content_type=content_type)
            except FileNotFoundError:
                self.__cache.remove(self.__encode_key(image_name=image_name, **kwargs))
                return await self.draw_image(
                    image_name,
                    content_type=content_type,
                    cache=cache,
                    **kwargs
                )
        else:
            async with self._client.get(
                    url=self.BASE + "/draw",
                    params={**kwargs, "name": image_name},
                    timeout=10
            ) as response:
                if response.status != 200:
                    try:
                        response_text = (await response.json()).get("message")
                    except JSONDecodeError:
                        response_text = await response.text(encoding="utf-8")

                    raise DrawBadRequest(response_text)

                _path = (await response.json()).get("encode")
                if cache:
                    self.__cache.put(self.__encode_key(image_name=image_name, **kwargs), _path)
                return self._decode_image(_path, content_type=content_type)

    async def get_stats(self) -> dict[str]:
        async with self._client.get(url=self.BASE + "/stats") as response:
            if response.status != 200:
                raise DrawBadRequest((await response.json()).get("message"))

            return await response.json()

    async def get_status(self) -> bool:
        try:
            async with self._client.get(url=self.BASE + "/status", timeout=0.5):
                pass
        except (ClientConnectorError, TimeoutError):
            bot = ChisatoBot.from_cache()
            if env.MAIN_ID == bot.user.id:
                await bot.webhooks.post(
                    type="command",
                    data={
                        "embed": EmbedUI(
                            title=f"{ERROR_EMOJI} Проблема с API",
                            description=f"> **Причина:** `API не дает ответа.`\n"
                                        f"> **Время:** {datetime.now()} | `{datetime.now().timestamp()}`"
                        )
                    }
                )

            return False
        else:
            return True
