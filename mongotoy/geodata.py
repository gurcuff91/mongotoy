import typing


class Geometry:

    @property
    def type(self) -> str:
        return self.__class__.__name__

    @property
    def coordinates(self) -> list:
        # noinspection PyTypeChecker
        return list(self)

    def dump_json(self) -> dict:
        """
        Dump the value to valid GeoJSON.

        Returns:
            dict: The dumped value.

        """
        return dict(type=self.type, coordinates=self.coordinates)


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
        if not len(points) >= 4:
            raise TypeError('The LinearRing must be an array of four or more Points')
        isring = points[0] == points[-1]
        if not isring:
            raise TypeError('The first and last positions in LinearRing must be equivalent')
        super().__init__([Point(*i) for i in points])


class Point(Position, Geometry):
    """
    For type "Point", the "coordinates" member is a single position.

    https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.2
    """

    def __init__(self, *coordinates: int | float):
        if len(coordinates) != 2:
            raise TypeError(f'The Point must represent single position, i.e. [lat, long]')
        super().__init__(*coordinates)


class MultiPoint(list[Point], Geometry):
    """
    For type "MultiPoint", the "coordinates" member is an array of
    positions.

    https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.3
    """

    def __init__(self, *points: Point):
        super().__init__([Point(*i) for i in points])


class LineString(list[Point], Geometry):
    """
    For type "LineString", the "coordinates" member is an array of two or
    more positions.

    https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.4
    """

    def __init__(self, *points: Point):
        if not len(points) >= 2:
            raise TypeError('The LineString must be an array of two or more Points')
        super().__init__([Point(*i) for i in points])


class MultiLineString(list[LineString], Geometry):
    """
    For type "MultiLineString", the "coordinates" member is an array of
    LineString coordinate arrays.

    https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.5
    """

    def __init__(self, *lines: LineString):
        super().__init__([LineString(*i) for i in lines])


class Polygon(list[LineString], Geometry):
    """
    https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.6
    """

    def __init__(self, *rings: LineString):
        super().__init__([LinearRing(*i) for i in rings])


class MultiPolygon(list[Polygon], Geometry):
    """
     For type "MultiPolygon", the "coordinates" member is an array of
     Polygon coordinate arrays.

     https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.7
    """

    def __init__(self, *polygons: Polygon):
        super().__init__([Polygon(*i) for i in polygons])
