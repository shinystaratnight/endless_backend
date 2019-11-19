import datetime

from django.core.cache import cache
from django.utils import timezone

from r3sourcer.apps.activity import models as activity_models


class RelatedActivitiesColumnMixin():

    def get_method_fields(self):
        method_fields = list(super().get_method_fields())
        return method_fields + ['actual_activities', 'overdue_activities', 'total_activities']

    def get_related_activities(self, obj):
        if obj is None:
            return None

        cached_key = 'related_activities:{id}'.format(id=obj.id)
        cached_data = cache.get(cached_key, None)
        if not isinstance(cached_data, tuple) or len(cached_data) != 3:
            # TODO: Fix timezone
            now = timezone.now()
            activities = activity_models.Activity.objects.filter(
                entity_object_id=obj.id, entity_object_name=obj.__class__.__name__
            )

            # TODO: uncomment this after add SMS Activity
            # if hasattr(obj, 'contact'):
            #     activities = activities.filter(
            #         models.Q(sms_activities__from_contact_id=obj.contact.id) |
            #         models.Q(sms_activities__to_contact_id=obj.contact.id)
            #     )
            # TODO: Fix timezone
            yesterday = timezone.now() - datetime.timedelta(days=1)
            # TODO: Fix timezone
            tomorrow = timezone.now() + datetime.timedelta(days=1)
            yesterday = yesterday.replace(second=0, minute=0, hour=0)
            tomorrow = tomorrow.replace(second=59, minute=59, hour=23)

            total = activities.count()
            actual = activities.filter(ends_at__gte=yesterday, ends_at__lte=tomorrow).exclude(
                done=activity_models.Activity.STATUS_CHOICES.DONE
            ).count()
            overdue = activities.filter(ends_at__lte=now).exclude(
                done=activity_models.Activity.STATUS_CHOICES.DONE
            ).count()
            cache.set(cached_key, (total, actual, overdue), timeout=60 * 20)
        else:
            total, actual, overdue = cached_data

        return total, actual, overdue

    def get_actual_activities(self, obj):
        res = self.get_related_activities(obj)

        if res and len(res) == 3 and res[0] > 0:
            return res[1]

        return None

    def get_overdue_activities(self, obj):
        res = self.get_related_activities(obj)

        if res and len(res) == 3 and res[0] > 0:
            return res[2]

        return '-'

    def get_total_activities(self, obj):
        res = self.get_related_activities(obj)

        if res and len(res) == 3 and res[0] > 0:
            return res[0]

        return None
