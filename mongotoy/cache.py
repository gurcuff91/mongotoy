import typing
from collections import OrderedDict


class TypeCache:
    """
    Cache class for storing and retrieving types.

    Attributes:
        _cache (OrderedDict): A dictionary to store types.
    """

    def __init__(self):
        """
        Initialize a TypesCache object with an empty cache.
        """
        self._cache = OrderedDict()

    # noinspection PyMethodMayBeStatic
    def _prepare_key(self, key: typing.Type | str) -> str:
        """
        Prepare the key for storage in the cache.

        Args:
            key (typing.Type | str): The type or string key.

        Returns:
            str: The prepared key.
        """
        return key.__name__ if not isinstance(key, str) else key

    def add_type(self, type_: typing.Type | str, value: typing.Type):
        """
        Add a type to the cache.

        Args:
            type_ (typing.Type | str): The type or string key.
            value (typing.Type): The value to be stored.

        """
        if self.exist_type(type_):
            raise TypeError(f'Type `{type_}` already declared')
        self._cache[self._prepare_key(type_)] = value

    def exist_type(self, type_: typing.Type | str) -> bool:
        """
        Check if a type exists in the cache.

        Args:
            type_ (typing.Type | str): The type or string key.

        Returns:
            bool: True if the type exists in the cache, False otherwise.
        """
        return self._prepare_key(type_) in self._cache

    def get_type(self, type_: typing.Type | str, do_raise: bool = False) -> typing.Type | None:
        """
        Retrieve a type from the cache.

        Args:
            type_ (typing.Type | str): The type or string key.
            do_raise (bool): Raise TypeError is type does not exist

        Returns:
            typing.Type | None: The retrieved type if found, None otherwise.
        """
        res = self._cache.get(self._prepare_key(type_))
        if not res and do_raise:
            raise TypeError(f'Type `{type_}` not declared yet')
        return res

    def get_all_types(self) -> list[typing.Type]:
        # noinspection PyTypeChecker
        return self._cache.values()


# Singleton instances
documents = TypeCache()
mappers = TypeCache()
