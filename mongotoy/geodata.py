import typing


class Geometry:

    def dump_geojson(self) -> dict:
        # noinspection PyTypeChecker
        return dict(type=self.__class__.__name__, coordinates=list(self))


def parse_geojson(geojson: dict, parser: typing.Type[Geometry]) -> Geometry:
    """
    Parse a GeoJSON dictionary using a given geometry parser.

    Args:
        geojson (dict): The GeoJSON dictionary to parse.
        parser (typing.Type): The geometry parser class.

    Returns:
        'Geometry': An instance of the parsed geometry.

    Raises:
        TypeError: If the GeoJSON dictionary is invalid or does not match the expected parser.
    """
    if not geojson.get('type'):
        raise TypeError('Invalid geo-json, type field is required')
    if not geojson.get('coordinates'):
        raise TypeError('Invalid geo-json, coordinates field is required')
    if geojson['type'] != parser.__name__:
        raise TypeError(f'Invalid geo-json type {geojson["type"]}, required is {parser.__name__}')

    # noinspection PyArgumentList
    return parser(*geojson['coordinates'])


class Position(list[int | float]):
    """
    A position is the fundamental geometry construct

    https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.1
    """

    def __init__(self, longitude: int | float, latitude: int | float):
        if not float('-180') < longitude < float('180'):
            raise ValueError(f'The position longitude {longitude} is out of range, '
                             f'valid range is -180 <> 180')
        if not float('-90') < latitude < float('90'):
            raise ValueError(f'The position latitude {latitude} is out of range, '
                             f'valid range is -90 <> 90')
        super().__init__([longitude, latitude])


class LinearRing(list):
    """
    A "LinearRing" is a closed LineString with four or more positions

    https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.6
    """

    def __init__(self, *points):
        from mongotoy.types import Point
        if not len(points) >= 4:
            raise TypeError('The LinearRing must be an array of four or more Points')
        isring = points[0] == points[-1]
        if not isring:
            raise TypeError('The first and last positions in LinearRing must be equivalent')
        super().__init__([Point(*i) for i in points])
