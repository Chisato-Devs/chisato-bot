from dataclasses import dataclass


@dataclass(kw_only=True)
class Work:
    name: str
    initial_payment: int
    final_payment: int
    initial_premium: int
    final_premium: int
    need_works_count: int
