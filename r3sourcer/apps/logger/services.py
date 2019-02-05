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
        self.logger_database.migrate('r3sourcer.apps.logger.clickhouse_migrations')

    def _map_location_log(self, log_instance):
        return {
            'model': log_instance.model,
            'object_id': log_instance.object_id,
            'latitude': log_instance.latitude,
            'longitude': log_instance.longitude,
            'log_at': log_instance.log_at,
            'timesheet_id': log_instance.timesheet_id,
        }

    def get_location_queryset(self):
        return LocationHistory.objects_in(self.logger_database)

    def log_instance_location(self, instance, latitude, longitude, timesheet_id=None):
        now = timezone.now()

        log = LocationHistory(
            model=instance._meta.label,
            object_id=str(instance.pk),
            timesheet_id=timesheet_id and str(timesheet_id),
            latitude=latitude,
            longitude=longitude,
            log_at=now,
            date=now.date()
        )
        self.logger_database.insert([log])

    def fetch_location_history(self, instance, **kwargs):
        page_num = kwargs.pop('page_num', 1)
        page_size = kwargs.pop('page_size', 10)

        kwargs['object_id'] = str(instance.pk)

        if 'timesheet_id' in kwargs and kwargs.get('timesheet_id') is None:
            del kwargs['timesheet_id']

        qs = self.get_location_queryset().filter(**kwargs).order_by('-log_at').paginate(
            page_num=page_num, page_size=page_size
        )

        return {
            'results': [self._map_location_log(log) for log in qs.objects],
            'count': qs.number_of_objects,
        }

