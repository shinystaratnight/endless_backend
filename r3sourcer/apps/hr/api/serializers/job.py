from datetime import date, datetime, timedelta

from django.db.models import Max, Q
from django.conf import settings
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers, exceptions

from r3sourcer.apps.core import models as core_models
from r3sourcer.apps.core.api import serializers as core_serializers, mixins as core_mixins
from r3sourcer.apps.core.utils.user import get_default_user

from r3sourcer.apps.candidate import models as candidate_models
from r3sourcer.apps.hr import models as hr_models
from r3sourcer.apps.hr.utils import utils as hr_utils, job as hr_job_utils
from r3sourcer.apps.logger.main import endless_logger


class JobSerializer(core_mixins.WorkflowStatesColumnMixin, core_serializers.ApiBaseModelSerializer):

    method_fields = ('is_fulfilled_today', 'is_fulfilled', 'no_sds', 'hide_fillin', 'title', 'extend', 'tags')

    class Meta:
        model = hr_models.Job
        fields = (
            '__all__',
            {
                'jobsite': ['id', {
                    'primary_contact': ['id', {
                        'contact': ['id', 'phone_mobile']
                    }],
                }],
                'position': ['id', 'name', 'upper_rate_limit', 'lower_rate_limit', 'default_rate'],
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
        current_state = obj.get_current_state()

        return current_state and current_state.number == 20

    def validate(self, validated_data):
        hourly_rate_default = validated_data.get('hourly_rate_default')

        if hourly_rate_default:
            skill = validated_data.get('position')
            is_less_than_min = skill.lower_rate_limit and skill.lower_rate_limit > hourly_rate_default
            is_more_than_max = skill.upper_rate_limit and skill.upper_rate_limit < hourly_rate_default

            if is_less_than_min or is_more_than_max:
                if is_less_than_min and is_more_than_max:
                    error_part = _('between {lower} and {upper}')
                elif is_less_than_min:
                    error_part = _('more than or equal {lower}')
                else:
                    error_part = _('less than or equal {upper}')

                error_part = error_part.format(
                    lower=skill.lower_rate_limit, upper=skill.upper_rate_limit
                )

                raise exceptions.ValidationError({
                    'hourly_rate_default': _('Hourly rate should be {error_part}').format(error_part=error_part)
                })

        return validated_data

    def get_tags(self, obj):
        tags = core_models.Tag.objects.filter(job_tags__job=obj).distinct()
        return core_serializers.TagSerializer(tags, many=True, read_only=True, fields=['id', 'name']).data


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
            candidate_rate = obj.shift.hourly_rate.hourly_rate
        elif obj.shift.date.hourly_rate:
            candidate_rate = obj.shift.date.hourly_rate.hourly_rate
        else:
            candidate_rate = obj.candidate_contact.get_candidate_rate_for_skill(obj.job.position)

        return candidate_rate

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
        if obj is None or (obj.is_accepted() and not self.has_late_reply_handling(obj)):
            return None

        if obj.is_accepted() or obj.shift.is_fulfilled() == hr_models.FULFILLED:
            return None

        return True

    def get_has_cancel_action(self, obj):
        if obj is None or obj.is_cancelled():
            return None

        return True

    @classmethod
    def is_available_for_resend(cls, obj):
        not_received_or_scheduled = obj.reply_received_by_sms is None and not obj.is_accepted()
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
                last_jo.offer_sent_by_sms.sent_at < timezone.now()
            )

        return False

    def get_has_resend_action(self, obj):
        if not obj:
            return None

        return self.is_available_for_resend(obj)

    @classmethod
    def is_available_for_send(cls, obj):
        not_sent = obj.offer_sent_by_sms is None and not obj.is_accepted()
        target_date_and_time = timezone.localtime(obj.start_time)
        is_filled = obj.is_quota_filled()
        is_today_or_future = target_date_and_time.date() >= timezone.now().date()

        return not_sent and not is_filled and is_today_or_future

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
        'count_timesheets', 'hourly_rate', 'evaluation', 'color', 'overpriced', 'favourite', 'tags',
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
                'candidate_scores': ['reliability', 'average_score', 'loyalty', 'recruitment_score'],
                'tag_rels': ['tag'],
            }
        )

    def _get_jo_messages(self, obj, date):
        from_date = date - timedelta(hours=settings.VACANCY_FILLING_TIME_DELTA)
        to_date = date + timedelta(hours=settings.VACANCY_FILLING_TIME_DELTA)
        job_offers = obj.job_offers.filter(
            Q(shift__date__shift_date=from_date.date(),
                shift__time__gte=from_date.timetz()) |
            Q(shift__date__shift_date__gt=from_date.date()),
            Q(shift__date__shift_date=to_date.date(),
                shift__time__lte=to_date.timetz()) |
            Q(shift__date__shift_date__lt=to_date.date())
        )

        accepted_messages = []
        not_accepted_messages = []

        for jo in job_offers.all():
            message = {
                'message': str(jo.shift.date.job.jobsite),
                'job': jo.shift.date.job.id,
            }
            if jo.status == hr_models.JobOffer.STATUS_CHOICES.accepted:
                message['status'] = _('Accepted')
                accepted_messages.append(message)
            elif jo.status == hr_models.JobOffer.STATUS_CHOICES.cancelled:
                message['status'] = _('Rejected')
                not_accepted_messages.append(message)
            else:
                message['status'] = _('Pending')
                not_accepted_messages.append(message)

        return accepted_messages, not_accepted_messages

    def get_available(self, obj):
        shifts_data = self.context['partially_available_candidates'].get(obj.id, {})
        init_shifts = self.context['init_shifts']

        response_data = []
        text = _('All shifts')

        if len(shifts_data) > 0:
            dates = []

            for shift in shifts_data['shifts']:
                data = {
                    'datetime': timezone.make_aware(datetime.combine(shift.date.shift_date, shift.time)),
                }

                accepted_messages, not_accepted_messages = self._get_jo_messages(obj, data['datetime'])

                if hr_job_utils.HAS_JOBOFFER in shifts_data['reasons'] and len(accepted_messages) > 0:
                    data['messages'] = accepted_messages
                elif hr_job_utils.UNAVAILABLE in shifts_data['reasons']:
                    data['messages'] = [{
                        'status': _('Unavailable'),
                        'message': None,
                        'job': None,
                    }]
                else:
                    continue

                dates.append(data)

            if len(dates) > 0:
                response_data.append({
                    'text': _('Unavailable shifts'),
                    'shifts': dates,
                })

        dates = []
        unknown_dates = []

        for shift in init_shifts:
            data = {
                'datetime': timezone.make_aware(datetime.combine(shift.date.shift_date, shift.time)),
            }

            accepted_messages, not_accepted_messages = self._get_jo_messages(obj, data['datetime'])

            if len(not_accepted_messages) > 0:
                data['messages'] = not_accepted_messages
                dates.append(data)
            elif len(accepted_messages) == 0:
                data['messages'] = [{
                    'status': _('Unknown'),
                    'message': None,
                    'job': None,
                }]
                unknown_dates.append(data)

        if len(dates) > 0 and len(unknown_dates) < len(init_shifts):
            response_data.append({
                'text': _('Available shifts'),
                'shifts': dates,
            })
            if len(unknown_dates) > 0:
                response_data.append({
                    'text': _('Unknown shifts'),
                    'shifts': unknown_dates,
                })
        else:
            response_data = [{
                'text': text,
                'shifts': [],
            }]

        return response_data

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
        return hourly_rate

    def get_evaluation(self, obj):
        return '{} ({})'.format(obj.total_evaluation_average(), obj.candidate_evaluations.count())

    def get_favourite(self, obj):
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

    def get_tags(self, obj):
        job_tags = self.context['job'].tags
        job_tags_ids = job_tags.values_list('tag_id', flat=True)

        existing = obj.tag_rels.exclude(tag_id__in=job_tags_ids).values_list('tag__name', flat=True)
        required = obj.tag_rels.filter(tag_id__in=job_tags_ids).values_list('tag__name', flat=True)
        missing = job_tags.exclude(
            tag_id__in=obj.tag_rels.values_list('tag_id', flat=True)
        ).values_list('tag__name', flat=True)

        return {
            'required': required,
            'missing': missing,
            'existing': existing,
        }


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
                        'job': ['position', 'customer_company', 'notes', {
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


class JobsiteSerializer(
    core_mixins.WorkflowStatesColumnMixin, core_mixins.WorkflowLatestStateMixin,
    core_serializers.ApiBaseModelSerializer
):

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
                'regular_company': ('id', 'industry', 'short_name', 'logo'),
                'portfolio_manager': (
                    'id', 'job_title',
                    {
                        'contact': ('id', 'phone_mobile'),
                    }
                ),
                'primary_contact': (
                    'id', 'job_title',
                    {
                        'contact': ('id', 'phone_mobile', 'email'),
                    }
                )
            }
        )

    def validate(self, validated_data):
        is_available = validated_data.get('is_available')
        primary_contact = validated_data.get('primary_contact')
        address = validated_data.get('address')

        if is_available:
            if not primary_contact or not primary_contact.contact.email:
                raise exceptions.ValidationError({
                    'is_available': _('Supervisor with valid email is required.')
                })

            if not address:
                raise exceptions.ValidationError({
                    'is_available': _('Address is required.')
                })

        return validated_data


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
            return obj.shift_dates.filter(cancelled=False, shifts__isnull=False).latest('shift_date').id
        except hr_models.ShiftDate.DoesNotExist:
            return None


