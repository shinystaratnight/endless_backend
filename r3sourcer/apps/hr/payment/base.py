import copy
from datetime import timedelta
from io import BytesIO

import weasyprint
from django.db.models import Q
from django.utils.timezone import localtime

from r3sourcer.apps.pricing.models import (
    RateCoefficientModifier, AllowanceMixin
)
from ..models import TimeSheet


def calc_worked_delta(timesheet):
    """
    Calculate worked hours from time sheet.

    :param timesheet: object TimeSheet
    :return: timedelta
    """

    started = localtime(timesheet.shift_started_at)
    ended = timesheet.shift_ended_at
    if ended:
        ended = localtime(ended)

    hours_12 = timedelta(hours=12)
    if ended:
        if ended < started:
            timesheet.shift_ended_at += hours_12
            timesheet.save(update_fields=['shift_ended_at'])
            ended = timesheet.shift_ended_at

        delta = ended - started

        if timesheet.break_started_at and timesheet.break_ended_at:
            break_started = localtime(timesheet.break_started_at)
            break_ended = localtime(timesheet.break_ended_at)
            if break_started.date() < started.date():
                break_started += timedelta(days=1)
            if break_started < started:
                break_started += hours_12
            if break_ended < started:
                break_ended += hours_12

            if break_started > ended or break_ended > ended:
                break_delta = timedelta()
            elif break_ended >= break_started:
                break_delta = break_ended - break_started
                timesheet.break_started_at = break_started
                timesheet.break_ended_at = break_ended
                timesheet.save(
                    update_fields=['break_started_at', 'break_ended_at']
                )
            else:
                break_delta = timedelta()
        else:
            break_delta = timedelta()

        delta -= break_delta
    else:
        delta = timedelta()

    return delta


class BasePaymentService:

    modifier_type = RateCoefficientModifier.TYPE_CHOICES.company

    def _get_timesheets(self, timesheets, date_from=None, date_to=None, candidate=None, company=None):

        timesheets = timesheets or TimeSheet.objects.order_by('shift_started_at')
        timesheets = timesheets.filter(
            candidate_submitted_at__isnull=False,
            supervisor_approved_at__isnull=False
        )

        if company:
            timesheets = timesheets.filter(
                job_offer__shift__date__job__jobsite__regular_company=company
            )

        if candidate:
            timesheets = timesheets.filter(
                job_offer__candidate_contact=candidate,
            )

        if date_from:
            qry = Q(shift_started_at__date__gte=date_from)
            if date_to:
                qry &= Q(shift_started_at__date__lt=date_to)

            timesheets = timesheets.filter(qry)

        return timesheets

    @classmethod
    def _get_file_from_str(cls, str):
        pdf = weasyprint.HTML(string=str)
        pdf_file = BytesIO()
        pdf_file.write(pdf.write_pdf())
        pdf_file.seek(0)

        return pdf_file

    def lines_iter(self, coeffs_hours, skill, hourly_rate):
        for coeff_hours in coeffs_hours:
            coefficient = coeff_hours['coefficient']
            notes = str(skill)
            if coefficient != 'base':
                modifier = coefficient.rate_coefficient_modifiers.filter(
                    type=self.modifier_type
                ).first()

                is_allowance = any([
                    isinstance(rule.rule, AllowanceMixin)
                    for rule in coefficient.rate_coefficient_rules.all()]
                )
                if is_allowance:
                    rate = modifier.fixed_override
                else:
                    rate = modifier.calc(hourly_rate)
                notes = '{} {}'.format(notes, str(coefficient))
            else:
                rate = hourly_rate

            line = copy.copy(coeff_hours)
            line['rate'] = rate
            line['notes'] = notes

            yield line
