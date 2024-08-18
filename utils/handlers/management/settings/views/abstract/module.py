from disnake import SelectOption, MessageInteraction


class SettingModule:
    option: SelectOption
    main_module: bool = False

    async def main_callback(self, interaction: MessageInteraction) -> None: ...
