import re
from typing import Literal

import pymongo


class QueryExpression(dict[str, list | dict]):
    """
    Represents a base object used to construct query expressions.

    All comparison and logical operators return `QueryExpression` objects.

    The `|`, `&`, '~' operators are supported for respectively:
     - [or][QueryExpression.__or__]
     - [and][QueryExpression.__and__]
     - [not][QueryExpression.__invert__]

    Warning:
        When using these operators, ensure correct bracketing of expressions
        to avoid Python operator precedence issues.
    """

    def __and__(self, other: 'QueryExpression') -> 'QueryExpression':
        """
        Represents the logical AND operation between two query expressions.

        Args:
            other (QueryExpression): Another query expression.

        Returns:
            QueryExpression: Result of the logical AND operation.
        """
        if not other:
            return self
        if not self:
            return other
        return QueryExpression({'$and': [self, other]})

    def __or__(self, other: 'QueryExpression') -> 'QueryExpression':
        """
        Represents the logical OR operation between two query expressions.

        Args:
            other (QueryExpression): Another query expression.

        Returns:
            QueryExpression: Result of the logical OR operation.
        """
        if not other:
            return self
        if not self:
            return other
        return QueryExpression({'$or': [self, other]})

    def __invert__(self) -> 'QueryExpression':
        """
        Represents the logical NOT operation on the query expression.

        Returns:
            QueryExpression: Result of the logical NOT operation.
        """
        return QueryExpression({'$not': self})


class SortExpression(dict[str, Literal[-1, 1] | dict]):
    """
    Represents a base object for constructing sort expressions.

    The `|` operator is used to merge expressions and returns a `SortExpression` object.

    Warning:
        When using this operator, ensure correct bracketing of expressions
        to avoid Python operator precedence issues.
    """

    def __or__(self, other: 'SortExpression') -> 'SortExpression':
        """
        Represents the merging of two sort expressions using the logical OR operator (`|`).

        Args:
            other (SortExpression): Another sort expression.

        Returns:
            SortExpression: Result of merging the two sort expressions.
        """
        if not other:
            return self
        if not self:
            return other
        return SortExpression({**self, **other})


def Asc(*fields: str) -> SortExpression:
    """
    Utility function to create ascending sort expressions.

    Args:
        *fields (str): Variable number of field names to be sorted in ascending order.

    Returns:
        SortExpression: Resulting ascending sort expression.
    """
    sort_expression = SortExpression()
    for field in fields:
        sort_expression = sort_expression | SortExpression({str(field): pymongo.ASCENDING})
    return sort_expression


def Desc(*fields: str) -> SortExpression:
    """
    Utility function to create descending sort expressions.

    Args:
        *fields (str): Variable number of field names to be sorted in descending order.

    Returns:
        SortExpression: Resulting descending sort expression.
    """
    sort_expression = SortExpression()
    for field in fields:
        sort_expression = sort_expression | SortExpression({str(field): pymongo.DESCENDING})
    return sort_expression


class Q:
    """
    Query builder class.

    This class provides utility methods for constructing complex query expressions using MongoDB operators.
    It allows users to specify conditions on fields and combine them using logical operators.

    Example:
        ```python
        query = (Q(name__eq='John') & Q(age__gt=25)) | Q(department__in=['Engineering', 'Marketing'])
        ```

        In this example, the resulting query would match documents where the 'name' is 'John',
        'age' is greater than 25, or 'department' is either 'Engineering' or 'Marketing'.
        
    Warning:
        When combining multiple conditions, ensure correct usage of brackets to avoid Python
        operator precedence issues.
    """

    @classmethod
    def _eq(cls, key: str, value) -> QueryExpression:
        """
        Creates an equality query expression.

        Args:
            key (str): The field name.
            value: The value to compare against.

        Returns:
            QueryExpression: The equality query expression.
        """
        return QueryExpression({key: {'$eq': value}})

    @classmethod
    def _ne(cls, key: str, value) -> QueryExpression:
        """
        Creates a not-equal query expression.

        Args:
            key (str): The field name.
            value: The value to compare against.

        Returns:
            QueryExpression: The not-equal query expression.
        """
        return QueryExpression({key: {'$ne': value}})

    @classmethod
    def _gt(cls, key: str, value) -> QueryExpression:
        """
        Creates a greater-than query expression.

        Args:
            key (str): The field name.
            value: The value to compare against.

        Returns:
            QueryExpression: The greater-than query expression.
        """
        return QueryExpression({key: {'$gt': value}})

    @classmethod
    def _gte(cls, key: str, value) -> QueryExpression:
        """
        Creates a greater-than-or-equal query expression.

        Args:
            key (str): The field name.
            value: The value to compare against.

        Returns:
            QueryExpression: The greater-than-or-equal query expression.
        """
        return QueryExpression({key: {'$gte': value}})

    @classmethod
    def _lt(cls, key: str, value) -> QueryExpression:
        """
        Creates a less-than query expression.

        Args:
            key (str): The field name.
            value: The value to compare against.

        Returns:
            QueryExpression: The less-than query expression.
        """
        return QueryExpression({key: {'$lt': value}})

    @classmethod
    def _lte(cls, key: str, value) -> QueryExpression:
        """
        Creates a less-than-or-equal query expression.

        Args:
            key (str): The field name.
            value: The value to compare against.

        Returns:
            QueryExpression: The less-than-or-equal query expression.
        """
        return QueryExpression({key: {'lte': value}})

    @classmethod
    def _in(cls, key: str, value: list) -> QueryExpression:
        """
        Creates an 'in' query expression.

        Args:
            key (str): The field name.
            value (list): The list of values.

        Returns:
            QueryExpression: The 'in' query expression.
        """
        return QueryExpression({key: {'$in': value}})

    @classmethod
    def _nin(cls, key: str, value: list) -> QueryExpression:
        """
        Creates a 'not in' query expression.

        Args:
            key (str): The field name.
            value (list): The list of values.

        Returns:
            QueryExpression: The 'not in' query expression.
        """
        return QueryExpression({key: {'$nin': value}})

    @classmethod
    def _match(cls, key: str, value: re.Pattern) -> QueryExpression:
        """
        Creates a regex query expression.

        Args:
            key (str): The field name.
            value (re.Pattern): The regular expression pattern.

        Returns:
            QueryExpression: The regex query expression.
        """
        return QueryExpression({key: {'$regex': value}})
    
    def __init__(self, **kwargs):
        """
        Constructor function to create Query expression.

        Args:
            **kwargs: Keyword arguments specifying field names and operator specifications.
        """
        # Base query expression
        q = QueryExpression()
        
        for key, val in kwargs.items():
            args = key.split('__')
            
            # Split field and operator i.e. address__street__eq -> address.street eq
            field = '.'.join(args[:-1])
            operator = args[-1:][0]
            
            # Get operator function
            operator = getattr(self.__class__, f'_{operator}')
            # Concat query expressions
            q = q & operator(field, val)

        return q

