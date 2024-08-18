from typing import Callable, TypeVar

from disnake import User
from disnake.ext.commands import check, MissingPermissions
from disnake.ext.commands.context import AnyContext

from utils.exceptions import DoesntHaveAgreedRole

T = TypeVar("T")


class CommandsPermission:

    @classmethod
    def decorator(cls, **perms) -> Callable[[T], T]:
        async def predicate(interaction: AnyContext) -> bool:
            if isinstance(interaction.author, User):
                return True

            if interaction.author is interaction.guild.owner:
                return True

            agreed_roles = []
            if (
                    (
                            not interaction.bot.databases or not  # type: ignore
                    (agreed_roles := await interaction.bot.databases.settings.get_permissions(  # type: ignore
                        interaction.application_command.qualified_name.replace(" ", "."),
                        guild=interaction.guild.id
                    ))
                    ) and perms
            ):
                if not (missing := [
                    perm for perm, value in perms.items()
                    if getattr(interaction.permissions, perm) != value
                ]):
                    return True

                raise MissingPermissions(missing)

            if agreed_roles:
                if [
                    role_id for role_id in agreed_roles
                    if (
                            interaction.guild.get_role(role_id)
                            and interaction.guild.get_role(role_id) in interaction.author.roles
                    )
                ]:
                    return True

                raise DoesntHaveAgreedRole(
                    f"Member {interaction.author.name} "
                    f"on guild {interaction.guild.id} ({interaction.guild.name}), missed roles",
                    required_roles=[
                        interaction.guild.get_role(role_id) for role_id in agreed_roles
                        if interaction.guild.get_role(role_id)
                    ]
                )

            raise Exception("Something went wrong in check roles decorator")

        return check(predicate)
