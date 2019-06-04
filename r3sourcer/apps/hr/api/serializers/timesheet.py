from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.utils.formats import time_format, date_format
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from r3sourcer.apps.core.models import Company
from r3sourcer.apps.core.api.fields import ApiBaseRelatedField, ApiContactPictureField
from r3sourcer.apps.core.api.serializers import ApiBaseModelSerializer
from r3sourcer.apps.myob.models import MYOBSyncObject
from r3sourcer.apps.pricing.utils.utils import format_timedelta
from r3sourcer.apps.sms_interface import models as sms_models
from r3sourcer.apps.sms_interface.api import serializers as sms_serializers

from ...models import TimeSheet, CandidateEvaluation


__all__ = [
    'TimeSheetSignatureSerializer',
    'PinCodeSerializer',
    'TimeSheetSerializer',
]


class ValidateApprovalScheme(serializers.Serializer):

    APPROVAL_SCHEME = None

    def validate(self, attrs):
        # get master companies and check existing
        client_company =  self.instance.job_offer.job.customer_company
        companies = self.instance.supervisor.get_master_company()
        if len(companies) == 0:
            raise serializers.ValidationError(_("Supervisor has not master company"))

        if client_company.timesheet_approval_scheme != self.APPROVAL_SCHEME:
            raise serializers.ValidationError(_("Incorrect approval scheme"))
        return attrs


class ApiTimesheetImageFieldsMixin():
    image_fields = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        image_fields = self.image_fields or []
        for image_field in image_fields:
            self.fields[image_field] = ApiContactPictureField(required=False)


class TimeSheetSignatureSerializer(ValidateApprovalScheme, ApiTimesheetImageFieldsMixin, ApiBaseModelSerializer):

    image_fields = ('supervisor_signature',)
    APPROVAL_SCHEME = Company.TIMESHEET_APPROVAL_SCHEME.SIGNATURE

    class Meta:
        model = TimeSheet
        fields = ('supervisor_signature',)
        extra_kwargs = {'supervisor_signature': {
            'required': True,
            'allow_empty_file': False,
            'allow_null': False}
        }


class PinCodeSerializer(ValidateApprovalScheme):

    APPROVAL_SCHEME = Company.TIMESHEET_APPROVAL_SCHEME.PIN

    pin_code = serializers.CharField(min_length=4)

    def validate(self, attrs):
        attrs = super(PinCodeSerializer, self).validate(attrs)
        supervisor = self.instance.supervisor
        if supervisor.pin_code != attrs['pin_code']:
            raise serializers.ValidationError({'pin_code': _("Incorrect pin code")})
        return attrs


