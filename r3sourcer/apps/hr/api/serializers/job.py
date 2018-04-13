from datetime import date, datetime
from functools import partial

from django.db.models import Max
from django.conf import settings
from django.utils import timezone, formats
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from r3sourcer.apps.activity.api import mixins as activity_mixins
from r3sourcer.apps.core import models as core_models
from r3sourcer.apps.core.api import serializers as core_serializers, mixins as core_mixins
from r3sourcer.apps.core.utils.user import get_default_user

from r3sourcer.apps.candidate import models as candidate_models
from r3sourcer.apps.hr import models as hr_models
from r3sourcer.apps.hr.utils import utils as hr_utils
from r3sourcer.apps.logger.main import endless_logger


class JobSerializer(core_mixins.WorkflowStatesColumnMixin, core_serializers.ApiBaseModelSerializer):

    method_fields = ('is_fulfilled_today', 'is_fulfilled', 'no_sds', 'hide_fillin', 'title', 'extend')

    class Meta:
        model = hr_models.Job
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

    def get_no_sds(self, obj):  # pragma: no cover
        if obj is None:
            return True

        return not obj.shift_dates.filter(
            shift_date__gt=timezone.localtime(timezone.now()).date(), cancelled=False
        ).exists()

    def get_hide_fillin(self, obj):  # pragma: no cover
        if obj is None:
            return True

        return not obj.can_fillin()

    def get_todays_timesheets(self, obj):
        result = "-"

        if obj is None:  # pragma: no cover
            return result

        today = timezone.localtime(timezone.now()).date()
        timesheets = hr_models.TimeSheet.objects.filter(
            job_offer__shift__date__job_id=obj.id, shift_started_at__date=today
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

    def _get_unfilled_future_vds_queryset(self, obj):
        today = date.today()
        shift_dates = obj.shift_dates.filter(
            shift_date__gte=today, cancelled=False
        ).distinct()
        return shift_dates

    def get_extend(self, obj):  # pragma: no cover
        return obj.has_state(20) and self._get_unfilled_future_vds_queryset(obj).exists()


class JobOfferSerializer(core_serializers.ApiBaseModelSerializer):

    method_fields = (
        'candidate_rate', 'client_rate', 'timesheets', 'has_accept_action', 'has_cancel_action', 'has_resend_action',
        'has_send_action',
    )

    class Meta:
        model = hr_models.JobOffer
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
            candidate_rate = obj.candidate_contact.get_candidate_rate_for_skill(obj.job.position)

        return candidate_rate.hourly_rate if candidate_rate else None

    def get_client_rate(self, obj):
        if not obj:
            return None

        price_list = obj.job.customer_company.get_effective_pricelist_qs(obj.job.position).first()
        if price_list:
            price_list_rate = price_list.price_list_rates.filter(skill=obj.job.position).first()
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
        if obj is None or timezone.now() >= obj.start_time or (obj.is_accepted() and not self.has_late_reply_handling(obj)):
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
        target_date_and_time = timezone.localtime(obj.start_time)
        is_filled = obj.is_quota_filled()
        is_today_or_future = target_date_and_time.date() >= timezone.now().date()

        if (obj.is_cancelled() or not_received_or_scheduled) and not is_filled and is_today_or_future:
            last_jo = obj.job.get_job_offers().filter(
                offer_sent_by_sms__isnull=False,
                candidate_contact=obj.candidate_contact
            ).order_by('offer_sent_by_sms__sent_at').last()
            return bool(
                obj.offer_sent_by_sms and last_jo and
                last_jo.offer_sent_by_sms.sent_at +
                timezone.timedelta(minutes=10) < timezone.now()
            )

        return False

    def get_has_resend_action(self, obj):
        if not obj:
            return None

        return self.is_available_for_resend(obj)

    @classmethod
    def is_available_for_send(cls, obj):
        not_sent_or_scheduled = (
            obj.offer_sent_by_sms is None and not obj.is_accepted() and obj.scheduled_sms_datetime is None
        )
        target_date_and_time = timezone.localtime(obj.start_time)
        is_filled = obj.is_quota_filled()
        is_today_or_future = target_date_and_time.date() >= timezone.now().date()

        return not_sent_or_scheduled and not is_filled and is_today_or_future

    def get_has_send_action(self, obj):
        if not obj:
            return None

        return self.is_available_for_send(obj)


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


class JobFillinSerialzier(core_serializers.ApiBaseModelSerializer):

    method_fields = (
        'available', 'days_from_last_timesheet', 'distance_to_jobsite', 'time_to_jobsite', 'skills_score',
        'count_timesheets', 'hourly_rate', 'evaluation', 'color', 'overpriced',
    )

    jos = serializers.IntegerField(read_only=True)

    class Meta:
        model = candidate_models.CandidateContact
        fields = (
            'id', 'recruitment_agent', 'tag_rels', 'nationality', 'transportation_to_work', 'strength', 'language',
            'jos', {
                'contact': ['gender', 'first_name', 'last_name', {
                    'address': ('longitude', 'latitude'),
                }],
                'candidate_scores': ['reliability', 'average_score'],
                'tag_rels': ['tag'],
            }
        )

    def get_available(self, obj):
        partially_available_candidates = self.context['partially_available_candidates']

        dates = partially_available_candidates.get(obj.id, [])

        date_format = partial(formats.date_format, format=settings.DATETIME_FORMAT)
        return map(date_format, dates)

    def get_days_from_last_timesheet(self, obj):
        last_timesheet = obj.last_timesheet_date
        if last_timesheet:
            today = date.today()
            return (today - timezone.localtime(last_timesheet).date()).days
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
        return hr_models.TimeSheet.objects.filter(job_offer__candidate_contact=obj.id).count()

    def get_hourly_rate(self, obj):
        hourly_rate = obj.get_rate_for_skill(
            self.context['job'].position, score__gt=0, skill__active=True
        )
        return hourly_rate.hourly_rate if hourly_rate else 0

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
            if obj.jos > 0:
                return 2
            return 1
        return 0


class CandidateJobOfferSerializer(core_serializers.ApiBaseModelSerializer):

    jobsite_address = core_serializers.AddressSerializer(read_only=True)

    method_fields = ('jobsite_address', 'hide_buttons', 'status', 'status_icon', 'hide_text', 'latitude', 'longitude')

    class Meta:
        model = hr_models.JobOffer
        fields = [
            '__all__',
            {
                'jobsite_address': ('__all__', ),
                'shift': ['id', 'time', {
                    'date': ['shift_date', {
                        'job': ['position', 'customer_company', {
                            'jobsite': ['primary_contact'],
                        }],
                    }],
                }],
            }
        ]

    def get_jobsite_address(self, obj):
        address = obj.job.jobsite.get_address()
        return address and core_serializers.AddressSerializer(address).data

    def get_hide_buttons(self, obj):
        return obj.status != hr_models.JobOffer.STATUS_CHOICES.undefined

    def get_hide_text(self, obj):
        return not self.get_hide_buttons(obj)

    def get_status(self, obj):
        if obj.status == hr_models.JobOffer.STATUS_CHOICES.undefined:
            return ' '

        last_change = endless_logger.get_recent_field_change(hr_models.JobOffer, obj.id, 'status')
        if not last_change:
            return hr_models.JobOffer.STATUS_CHOICES[obj.status]

        updated_by_id = last_change['updated_by']
        system_user = get_default_user()
        reply_sms = obj.reply_received_by_sms
        jobsite_contact = obj.job.jobsite.primary_contact

        if obj.is_quota_filled() or (reply_sms and reply_sms.is_positive_answer() and not obj.is_accepted()):
            return _('Already filled')

        if obj.is_cancelled():
            if str(obj.candidate_contact.contact.user.id) == updated_by_id:
                return _('Declined by Candidate')
            elif str(system_user.id) == updated_by_id:
                if reply_sms and reply_sms.is_negative_answer():
                    return _('Declined by Candidate')
                else:
                    return _('Cancelled')
            elif jobsite_contact and str(jobsite_contact.contact.user.id) == updated_by_id:
                return _('Cancelled by Job Site Contact')
            else:
                return _('Cancelled by {name}').format(name=core_models.User.objects.get(id=updated_by_id))

        return hr_models.JobOffer.STATUS_CHOICES[obj.status]

    def get_status_icon(self, obj):
        return obj.status == hr_models.JobOffer.STATUS_CHOICES.accepted

    def get_latitude(self, obj):
        address = obj.job.jobsite.get_address()
        return address and address.latitude

    def get_longitude(self, obj):
        address = obj.job.jobsite.get_address()
        return address and address.longitude


class JobsiteSerializer(core_mixins.WorkflowStatesColumnMixin, core_serializers.ApiBaseModelSerializer):

    class Meta:
        model = hr_models.Jobsite
        fields = (
            '__all__',
            {
                'address': (
                    '__all__',
                    {
                        'city': ('id', 'name'),
                        'state': ('id', 'name'),
                    }
                ),
                'master_company': ('id', ),
            }
        )


class JobExtendSerialzier(core_serializers.ApiBaseModelSerializer):

    method_fields = ('job_shift', 'latest_date')

    autofill = serializers.BooleanField(required=False)

    class Meta:
        model = hr_models.Job
        fields = ('id', 'autofill')

    def get_job_shift(self, obj):
        return [
            timezone.make_aware(datetime.combine(shift.date.shift_date, shift.time))
            for shift in hr_models.Shift.objects.filter(date__job=obj)
        ]

    def get_latest_date(self, obj):
        try:
            return obj.shift_dates.filter(cancelled=False).latest('shift_date').id
        except hr_models.ShiftDate.DoesNotExist:
            return None
