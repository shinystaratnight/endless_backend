import copy
from datetime import timedelta
from io import BytesIO

import weasyprint
from django.db.models import Q

from r3sourcer.apps.pricing.models import (
    RateCoefficientModifier,
    AllowanceMixin,
)


def calc_worked_delta(timesheet):
    """
    Calculate worked hours from time sheet.

    :param timesheet: object TimeSheet
    :return: timedelta
    """

    if not timesheet.shift_ended_at:
        return timedelta()

    if timesheet.shift_ended_at < timesheet.shift_started_at:
        timesheet.shift_ended_at += timedelta(hours=12)
        timesheet.save(update_fields=['shift_ended_at'])

    delta = timesheet.shift_ended_at - timesheet.shift_started_at

    if timesheet.break_started_at and timesheet.break_ended_at:
        if timesheet.break_started_at.date() < timesheet.shift_started_at.date():
            timesheet.break_started_at += timedelta(days=1)

        if timesheet.break_started_at < timesheet.shift_started_at:
            timesheet.break_started_at += timedelta(hours=12)

        if timesheet.break_ended_at < timesheet.shift_started_at:
            timesheet.break_ended_at += timedelta(hours=12)

        if timesheet.break_started_at > timesheet.shift_ended_at \
                or timesheet.break_ended_at > timesheet.shift_ended_at:
            break_delta = timesheet.break_ended_at - timesheet.break_started_at

        elif timesheet.break_ended_at >= timesheet.break_started_at:
            break_delta = timesheet.break_ended_at - timesheet.break_started_at
            timesheet.break_ended_at = timesheet.break_ended_at
            timesheet.save(
                update_fields=['break_started_at', 'break_ended_at']
            )
        else:
            break_delta = timedelta()
    else:
        break_delta = timedelta()

    delta -= break_delta

    return delta


class BasePaymentService:

    modifier_type = RateCoefficientModifier.TYPE_CHOICES.company

    def _get_timesheets(self, timesheets, date_from=None, date_to=None, candidate=None, company=None):
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
        return timesheets.order_by('shift_started_at')

    @classmethod
    def _get_file_from_str(cls, str):
        pdf = weasyprint.HTML(string=str)
        pdf_file = BytesIO()
        pdf_file.write(pdf.write_pdf())
        pdf_file.seek(0)

        return pdf_file

    def lines_iter(self, coeffs_hours, skill, hourly_rate, timesheet):
        for coeff_hours in coeffs_hours:
            coefficient = coeff_hours['coefficient']
            notes = str(skill)
            if coefficient != 'base':
                if self.modifier_type == RateCoefficientModifier.TYPE_CHOICES.company:
                    modifier_rel = coefficient.price_list_rate_modifiers.filter(
                        price_list_rate__price_list__company=timesheet.regular_company,
                    ).first()
                elif self.modifier_type == RateCoefficientModifier.TYPE_CHOICES.candidate:
                    modifier_rel = coefficient.candidate_skill_coefficient_rels.filter(
                        skill_rel__candidate_contact=timesheet.candidate_contact,
                    ).first()

                modifier = modifier_rel and modifier_rel.rate_coefficient_modifier

                if not modifier:
                    modifier = coefficient.rate_coefficient_modifiers.filter(
                        type=self.modifier_type, default=True,
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
