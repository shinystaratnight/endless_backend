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
        return obj and obj.is_fulfilled_today()  # pragma: no cover

    def get_is_fulfilled(self, obj):
        return obj and obj.is_fulfilled()  # pragma: no cover

    def get_no_vds(self, obj):  # pragma: no cover
        if obj is None:
            return True

        return not obj.vacancy_dates.filter(
            shift_date__gt=timezone.localtime(timezone.now()).date(), cancelled=False
        ).exists()

    def get_can_fillin(self, obj):  # pragma: no cover
        if obj is None:
            return True

        return obj.can_fillin()

    def get_todays_timesheets(self, obj):
        result = "-"

        if obj is None:  # pragma: no cover
            return result

        today = timezone.localtime(timezone.now()).date()
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

    def get_title(self, obj):  # pragma: no cover
        if obj is None:
            return None

        return obj.get_title()


class VacancyOfferSerializer(core_serializers.ApiBaseModelSerializer):

    method_fields = ('candidate_rate', 'client_rate', 'timesheets')

    class Meta:
        model = hr_models.VacancyOffer
        fields = [
            '__all__',
            {
                'shift': ['id', 'time', {
                    'date': ['shift_date'],
                }],
            }
        ]

    def get_candidate_rate(self, obj):
        if not obj:
            return None

        if obj.shift.hourly_rate:
            candidate_rate = obj.shift.hourly_rate
        elif obj.shift.date.hourly_rate:
            candidate_rate = obj.shift.date.hourly_rate
        else:
            candidate_rate = obj.candidate_contact.get_candidate_rate_for_skill(obj.vacancy.position)

        return candidate_rate and candidate_rate.hourly_rate

    def get_client_rate(self, obj):
        if not obj:
            return None

        price_list = obj.vacancy.customer_company.get_effective_pricelist_qs(obj.vacancy.position).first()
        if price_list:
            price_list_rate = price_list.price_list_rates.filter(rate__skill=obj.position).first()
            rate = price_list_rate and price_list_rate.hourly_rate
        else:
            rate = None

        return rate

    def get_timesheets(self, obj):  # pragma: no cover
        if obj is None:
            return None

        timesheet = obj.time_sheets.first()
        return timesheet and timesheet.id


class ShiftSerializer(core_serializers.ApiBaseModelSerializer):

    method_fields = ('is_fulfilled',)

    class Meta:
        model = hr_models.Shift
        fields = (
            '__all__', {
                'date': ('__all__', )
            }
        )

    def get_is_fulfilled(self, obj):  # pragma: no cover
        return obj and obj.is_fulfilled()
