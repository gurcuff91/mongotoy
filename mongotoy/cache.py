import typing
from collections import OrderedDict


class TypesCache:

    def __init__(self):
        self._cache = OrderedDict()

    # noinspection PyMethodMayBeStatic
    def _prepare_key(self, key: typing.Type | str) -> str:
        return key.__name__ if not isinstance(key, str) else key

    def add_type(self, type_: typing.Type | str, value: typing.Type):
        self._cache[self._prepare_key(type_)] = value

    def exist_type(self, type_: typing.Type | str) -> bool:
        return self._prepare_key(type_) in self._cache

    def get_type(self, type_: typing.Type | str) -> typing.Type | None:
        return self._cache.get(self._prepare_key(type_))


# Singleton
documents = TypesCache()
mappers = TypesCache()
