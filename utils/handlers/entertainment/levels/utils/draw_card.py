from disnake import MessageInteraction, ApplicationCommandInteraction, Member, File

from utils.basic import IntFormatter, ChisatoBot
from utils.basic.services.draw import DrawService

__all__ = (
    "RankCard",
)


class RankCard:
    bot: ChisatoBot = ChisatoBot.from_cache()

    @classmethod
    async def draw(cls, interaction: MessageInteraction | ApplicationCommandInteraction, member: Member) -> File:
        async with DrawService(cls.bot.session) as ir:
            level_data = await cls.bot.databases.level.get_member_values(interaction.guild.id, member.id)
            file = await ir.draw_image(
                "level_card",
                userName=member.name,
                userAvatar=member.display_avatar.url,
                levelValue=str(level_data[3]),
                prestigeValue=IntFormatter(level_data[2]).to_roman(),
                nowExp=str(level_data[5]),
                needExp=str(level_data[4]),
            )

        return file
