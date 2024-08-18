__all__ = (
    "ConvertTime",
)


class ConvertTime:
    _cache: dict[int, str] = {}

    @classmethod
    def format(cls, _s: int) -> str:
        if _s in cls._cache:
            return cls._cache[_s]
        else:
            seconds = _s // 1000
            minutes = seconds // 60
            seconds = seconds % 60
            cls._cache[_s] = '{:02d}:{:02d}'.format(minutes, seconds)

            return cls._cache[_s]
