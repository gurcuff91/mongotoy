import re
from typing import Literal

import pymongo

EmptyValue = type('EmptyValue', (), {})()
IndexType = Literal[-1, 1, '2d', '2dsphere', 'hashed', 'text']


# noinspection PyPep8Naming
class Sort(dict[str, Literal[-1, 1] | dict]):
    """
    Represents a base object for constructing sort expressions.

    The `|` operator is used to merge expressions and returns a `Sort` object.

    Warning:
        When using this operator, ensure correct bracketing of expressions
        to avoid Python operator precedence issues.
    """

    def __or__(self, other: 'Sort') -> 'Sort':
        """
        Represents the merging of two sort expressions using the logical OR operator (`|`).

        Args:
            other (SortExpression): Another sort expression.

        Returns:
            Sort: Result of merging the two sort expressions.
        """
        if not other:
            return self
        if not self:
            return other
        return Sort({**self, **other})

    def __repr__(self):
        return f'Sort({super().__repr__()})'

    @classmethod
    def Asc(cls, *args) -> 'Sort':
        """
        Utility function to create ascending sort expressions.

        Args:
            *args: Variable number of fields to be sorted in ascending order.

        Returns:
            Sort: Resulting ascending sort expression.
        """
        exp = cls()
        for field in args:
            exp = exp | cls({str(field): pymongo.ASCENDING})
        return exp

    @classmethod
    def Desc(cls, *args) -> 'Sort':
        """
        Utility function to create descending sort expressions.

        Args:
            *args: Variable number of field to be sorted in ascending order.

        Returns:
            Sort: Resulting ascending sort expression.
        """
        exp = cls()
        for field in args:
            exp = exp | cls({str(field): pymongo.DESCENDING})
        return exp


# noinspection PyPep8Naming
class Query(dict[str, list | dict]):
    """
    Represents a base object used to construct query expressions.

    All comparison and logical operators return `Query` objects.

    The `|`, `&`, '~' operators are supported for respectively:
     - [or][Query.__or__]
     - [and][Query.__and__]
     - [not][Query.__invert__]

    Warning:
        When using these operators, ensure correct bracketing of expressions
        to avoid Python operator precedence issues.
    """

    def __and__(self, other: 'Query') -> 'Query':
        """
        Represents the logical AND operation between two query expressions.

        Args:
            other (Query): Another query expression.

        Returns:
            Query: Result of the logical AND operation.
        """
        if not other:
            return self
        if not self:
            return other
        return Query({'$and': [self, other]})

    def __or__(self, other: 'Query') -> 'Query':
        """
        Represents the logical OR operation between two query expressions.

        Args:
            other (Query): Another query expression.

        Returns:
            Query: Result of the logical OR operation.
        """
        if not other:
            return self
        if not self:
            return other
        return Query({'$or': [self, other]})

    def __invert__(self) -> 'Query':
        """
        Represents the logical NOT operation on the query expression.

        Returns:
            Query: Result of the logical NOT operation.
        """
        return Query({'$not': self})

    def __repr__(self):
        return f'Query({super().__repr__()})'

    @classmethod
    def Eq(cls, field, value) -> 'Query':
        """
        Creates an equality query expression.

        Args:
            field: The field.
            value: The value to compare against.

        Returns:
            Query: The equality query expression.
        """
        return cls({str(field): {'$eq': value}})

    @classmethod
    def Ne(cls, field, value) -> 'Query':
        """
        Creates a not-equal query expression.

        Args:
            field: The field.
            value: The value to compare against.

        Returns:
            Query: The not-equal query expression.
        """
        return cls({str(field): {'$ne': value}})

    @classmethod
    def Gt(cls, field, value) -> 'Query':
        """
        Creates a greater-than query expression.

        Args:
            field: The field name.
            value: The value to compare against.

        Returns:
            Query: The greater-than query expression.
        """
        return cls({str(field): {'$gt': value}})

    @classmethod
    def Gte(cls, field, value) -> 'Query':
        """
        Creates a greater-than-or-equal query expression.

        Args:
            field: The field name.
            value: The value to compare against.

        Returns:
            Query: The greater-than-or-equal query expression.
        """
        return cls({str(field): {'$gte': value}})

    @classmethod
    def Lt(cls, field, value) -> 'Query':
        """
        Creates a less-than query expression.

        Args:
            field: The field name.
            value: The value to compare against.

        Returns:
            Query: The less-than query expression.
        """
        return cls({str(field): {'$lt': value}})

    @classmethod
    def Lte(cls, field, value) -> 'Query':
        """
        Creates a less-than-or-equal query expression.

        Args:
            field: The field name.
            value: The value to compare against.

        Returns:
            Query: The less-than-or-equal query expression.
        """
        return cls({str(field): {'$lte': value}})

    @classmethod
    def In(cls, field, value: list) -> 'Query':
        """
        Creates an 'in' query expression.

        Args:
            field: The field name.
            value (list): The list of values.

        Returns:
            Query: The 'in' query expression.
        """
        return cls({str(field): {'$in': value}})

    @classmethod
    def Nin(cls, field, value: list) -> 'Query':
        """
        Creates a 'not in' query expression.

        Args:
            field: The field name.
            value (list): The list of values.

        Returns:
            Query: The 'not in' query expression.
        """
        return cls({str(field): {'$nin': value}})

    @classmethod
    def Regex(cls, field, value: re.Pattern) -> 'Query':
        """
        Creates a regex query expression.

        Args:
            field: The field name.
            value (re.Pattern): The regular expression pattern.

        Returns:
            Query: The regex query expression.
        """
        return cls({str(field): {'$regex': value}})


# noinspection PyPep8Naming
class Join(dict[str, list[str]]):
    """
    Class representing a join condition for database queries.

    This class provides methods to construct join conditions commonly used in database queries.

    Args:
        dict[str, list[str]]: A dictionary representing the join condition.

    """

    @classmethod
    def Eq(cls, left: str, right: str) -> 'Join':
        """
        Constructs a join condition for equality.

        Args:
            left (str): The left side of the join condition.
            right (str): The right side of the join condition.

        Returns:
            Join: An instance of the Join class representing the equality join condition.

        """
        return cls({'$eq': [left, right]})

    @classmethod
    def In(cls, left: str, right: str) -> 'Join':
        """
        Constructs a join condition for membership.

        Args:
            left (str): The left side of the join condition.
            right (str): The right side of the join condition.

        Returns:
            Join: An instance of the Join class representing the membership join condition.

        """
        return cls({'$in': [left, right]})


# noinspection PyPep8Naming
def Q(**kwargs) -> Query:
    """
    Constructor function to create Query expression.

    Args:
        **kwargs: Keyword arguments specifying field names and operator specifications.
    """
    q = Query()
    for key, value in kwargs.items():
        args = key.split('__')

        # Split field and operator i.e. address__street__eq -> address.street eq
        field = '.'.join(args[:-1])
        operator = args[-1:][0]

        # Get operator function
        operator = getattr(Query, operator.lower().capitalize())
        # Concat query expressions
        q = q & operator(field, value)

    return q
