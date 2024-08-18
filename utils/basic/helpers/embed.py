from __future__ import annotations

import re

from disnake import Embed, Colour, Member, Localized

from utils.enviroment import env


class EmbedUI(Embed):
    def __init__(
            self, title: Localized | str = None, description: Localized | str = None,
            color: int | Colour = env.COLOR, *args, **kwargs
    ) -> None:
        super().__init__(
            title=title,
            description=description,
            color=color,
            *args,
            **kwargs
        )

    @classmethod
    def from_dict_with_attrs(cls, embed_data: dict, attrs: dict) -> EmbedUI:
        return cls.from_dict(embed_data).set_attrs(attrs)

    def set_attrs(self, attrs: dict) -> EmbedUI:
        pattern = r"\+(\w+)\+"

        def custom_replace(match: re.Match):
            return attrs.get(match.group(1), match.group(0))

        def replace_in_structure(structure: dict | list | str | int):
            if isinstance(structure, dict):
                return {key: replace_in_structure(value) for key, value in structure.items()}
            elif isinstance(structure, list):
                return [replace_in_structure(item) for item in structure]
            elif isinstance(structure, str):
                return re.sub(pattern, custom_replace, structure, count=20)
            else:
                return structure

        return self.from_dict(replace_in_structure(super().to_dict()))


class EmbedErrorUI(Embed):
    def __init__(self, description: str | Localized, member: Member) -> None:
        super().__init__(
            description=f"<:RemoveCircle:1113824544709414984> | **{member.display_name}**, " + str(description),
            color=0x2b2d31
        )
