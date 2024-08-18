from dataclasses import dataclass


@dataclass(kw_only=True)
class Pet:
    name: str
    emoji: str
    power: int
    stamina: int
    mana: int
    cost: int
    image_link: str
    level: int
    exp_need: int = 20
    exp_now: int = 0
    owner_id: int = 0
    guild_id: int = 0
