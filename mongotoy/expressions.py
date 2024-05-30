import re
import typing
from typing import Literal

import pymongo

from mongotoy import geodata

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
    def Asc(cls, *fields) -> 'Sort':
        """
        Utility function to create ascending sort expressions.

        Args:
            *fields: Variable number of fields to be sorted in ascending order.

        Returns:
            Sort: Resulting ascending sort expression.
        """
        exp = cls()
        for field in fields:
            exp = exp | cls({str(field): pymongo.ASCENDING})
        return exp

    @classmethod
    def Desc(cls, *fields) -> 'Sort':
        """
        Utility function to create descending sort expressions.

        Args:
            *fields: Variable number of field to be sorted in ascending order.

        Returns:
            Sort: Resulting ascending sort expression.
        """
        exp = cls()
        for field in fields:
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

    @classmethod
    def Intersects(cls, field, value: geodata.Geometry) -> 'Query':
        """
        Creates a geo intersects query expression.

        Selects documents whose geospatial data intersects with a specified GeoJSON object;
        i.e. where the intersection of the data and the specified object is non-empty.

        Args:
            field: The field name.
            value (geodata.Geometry): The geometry.

        Returns:
            Query: The geo intersects query expression.
        """
        return cls({
            str(field): {
                '$geoIntersects': {
                    '$geometry': value.dump_json()
                }
            }
        })

    @classmethod
    def Within(cls, field, value: geodata.Polygon | geodata.MultiPolygon) -> 'Query':
        """
        Creates a geo within query expression.

        Selects documents with geospatial data that exists entirely within a specified shape.

        Args:
            field: The field name.
            value (geodata.Polygon | geodata.MultiPolygon): The polygon or multipolygon geometry.

        Returns:
            Query: The geo within query expression.
        """
        return cls({
            str(field): {
                '$geoWithin': {
                    '$geometry': value.dump_json()
                }
            }
        })

    @classmethod
    def Near(
        cls,
        field,
        value: geodata.Point,
        max_distance: typing.Optional[int] = None,
        min_distance: typing.Optional[int] = None,
        as_near_sphere: bool = False
    ) -> 'Query':
        """
        Creates a geo near query expression.

        Specifies a point for which a geospatial query returns the documents from nearest to farthest

        Args:
            field: The field name.
            value (geodata.Point): The center point geometry.
            max_distance (int, Optional): Max distance (in meters) from the center point.
            min_distance (int, Optional): Min distance (in meters) from the center point.
            as_near_sphere (bool): Calculates distances using spherical geometry.

        Returns:
            Query: The geo near query expression.
        """
        near_op = '$nearSphere' if as_near_sphere else '$near'
        near_exp = {
            '$geometry': value.dump_json()
        }
        if max_distance:
            near_exp['$maxDistance'] = max_distance
        if min_distance:
            near_exp['$minDistance'] = min_distance

        return cls({
            str(field): {
                near_op: near_exp
            }
        })


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
