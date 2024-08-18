import json
import os
from collections import defaultdict
from typing import Union, Optional, Dict, TypeAlias

from disnake import LocalizationProtocol, utils, Locale
from loguru import logger

MT: TypeAlias = str | int | list


class ChisatoLocalStore(LocalizationProtocol):
    def __init__(self) -> None:
        self._loc: Dict[str, Dict[str, str]] = {}
        self._loaded_defaults = False

    def get(
            self, key: str, locale: Optional[str | Locale] = None, values: Optional[tuple] = ()
    ) -> Optional[dict[MT, MT] | list[MT] | MT]:
        if key is None:
            return
        self.load_default()
        data = self._loc.get(key, {})

        if locale:
            locale = str(locale)
            if not (locale := utils.as_valid_locale(locale)):
                logger.warning(f"Invalid locale '{locale}'")
                return

            try:
                return data.get(locale).format(*values) if values else data.get(locale)
            except AttributeError:
                return key
        else:
            if values:
                return {key: value.format(*values) for key, value in data.items()}

            return data

    def load_default(self) -> None:
        if not self._loaded_defaults:
            self._loaded_defaults = True
            for data in self._loc.values():
                for locale in Locale:
                    if str(locale) not in data.keys():
                        try:
                            data[str(locale)] = data["en-US"]
                        except KeyError:
                            pass

    @staticmethod
    def ensure_directory(path: os.PathLike | str) -> None:
        if not os.path.exists(path):
            os.makedirs(path)

    @staticmethod
    def load_json_file(file_path: os.PathLike | str) -> Optional[dict[str, str]]:
        with open(file_path, encoding="utf8", mode='r') as file:
            return json.load(file)

    @staticmethod
    def write_json_file(file_path: os.PathLike | str, data: dict) -> None:
        with open(file_path, encoding="utf8", mode='w') as f:
            json.dump(data, f)

    @classmethod
    def load(cls, path: Optional[str | os.PathLike] = None) -> "ChisatoLocalStore":
        self = cls()

        json_files = ["ru.json", "uk.json", "en_US.json"]
        langs_data = defaultdict()

        if not path:
            for folder in os.listdir("./cogs"):
                if os.path.isdir(f"./cogs/{folder}"):
                    loc_path = f"./cogs/{folder}/locale"

                    cls.ensure_directory(loc_path)
                    for loc_file in json_files:
                        if not os.path.exists(f"{loc_path}/{loc_file}"):
                            cls.write_json_file(f"{loc_path}/{loc_file}", {})

                    for filename in os.listdir(loc_path):
                        if filename.endswith(".json"):
                            langs_data[
                                filename.split(".")[0]
                            ] = cls.load_json_file(f"{loc_path}/{filename}")

            for language, data in langs_data.items():
                self._load_dict(data=data, locale=language.replace("_", "-"))
            return self

        loc_path = str(os.path.dirname(path).replace("\\", "/")) + "/locale"
        for filename in os.listdir(loc_path):
            for loc_file in json_files:
                if not os.path.exists(f"{loc_path}/{loc_file}"):
                    with open(f"{loc_path}/{loc_file}", encoding="utf8", mode='w') as f:
                        json.dump({}, f)

            if filename.endswith('.json'):
                self._load_file(f"{loc_path}/{filename}")

        return self

    def _load_file(self, file_path: Union[str, os.PathLike]) -> None:
        locale = file_path.split('/')[-1].split('.')[0]
        if not (locale := utils.as_valid_locale(locale)):
            raise ValueError(f"invalid locale '{file_path}'")

        with open(file_path, encoding="utf8", mode='r') as file:
            json_data = json.load(file)

        self._load_dict(json_data, locale.replace("_", "-"))

    def _load_dict(self, data: Dict[str, str], locale: str) -> None:
        for key, value in data.items():
            if self._loc.get(key):
                self._loc[key].update({locale: value})
            else:
                self._loc[key] = {locale: value}
