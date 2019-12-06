from datetime import datetime

import pytz
from celery import shared_task
from django.db import transaction

from r3sourcer.apps.activity.models import ActivityRepeat, ActivityDate


@shared_task(bind=True, max_retries=0)
def activity_handler(self, repeater_id):
    with transaction.atomic():
        activity_repeater = ActivityRepeat.objects.select_for_update(nowait=True).get(id=repeater_id)
        activity_repeater.occur()


@shared_task()
def activity_dates_and_enabled_handler():
    now_utc = datetime.now(pytz.utc)
    with transaction.atomic():
        activity_dates = ActivityDate.objects.select_for_update().filter(status=ActivityDate.STATUS_CHOICES.WAITING,
                                                                         occur_at__lte=now_utc,
                                                                         activity=None)
        for dt in activity_dates.iterator():
            dt.occur()
