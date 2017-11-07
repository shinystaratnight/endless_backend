from datetime import timedelta, date
from calendar import monthrange

from celery import shared_task
from django.utils import timezone

from r3sourcer.apps.core.models import Company, InvoiceRule, Invoice, Contact
from .models import PayslipRule, Payslip, Jobsite, ContactJobsiteDistanceCache
from .payment import InvoiceService, PayslipService
from .utils.utils import get_invoice_rule, get_payslip_rule, calculate_distances_for_jobsite


@shared_task
def prepare_invoices():
    service = InvoiceService()
    now = timezone.localtime(timezone.now())

    for company in Company.objects.all():
        invoice_rule = get_invoice_rule(company)

        if not invoice_rule:
            continue

        if invoice_rule.period == InvoiceRule.PERIOD_CHOICES.monthly and \
                invoice_rule.period_zero_reference == now.day:
            if now.month == 1:
                year = now.year - 1
                month = 12
            else:
                year = now.year
                month = month - 1

            last_day = monthrange(year, month)
            day = now.day if now.day <= last_day else last_day

            from_date = date(year, month, day)
        elif invoice_rule.period == InvoiceRule.PERIOD_CHOICES.fortnightly:
            from_date = (now - timedelta(days=14)).date()
        elif invoice_rule.period == InvoiceRule.PERIOD_CHOICES.weekly:
            from_date = (now - timedelta(days=7)).date()
        elif invoice_rule.period == InvoiceRule.PERIOD_CHOICES.daily:
            from_date = (now - timedelta(days=1)).date()
        else:
            from_date = None

        if from_date:
            existing_invoice = Invoice.objects.filter(
                company=company,
                date__gte=from_date
            )
            if existing_invoice.exists():
                existing_invoice = existing_invoice.latest('date')
                from_date = existing_invoice.date + timedelta(days=1)

            service.prepare(company, from_date)


@shared_task
def prepare_payslips():
    service = PayslipService()
    now = timezone.localtime(timezone.now())

    for company in Company.objects.all():
        payslip_rule = get_payslip_rule(company)

        if not payslip_rule:
            continue

        to_date = now.date()
        if payslip_rule.period == PayslipRule.PERIOD_CHOICES.monthly and \
                payslip_rule.period_zero_reference == now.day:
            if now.month == 1:
                year = now.year - 1
                month = 12
            else:
                year = now.year
                month = month - 1

            last_day = monthrange(year, month)
            day = now.day if now.day <= last_day else last_day

            from_date = date(year, month, day)
        elif payslip_rule.period == PayslipRule.PERIOD_CHOICES.fortnightly:
            from_date = (now - timedelta(days=14)).date()
        elif payslip_rule.period == PayslipRule.PERIOD_CHOICES.weekly:
            from_date = (now - timedelta(days=7)).date()
        elif payslip_rule.period == PayslipRule.PERIOD_CHOICES.daily:
            from_date = (now - timedelta(days=1)).date()
        else:
            from_date = None

        if from_date:
            existing_payslip = Payslip.objects.filter(
                company=company,
                from_date__gte=from_date,
            )
            if existing_payslip.exists():
                existing_payslip = existing_payslip.latest('date')
                from_date = existing_payslip.from_date + timedelta(days=1)

            service.prepare(company, from_date, to_date)


@shared_task
def update_all_distances():

    all_calculated_jobsites = Jobsite.objects.filter(
        id__in=ContactJobsiteDistanceCache.objects.filter(
            updated_at__isnull=True
        ).values('jobsite')
    )

    for jobsite in all_calculated_jobsites:
        if not (jobsite.latitude == 0 and jobsite.longitude == 0):
            contacts = Contact.objects.filter(distance_caches__jobsite=jobsite)
            if not calculate_distances_for_jobsite(contacts, jobsite):
                break
