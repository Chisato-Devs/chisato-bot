from http.client import HTTPException

from disnake import MessageInteraction, Embed, ui, Member, ApplicationCommandInteraction, SelectOption, Guild, \
    Interaction, ModalInteraction, Forbidden, NotFound, InteractionResponded, Locale
from disnake.ui import Button, BaseSelect, StringSelect
from disnake.ui import Item, View

from utils.consts import ERROR_EMOJI
from utils.enviroment import env
from utils.exceptions.trace import Trace
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore().load(__file__)


class View(ui.View):
    __slots__ = (
        "_store",
        "__author",
        "__interaction",
        "__guild"
    )

    def __init__(
            self,
            store: ChisatoLocalStore = None,
            author: Member | None = None,
            timeout: int | None = 300,
            guild: Guild = None,
            interaction: MessageInteraction | ApplicationCommandInteraction | ModalInteraction = None,
            exceptions: list[type] = None
    ) -> None:
        self._exceptions = exceptions if exceptions else []
        self._store = store

        self.__author = author
        if not author and interaction:
            self.__author = interaction.author

        self.__interaction = interaction
        self.__guild = guild

        if interaction:
            self._locale = interaction.guild_locale
        elif guild:
            self._locale = guild.preferred_locale
        elif isinstance(author, Member) and author:
            self._locale = author.guild.preferred_locale
        else:
            self._locale = Locale.en_US

        self._timeout = timeout
        self._end = False
        self.end = False

        super().__init__(timeout=timeout)

        if self._store:
            for child in self.children:
                self.localize_item(child)

    async def on_error(self, error: Exception, item: Item, interaction: MessageInteraction) -> None:
        from utils.basic import ChisatoBot

        if ChisatoBot.from_cache().disable_errors:
            return await super().on_error(error, item, interaction)

        if type(error) in self._exceptions:
            return

        await Trace.generate(error, interaction)

    def get_item(self, custom_id: str) -> Button | BaseSelect:
        for child in self.children:
            if child.custom_id == custom_id:  # type: ignore
                return child  # type: ignore

    async def on_timeout(self) -> None:
        if (
                isinstance(self._timeout, int)
                and self.__interaction
                and not (self._end or self.end)
        ):
            try:
                await self.custom_defer(self.__interaction)
            except HTTPException:
                pass
            except Forbidden:
                pass
            except NotFound:
                pass

    async def custom_defer(self, interaction: Interaction) -> any:
        for i in self.children:
            i.disabled = True

        try:
            await interaction.response.edit_message(view=self)
        except InteractionResponded:
            try:
                await interaction.edit_original_response(view=self)
            except Exception as e:
                return e
        except Exception as e:
            return e

    def button_disables(self, custom_ids: list[str], disabled: bool) -> None:
        for child in self.children:
            if child.custom_id in custom_ids:  # type: ignore
                child.disabled = disabled

    @staticmethod
    async def send_error_message(interaction: MessageInteraction) -> None:
        return await interaction.response.send_message(
            embed=Embed(
                description=f"{ERROR_EMOJI} | "
                            f"**{interaction.author.name}**, "
                            f"{_t.get('its_not_your_component', locale=interaction.guild_locale)}!",
                color=env.COLOR
            ),
            ephemeral=True
        )

    async def interaction_check(self, interaction: MessageInteraction) -> bool | None:
        if interaction.component.custom_id in self._exceptions:
            return True

        if (
                (self.__author and self.__author.id != interaction.author.id)
                or (hasattr(self, "author") and getattr(self, "author").id != interaction.author.id)
        ):
            return await self.send_error_message(interaction)
        else:
            return True

    def _localize_select_option(self, option: SelectOption) -> SelectOption:
        if option_label := self._store.get(key=option.label, locale=self._locale):
            option.label = option_label
        if option_description := self._store.get(key=option.description, locale=self._locale):
            option.description = option_description

        return option

    def localize_item(self, item: Item) -> Item:
        if self._store and self._locale:
            if isinstance(item, Button):
                if label := self._store.get(item.label, locale=self._locale):
                    item.label = label
            elif isinstance(item, BaseSelect):
                if placeholder := self._store.get(item.placeholder, locale=self._locale):
                    item.placeholder = placeholder

                if isinstance(item, StringSelect):
                    options = [self._localize_select_option(option) for option in item.options]

                    item.options.clear()
                    item.options.extend(options)

        return item

    def add_item(self, item: Item) -> "View":
        return super().add_item(item=self.localize_item(item))
