from typing import Callable, TypeVar, TYPE_CHECKING, Union, Optional, List, Sequence, Dict, Any, Coroutine

from disnake import Permissions, Option
from disnake.ext.commands import Cog, slash_command, command, InvokableSlashCommand

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

T = TypeVar("T")
LocalizedRequired = Union[str, "Localized[str]"]
LocalizedOptional = Union[Optional[str], "Localized[Optional[str]]"]
CommandCallback = Callable[[Callable[..., Coroutine[Any, Any, T][Any]]], InvokableSlashCommand]


class CogUI(Cog):
    def __init__(self, bot: "ChisatoBot") -> None:
        self.bot = bot

    @classmethod
    def context_command(cls, *args, **kwargs) -> Callable[[T], T]:
        return command(*args, **kwargs)

    @classmethod
    def slash_command(
            cls,
            name: LocalizedOptional = None,
            description: LocalizedOptional = None,
            dm_permission: Optional[bool] = False,
            default_member_permissions: Optional[Union[Permissions, int]] = None,
            nsfw: Optional[bool] = None,
            options: Optional[List[Option]] = None,
            guild_ids: Optional[Sequence[int]] = None,
            connectors: Optional[Dict[str, str]] = None,
            auto_sync: Optional[bool] = None,
            extras: Optional[Dict[str, Any]] = None,
            **kwargs,
    ) -> Callable[[CommandCallback], InvokableSlashCommand]:
        return slash_command(  # type: ignore
            name=name, description=description, dm_permission=dm_permission,
            default_member_permissions=default_member_permissions, nsfw=nsfw,
            options=options, guild_ids=guild_ids, connectors=connectors,
            auto_sync=auto_sync, extras=extras, **kwargs
        )
