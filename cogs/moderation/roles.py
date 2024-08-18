from typing import TYPE_CHECKING

from disnake import Forbidden, Localized
from disnake import MessageCommandInteraction, Member, Role, HTTPException
from disnake.ext.commands import Param

from utils.basic import EmbedErrorUI, EmbedUI, CogUI, CommandsPermission
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

_t = ChisatoLocalStore.load(__file__)


class RolesCog(CogUI):

    @CogUI.slash_command(name="role")
    async def __role(self, interaction: MessageCommandInteraction) -> None:
        pass

    @__role.sub_command(
        name="add", description=Localized(
            "🔼 Добавить роль: назначение роли пользователю.",
            data=_t.get("roles.command.add.description")
        )
    )
    @CommandsPermission.decorator(manage_roles=True)
    async def role_add(
            self,
            interaction: MessageCommandInteraction,
            member: Member = Param(
                name=Localized("пользователь", data=_t.get("roles.command.add.option.member.name")),
                description=Localized(
                    "- укажи пользователя, которому хочешь добавить роль.",
                    data=_t.get("roles.command.add.option.member.description")
                ),
                default=lambda x: x.author
            ),
            role: Role = Param(
                name=Localized("роль", data=_t.get("roles.command.add.option.role.name")),
                description=Localized(
                    "- укажи роль, которую хочешь добавить пользователю.",
                    data=_t.get("roles.command.add.option.role.description")
                )
            ),
            reason: str = Param(
                name=Localized("причина", data=_t.get("roles.command.add.option.reason.name")),
                description=Localized(
                    "- укажи причину добавления роли.", data=_t.get("roles.command.add.option.reason.description")
                ),
                default="None"
            )
    ) -> None:
        if reason == "None":
            reason = _t.get("roles.command.add.option.reason.default", locale=interaction.guild_locale)
        if interaction.author.top_role.position <= role.position:
            embed: EmbedErrorUI = EmbedErrorUI(
                _t.get("roles.add.error.cant_give_it", locale=interaction.guild_locale), interaction.author
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif role in member.roles:
            embed: EmbedErrorUI = EmbedErrorUI(
                _t.get("roles.add.error.already_have_it", locale=interaction.guild_locale), interaction.author
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif member.bot:
            embed: EmbedErrorUI = EmbedErrorUI(
                _t.get("roles.add.error.not_bot", locale=interaction.guild_locale), interaction.author
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        else:
            try:
                await member.add_roles(role)
            except Forbidden:
                embed: EmbedErrorUI = EmbedErrorUI(
                    _t.get("roles.add.error.forbidden", locale=interaction.guild_locale), interaction.author
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except HTTPException:
                embed: EmbedErrorUI = EmbedErrorUI(
                    _t.get("roles.add.error.http", locale=interaction.guild_locale), interaction.author
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                embed: EmbedUI = EmbedUI(
                    title=_t.get("roles.title", locale=interaction.guild_locale),
                    description=_t.get(
                        "roles.add.success", locale=interaction.guild_locale,
                        values=(
                            interaction.author.mention, interaction.author, member.mention,
                            member, role.mention, role.name, reason
                        )
                    )
                )

                await interaction.response.send_message(embed=embed)

    @__role.sub_command(
        name="remove", description=Localized(
            "🔽 Удалить роль: снятие роли с пользователя.",
            data=_t.get("roles.remove.description")
        )
    )
    @CommandsPermission.decorator(manage_roles=True)
    async def role_remove(
            self,
            interaction: MessageCommandInteraction,
            member: Member = Param(
                name=Localized("пользователь", data=_t.get("roles.remove.option.member.name")),
                description=Localized(
                    "- укажи пользователя, у которого хочешь удалить роль.",
                    data=_t.get("roles.remove.option.member.description")
                ),
                default=lambda x: x.author
            ),
            role: Role = Param(
                name=Localized("роль", data=_t.get("roles.remove.option.role.name")),
                description=Localized(
                    "- укажи роль, которую хочешь удалить у пользователя.",
                    data=_t.get("roles.remove.option.role.description")
                )
            ),
            reason: str = Param(
                name=Localized("причина", data=_t.get("roles.remove.option.reason.name")),
                description=Localized(
                    "- укажи причину удаления роли.", data=_t.get("roles.remove.option.reason.description")
                ),
                default="None"
            )
    ) -> None:
        if reason == "None":
            reason = _t.get("roles.remove.option.reason.default", locale=interaction.guild_locale)
        if interaction.author.top_role.position <= role.position:
            embed: EmbedErrorUI = EmbedErrorUI(
                _t.get("role.remove.error.cant_take_off_it", locale=interaction.guild_locale),
                interaction.author
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif role not in member.roles:
            embed: EmbedErrorUI = EmbedErrorUI(
                _t.get("role.remove.error.doesnt_have_it", locale=interaction.guild_locale), interaction.author
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif member.bot:
            embed: EmbedErrorUI = EmbedErrorUI(
                _t.get("role.remove.error.not_bot", locale=interaction.guild_locale), interaction.author
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        else:
            try:
                await member.remove_roles(role)
            except Forbidden:
                embed: EmbedErrorUI = EmbedErrorUI(
                    _t.get("role.remove.error.forbidden", locale=interaction.guild_locale), interaction.author
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except HTTPException:
                embed: EmbedErrorUI = EmbedErrorUI(
                    _t.get("role.remove.error.http", locale=interaction.guild_locale), interaction.author
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                embed: EmbedUI = EmbedUI(
                    title=_t.get("roles.title", locale=interaction.guild_locale),
                    description=_t.get(
                        "role.remove.success.removed", locale=interaction.guild_locale,
                        values=(
                            interaction.author.mention, interaction.author, member.mention,
                            member.name, role.mention, role.name, reason
                        )
                    )
                )

                await interaction.response.send_message(embed=embed)


def setup(bot: "ChisatoBot") -> None:
    bot.add_cog(RolesCog(bot))