class TimeSheetSerializer(ApiTimesheetImageFieldsMixin, ApiBaseModelSerializer):
    image_fields = ('supervisor_signature',)

    method_fields = (
        'company', 'jobsite', 'position', 'shift_started_ended', 'break_started_ended', 'job', 'related_sms',
        'candidate_filled', 'supervisor_approved', 'resend_sms_candidate', 'resend_sms_supervisor', 'candidate_sms',
        'candidate_sms_old', 'candidate_submit_hidden', 'evaluated', 'myob_status', 'show_sync_button', 'supervisor_sms',
        'invoice', 'shift', 'evaluation'
    )

    class Meta:
        model = TimeSheet
        fields = (
            'id', 'job_offer', 'going_to_work_sent_sms', 'going_to_work_reply_sms', 'going_to_work_confirmation',
            'shift_started_at', 'break_started_at', 'break_ended_at', 'shift_ended_at', 'supervisor',
            'candidate_submitted_at', 'supervisor_approved_at', 'supervisor_approved_scheme', 'candidate_rate',
            'rate_overrides_approved_by', 'rate_overrides_approved_at', 'sync_status', 'status', 'supervisor_modified',
            'supervisor_modified_at', 'supervisor_signature', 'process_status'
        )
        related_fields = {
            'job_offer': ('id', {
                'candidate_contact': ('id', {
                    'contact': ('picture', ),
                    'candidate_scores': ['average_score'],
                }, ),
            }, ),
        }

    def get_company(self, obj):
        if obj:
            company = obj.job_offer.job.customer_company
            return {
                    'id': company.id, '__str__': str(company),
                    'supervisor_approved_scheme': company.timesheet_approval_scheme
                    }

    def get_jobsite(self, obj):
        if obj:
            jobsite = obj.job_offer.job.jobsite
            return {
                'id': jobsite.id,
                'address': {
                    'id': jobsite.address.id,
                    '__str__': str(jobsite.address),
                },
                '__str__': str(jobsite),
            }

    def get_position(self, obj):
        if obj:
            position = obj.job_offer.job.position
            return {'id': position.id, '__str__': str(position)}

    def _format_date_range(self, date_start, date_end):
        if date_start:
            dt = timezone.make_naive(date_start)
            start = date_format(dt, settings.DATETIME_FORMAT)
        else:
            start = '-'

        if date_end:
            end = time_format(timezone.make_naive(date_end), settings.TIME_FORMAT)
        else:
            end = '-'

        return '{} / {}'.format(start, end)

    def get_shift_started_ended(self, obj):
        return self._format_date_range(obj.shift_started_at, obj.shift_ended_at)

    def get_break_started_ended(self, obj):
        return self._format_date_range(obj.break_started_at, obj.break_ended_at)

    def get_job(self, obj):
        job = obj.job_offer.job
        return {'id': job.id, '__str__': str(job)}

    def get_related_sms(self, obj):
        ct = ContentType.objects.get_for_model(TimeSheet)
        smses = sms_models.SMSMessage.objects.filter(
            related_objects__content_type=ct, related_objects__object_id=obj.id
        )
        if smses.exists():
            return sms_serializers.SMSMessageSerializer(smses, many=True, fields=['id', '__str__', 'type']).data

    def get_candidate_filled(self, obj):
        return obj.candidate_submitted_at is not None

    def get_supervisor_approved(self, obj):
        return obj.supervisor_approved_at is not None

    def get_resend_sms_candidate(self, obj):
        return (
            obj.going_to_work_confirmation and obj.candidate_submitted_at is None and
            obj.supervisor_approved_at is None and obj.shift_ended_at <= timezone.now()
        )

    def get_resend_sms_supervisor(self, obj):
        return (
            obj.going_to_work_confirmation and obj.candidate_submitted_at is not None and
            obj.supervisor_approved_at is None and obj.shift_ended_at <= timezone.now()
        )

    def get_candidate_submit_hidden(self, obj):
        return not self.get_resend_sms_candidate(obj)

    def get_evaluated(self, obj):
        return obj.candidate_evaluations.exists()

    def get_evaluation(self, obj):
        if obj.candidate_evaluations.exists():
            return CandidateEvaluationSerializer(
                obj.candidate_evaluations.all().first(),
                fields=['id', 'evaluation_score', 'evaluated_at',]
            ).data

    def get_myob_status(self, obj):
        if obj.supervisor_approved_at and obj.candidate_submitted_at:
            sync_objs = MYOBSyncObject.objects.filter(record=obj.id)
            if sync_objs.filter(synced_at__gte=obj.updated_at).exists():
                return _('Synced')
            elif sync_objs.exists():
                return _('Sync is outdated')
            else:
                return _('Not Synced')

        return None

    def get_show_sync_button(self, obj):
        allowed_states = [
            TimeSheet.SYNC_STATUS_CHOICES.not_synced,
            TimeSheet.SYNC_STATUS_CHOICES.sync_failed,
        ]
        return bool(obj.sync_status in allowed_states and obj.supervisor_approved_at and obj.candidate_submitted_at)

    def _get_related_sms(self, obj, template_slug):
        ct = ContentType.objects.get_for_model(TimeSheet)
        timesheet_date = timezone.localtime(obj.shift_started_at).date()
        sms = sms_models.SMSMessage.objects.filter(
            related_objects__content_type=ct, related_objects__object_id=obj.id,
            template__slug=template_slug, sent_at__date=timesheet_date
        ).first()

        if not sms:
            sms = sms_models.SMSMessage.objects.filter(
                template__slug=template_slug, sent_at__date=timesheet_date,
                company=obj.master_company
            ).first()
            if not sms:
                sms = sms_models.SMSMessage.objects.filter(
                    template__slug=template_slug, related_objects__object_id=obj.id,
                    company=obj.master_company
                    ).first()

        return sms and sms_serializers.SMSMessageSerializer(sms, fields=['id', '__str__']).data

    def get_supervisor_sms(self, obj):
        return self._get_related_sms(obj, 'supervisor-timesheet-sign')

    def get_candidate_sms(self, obj):
        return self._get_related_sms(obj, 'candidate-timesheet-hours')

    def get_candidate_sms_old(self, obj):
        return self._get_related_sms(obj, 'candidate-timesheet-hours-old')

    def get_invoice(self, obj):
        invoice_line = obj.invoice_lines.first()
        invoice = invoice_line and invoice_line.invoice
        return invoice and ApiBaseRelatedField.to_read_only_data(invoice)

    def get_shift(self, obj):
        if obj:
            shift = obj.job_offer.shift
            return {
                'id': shift.id,
                'date': {
                    'id': shift.date.id,
                    '__str__': str(shift.date),
                },
                '__str__': str(shift),
            }


class CandidateEvaluationSerializer(ApiBaseModelSerializer):

    method_fields = ('jobsite', 'position')

    class Meta:
        model = CandidateEvaluation
        fields = (
            'candidate_contact', 'supervisor', 'evaluated_at', 'reference_timesheet', 'evaluation_score',
            {
                'supervisor': ('id', 'contact', 'job_title'),
                'reference_timesheet': ('id', 'shift_started_at', 'shift_ended_at'),
            }
        )

    def get_jobsite(self, obj):
        if not obj.reference_timesheet:
            return

        return ApiBaseRelatedField.to_read_only_data(obj.reference_timesheet.job_offer.job.jobsite)

    def get_position(self, obj):
        if not obj.reference_timesheet:
            return

        return ApiBaseRelatedField.to_read_only_data(obj.reference_timesheet.job_offer.job.position)


class TimeSheetManualSerializer(ApiBaseModelSerializer):

    method_fields = (
        'shift_total', 'break_total', 'total_worked'
    )

    no_break = serializers.BooleanField(required=False)
    send_supervisor_message = serializers.BooleanField(required=False)
    send_candidate_message = serializers.BooleanField(required=False)
    candidate_submitted_at = serializers.DateTimeField(write_only=True, required=False)
    supervisor_approved_at = serializers.DateTimeField(write_only=True, required=False)

    class Meta:
        model = TimeSheet
        fields = (
            'id', 'shift_started_at', 'break_started_at', 'break_ended_at', 'shift_ended_at', 'no_break',
            'send_supervisor_message', 'send_candidate_message', 'candidate_submitted_at', 'supervisor_approved_at'
        )

    def validate(self, data):
        if data.get('no_break'):
            data['break_started_at'] = None
            data['break_ended_at'] = None

        return data

    def get_shift_total(self, obj):
        return format_timedelta(obj.shift_delta)

    def get_break_total(self, obj):
        return format_timedelta(obj.break_delta)

    def get_total_worked(self, obj):
        return format_timedelta(obj.shift_delta - obj.break_delta)
