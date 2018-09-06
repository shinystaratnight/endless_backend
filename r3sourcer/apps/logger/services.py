from django.conf import settings
from django.utils import timezone
from infi.clickhouse_orm.database import Database

from .models import LocationHistory


class LocationLogger():

    def __init__(self):
        self.logger_database = Database(
            settings.LOGGER_DB, db_url="http://{}:{}/".format(settings.LOGGER_HOST, settings.LOGGER_PORT),
            username=settings.LOGGER_USER, password=settings.LOGGER_PASSWORD
        )
        self.logger_database.create_table(LocationHistory)

    def _map_location_log(self, log_instance):
        return {
            'model': log_instance.model,
            'object_id': log_instance.object_id,
            'latitude': log_instance.latitude,
            'longitude': log_instance.longitude,
            'log_at': log_instance.log_at,
        }

    def get_location_queryset(self):
        return LocationHistory.objects_in(self.logger_database)

    def log_instance_location(self, instance, latitude, longitude):
        now = timezone.now()

        log = LocationHistory(
            model=instance._meta.label,
            object_id=str(instance.pk),
            latitude=latitude,
            longitude=longitude,
            log_at=now,
            date=now.date()
        )
        self.logger_database.insert([log])

    def fetch_location_history(self, instance, **kwargs):
        page_num = kwargs.pop('page_num', 1)
        page_size = kwargs.pop('page_size', 10)

        qs = self.get_location_queryset().filter(**kwargs).order_by('-log_at').paginate(
            page_num=page_num, page_size=page_size
        )

        return {
            'results': [self._map_location_log(log) for log in qs.objects],
            'count': qs.number_of_objects,
        }

