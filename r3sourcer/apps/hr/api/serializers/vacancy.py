from django.utils import timezone

from r3sourcer.apps.activity.api import mixins as activity_mixins
from r3sourcer.apps.core.api import serializers as core_serializers, mixins as core_mixins

from r3sourcer.apps.hr import models as hr_models


class VacancySerializer(
    activity_mixins.RelatedActivitiesColumnMixin, core_mixins.WorkflowStatesColumnMixin,
    core_serializers.ApiBaseModelSerializer
):

    method_fields = ('is_fulfilled_today', 'is_fulfilled', 'no_vds', 'can_fillin', 'todays_timesheets', 'title')

    class Meta:
        model = hr_models.Vacancy
        fields = (
            '__all__',
            {
                'jobsite': ['id', {
                    'primary_contact': ['id', {
                        'contact': ['id', 'phone_mobile']
                    }],
                }],
            }
        )

    def get_is_fulfilled_today(self, obj):
        return obj and obj.is_fulfilled_today()

    def get_is_fulfilled(self, obj):
        return obj and obj.is_fulfilled()

    def get_no_vds(self, obj):
        if obj is None:
            return True

        return not obj.vacancy_dates.filter(shift_date__gt=timezone.now().date(), cancelled=False).exists()

    def get_can_fillin(self, obj):
        if obj is None:
            return True

        return obj.can_fillin()

    def get_todays_timesheets(self, obj):
        result = "-"

        if obj is None:
            return result

        today = timezone.now().date()
        timesheets = hr_models.TimeSheet.objects.filter(
            vacancy_offer__shift__date__vacancy_id=obj.id, shift_started_at__date=today
        )
        total_timesheets = timesheets.count()

        if total_timesheets != 0:
            going_to_work_timesheets = timesheets.filter(going_to_work_confirmation=True).count()
            submitted_timesheets = timesheets.filter(candidate_submitted_at__isnull=False).count()
            approved_timesheets = timesheets.filter(supervisor_approved_at__isnull=False).count()
            result = "{}% / {}% / {}%".format(
                int(going_to_work_timesheets * 100 / total_timesheets),
                int(submitted_timesheets * 100 / total_timesheets),
                int(approved_timesheets * 100 / total_timesheets)
            )

        return result

    def get_title(self, obj):
        if obj is None:
            return None

        return obj.get_title()
