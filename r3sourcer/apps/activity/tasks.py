from celery import shared_task
from django.db import transaction
from django.utils import timezone


@shared_task(bind=True, max_retries=0)
def activity_handler(self, repeater_id):
    from .models import ActivityRepeat
    with transaction.atomic():
        activity_repeater = ActivityRepeat.objects.select_for_update(nowait=True).get(id=repeater_id)
        activity_repeater.occur()


@shared_task()
def activity_dates_and_enabled_handler():
    from .models import ActivityDate

    with transaction.atomic():
        activity_dates = ActivityDate.objects.select_for_update().filter(status=ActivityDate.STATUS_CHOICES.WAITING,
                                                                         occur_at__lte=timezone.now(), activity=None)
        for dt in activity_dates.iterator():
            dt.occur()
