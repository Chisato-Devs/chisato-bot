from dataclasses import dataclass

__all__ = (
    "CardItem"
)


@dataclass
class CardItem:
    uid: int | None
    card_id: int
    owner: int | None
    name_key: str
    description_key: str
    male_key: str
    image_key: str
    rarity: str
    stars_count: int
    created_timestamp: int | None
