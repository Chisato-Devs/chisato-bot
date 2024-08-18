from disnake import Locale


class IntFormatter:
    def __init__(self, _n: int) -> None:
        self._n = _n

    def format_number(self) -> str:
        suffixes = ['', 'k', 'M', 'G', 'T', 'P', 'E']

        num = abs(self._n)
        order = 0
        while num >= 1000 and order < len(suffixes) - 1:
            order += 1
            num /= 1000

        if order == 0:
            formatted_num = str(int(num))
        else:
            formatted_num = '{:.1f}{}'.format(num, suffixes[order])
        return formatted_num

    def to_roman(self) -> str:
        roman_numerals = {
            1000: 'M',
            900: 'CM',
            500: 'D',
            400: 'CD',
            100: 'C',
            90: 'XC',
            50: 'L',
            40: 'XL',
            10: 'X',
            9: 'IX',
            5: 'V',
            4: 'IV',
            1: 'I'
        }

        number = self._n
        result = ""
        for value, numeral in roman_numerals.items():
            count = number // value
            result += numeral * count
            number -= value * count

        return result if result else 0

    def convert_timestamp(self, locale: Locale = Locale.ru) -> str:
        locale = str(locale)
        days = int(self._n // (24 * 3600))
        hours = int((self._n % (24 * 3600)) // 3600)
        minutes = int((self._n % 3600) // 60)

        result = ""
        if days > 0:
            result += f"{days}d "
        if hours > 0:
            result += f"{hours}h "
        if minutes > 0 or (days == 0 and hours == 0):
            result += f"{minutes}m"

        return result
