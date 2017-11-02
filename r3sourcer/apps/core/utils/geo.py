import googlemaps
from datetime import datetime, date, time

from django.conf import settings

# Top-level Status Codes of Google Maps API
INVALID_REQUEST = 'INVALID_REQUEST'
MAX_ELEMENTS_EXCEEDED = 'MAX_ELEMENTS_EXCEEDED'
OVER_QUERY_LIMIT = 'OVER_QUERY_LIMIT'
REQUEST_DENIED = 'REQUEST_DENIED'
UNKNOWN_ERROR = 'UNKNOWN_ERROR'

MODE_DRIVING = 'driving'
MODE_TRANSIT = 'transit'


class GeoException(Exception):
    """
    Class for Google Maps API errors retransmission
    """

    def __init__(self, e):
        self.status = e.status
        self.message = e.message
        self.str = str(e)

    def __str__(self):
        return self.str


def fetch_geo_coord_by_address(address):
    gmaps = googlemaps.Client(key=settings.GOOGLE_GEO_CODING_API_KEY)
    try:
        geocode_result = gmaps.geocode(address)
        if geocode_result:
            return (
                geocode_result[0]['geometry']['location']['lat'],
                geocode_result[0]['geometry']['location']['lng']
            )
    # TODO: Make exception handling type specific and add logging if need
    except Exception as e:
        pass
    return None, None


def calc_distance(origins, destinations, mode=None):
    gmaps = googlemaps.Client(key=settings.GOOGLE_DISTANCE_MATRIX_API_KEY)
    try:
        dm_results = gmaps.distance_matrix(
            origins,
            destinations,
            mode,
            departure_time=int(datetime.combine(date.today(), time(6, 0)).timestamp()) if mode == MODE_TRANSIT else None
        )
        result = []
        for row in dm_results.get('rows', []):
            data_row = []
            for element in row.get('elements', []):
                if element['status'] != 'OK':
                    data_row.append({"distance": None, "duration": None})
                else:
                    data_row.append({"distance": element['distance']['value'],
                                     "duration": element['duration']['value']})
            if len(data_row) == 1:
                result.append(data_row[0])
            else:
                result.append(data_row)
    # TODO: Make exception handling type specific and add logging if need
    except googlemaps.exceptions.ApiError as e_api:
        raise GeoException(e_api)
    except Exception as e:
        if isinstance(e, GeoException):
            raise e
        result = None

    return result