class JobsiteMapAddressSerializer(core_serializers.ApiMethodFieldsMixin, serializers.ModelSerializer):

    method_fields = ('contact', 'name', 'type')

    class Meta:
        model = core_models.Address
        fields = ('latitude', 'longitude', '__str__')

    def get_name(self, obj):
        prefix = 'client_' if obj.client_name else ''
        return getattr(obj, '%s%s' % (prefix, 'name'))

    def get_contact(self, obj):
        prefix = 'client_' if obj.client_name else ''

        first_name = getattr(obj, '%s%s' % (prefix, 'first_name'))
        last_name = getattr(obj, '%s%s' % (prefix, 'last_name'))
        title = getattr(obj, '%s%s' % (prefix, 'title'))

        if not first_name and not last_name:
            name = None
        else:
            name = '{} {}'.format(first_name, last_name)
            if title:
                name = '{} {}'.format(title, name)

        job_title = getattr(obj, '%s%s' % (prefix, 'job_title'))
        return {
            'name': '%s %s' % (job_title, name) if job_title else name,
            'phone_mobile': getattr(obj, '%s%s' % (prefix, 'phone_mobile')),
        }

    def get_type(self, obj):
        if obj.client_name:
            return 'client_hq' if obj.client_hq else 'client'
        else:
            # TODO: it takes a lot of time to check open state! do we need this?
            open_states = core_models.WorkflowObject.objects.filter(
                state__number=50,
                object_id=obj.jobsite_id,
                active=True,
            ).exists()
            return 'jobsite_open' if open_states else 'jobsite'


class JobsiteMapFilterSerializer(serializers.Serializer):

    client = serializers.CharField(required=False)
    jobsite = serializers.CharField(required=False)
    portfolio_manager = serializers.UUIDField(required=False)
    filter_by = serializers.CharField(required=False)
    show_all = serializers.BooleanField(required=False, default=False)
