from datetime import date

from django.db.models import Max
from django.utils import timezone
from rest_framework import serializers

from r3sourcer.apps.activity.api import mixins as activity_mixins
from r3sourcer.apps.core.api import serializers as core_serializers, mixins as core_mixins

from r3sourcer.apps.candidate import models as candidate_models
from r3sourcer.apps.hr import models as hr_models
from r3sourcer.apps.hr.utils import utils as hr_utils


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
                'hourly_rate_default': ['id', 'hourly_rate'],
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

    method_fields = (
        'candidate_rate', 'client_rate', 'timesheets', 'has_accept_action', 'has_cancel_action', 'has_resend_action'
    )

    class Meta:
        model = hr_models.VacancyOffer
        fields = [
            '__all__',
            {
                'offer_sent_by_sms': ['id'],
                'reply_received_by_sms': ['id'],
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

        return candidate_rate.hourly_rate if candidate_rate else None

    def get_client_rate(self, obj):
        if not obj:
            return None

        price_list = obj.vacancy.customer_company.get_effective_pricelist_qs(obj.vacancy.position).first()
        if price_list:
            price_list_rate = price_list.price_list_rates.filter(skill=obj.vacancy.position).first()
            rate = price_list_rate and price_list_rate.hourly_rate
        else:
            rate = None

        return rate

    def get_timesheets(self, obj):  # pragma: no cover
        if obj is None:
            return None

        timesheet = obj.time_sheets.first()
        return timesheet and timesheet.id

    def has_late_reply_handling(self, obj):
        return (
            obj.offer_sent_by_sms and not obj.reply_received_by_sms and obj.offer_sent_by_sms.late_reply and
            not obj.accepted
        )

    def get_has_accept_action(self, obj):
        if obj is None or obj.is_cancelled() or (obj.is_accepted() and not self.has_late_reply_handling(obj)):
            return None

        return True

    def get_has_cancel_action(self, obj):
        if obj is None or obj.is_cancelled():
            return None

        return True

    @classmethod
    def is_available_for_resend(cls, obj):
        not_received_or_scheduled = (
            obj.reply_received_by_sms is None and not obj.is_accepted() and obj.scheduled_sms_datetime is None
        )

        if obj.is_cancelled() or not_received_or_scheduled:
            last_vo = obj.vacancy.get_vacancy_offers().filter(
                offer_sent_by_sms__isnull=False,
                candidate_contact=obj.candidate_contact
            ).order_by('offer_sent_by_sms__sent_at').last()
            return bool(
                obj.offer_sent_by_sms and last_vo and
                last_vo.offer_sent_by_sms.sent_at +
                timezone.timedelta(minutes=10) < timezone.now()
            )

        return False

    def get_has_resend_action(self, obj):
        if not obj:
            return None

        return self.is_available_for_resend(obj)


class ShiftSerializer(core_serializers.ApiBaseModelSerializer):

    method_fields = ('is_fulfilled',)

    class Meta:
        model = hr_models.Shift
        fields = (
            '__all__', {
                'hourly_rate': ('id', 'hourly_rate'),
                'date': ('__all__', )
            }
        )

    def get_is_fulfilled(self, obj):  # pragma: no cover
        return obj and obj.is_fulfilled()


class VacancyFillinSerialzier(core_serializers.ApiBaseModelSerializer):

    method_fields = (
        'available', 'days_from_last_timesheet', 'distance_to_jobsite', 'time_to_jobsite', 'skills_score',
        'count_timesheets', 'hourly_rate', 'average_score', 'evaluation', 'color', 'overpriced',
    )

    vos = serializers.IntegerField(read_only=True)

    class Meta:
        model = candidate_models.CandidateContact
        fields = (
            'id', 'recruitment_agent', 'tag_rels', 'nationality', 'transportation_to_work', 'strength', 'language',
            'vos', {
                'contact': ['gender', 'first_name', 'last_name', {
                    'address': ('longitude', 'latitude'),
                }],
                'candidate_scores': ['reliability'],
                'tag_rels': ['tag'],
            }
        )

    def get_available(self, obj):
        partially_available_candidates = self.context['partially_available_candidates']

        dates = partially_available_candidates.get(obj.id, [])

        return dates

    def get_days_from_last_timesheet(self, obj):
        last_timesheet = hr_models.TimeSheet.objects.filter(
            vacancy_offer__candidate_contact=obj.id
        ).order_by('-shift_started_at').first()
        if last_timesheet:
            today = date.today()
            if last_timesheet.shift_started_at:
                return (today - timezone.localtime(last_timesheet.shift_started_at).date()).days
            else:
                return 0
        else:
            return 0

    def get_distance_to_jobsite(self, obj):
        return hr_utils.meters_to_km(obj.distance_to_jobsite) if obj.distance_to_jobsite > -1 else -1

    def get_time_to_jobsite(self, obj):
        return hr_utils.seconds_to_hrs(obj.time_to_jobsite) if obj.time_to_jobsite and obj.time_to_jobsite > 0 else -1

    def get_skills_score(self, obj):
        max_score = obj.candidate_skills.filter(
            score__gt=0, skill__active=True
        ).aggregate(Max('score'))["score__max"]
        return max_score or 0

    def get_count_timesheets(self, obj):
        return hr_models.TimeSheet.objects.filter(vacancy_offer__candidate_contact=obj.id).count()

    def get_hourly_rate(self, obj):
        hourly_rate = obj.get_rate_for_skill(
            self.context['vacancy'].position, score__gt=0, skill__active=True
        )
        return hourly_rate.hourly_rate if hourly_rate else 0

    def get_average_score(self, obj):
        return obj.candidate_scores.get_average_score()

    def get_evaluation(self, obj):
        return '{} ({})'.format(obj.total_evaluation_average(), obj.candidate_evaluations.count())

    def get_is_favourite(self, obj):
        return obj.id in self.context['favourite_list']

    def get_overpriced(self, obj):
        return obj.id in self.context['overpriced']

    def get_color(self, obj):
        is_partially_avail = obj.id in self.context['partially_available_candidates']
        if self.get_overpriced(obj):
            if is_partially_avail:
                return 5
            return 3
        elif is_partially_avail:
            return 4
        elif obj.id in self.context['carrier_list'] or obj.id in self.context['booked_before_list']:
            if obj.vos > 0:
                return 2
            return 1
        return 0
