from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.contrib.sites.models import Site
from django.template import Context
from django.template.loader import get_template
from django.utils.formats import date_format
from django.utils.timezone import localtime
from filer.models import Folder, File

from r3sourcer.apps.core.models import Invoice, InvoiceLine, InvoiceRule, VAT
from r3sourcer.apps.pricing.services import PriceListCoefficientService
from r3sourcer.apps.pricing.models import RateCoefficientModifier, PriceListRate

from .base import BasePaymentService, calc_worked_delta

from ..models import TimeSheet
from ..utils.utils import get_invoice_rule


class InvoiceService(BasePaymentService):

    def _get_price_list_rate(self, skill, customer_company, industry):
        price_list_rate = PriceListRate.objects.filter(
            skill=skill,
            price_list__company=customer_company,
        ).last()

        return price_list_rate

    def calculate(self, company, from_date=None, timesheets=None,
                  show_candidate=False):

        timesheets = self._get_timesheets(timesheets, from_date, company=company)
        coefficient_service = PriceListCoefficientService()

        lines = []
        jobsites = set()

        for timesheet in timesheets:
            jobsite = timesheet.vacancy_offer.vacancy.jobsite
            industry = jobsite.industry
            skill = timesheet.vacancy_offer.vacancy.position
            customer_company = timesheet.vacancy_offer.shift.date.vacancy.customer_company
            price_list_rate = self._get_price_list_rate(
                skill, customer_company, industry
            )
            started_at = localtime(timesheet.shift_started_at)
            worked_hours = calc_worked_delta(timesheet)
            coeffs_hours = coefficient_service.calc_company(
                company, industry, skill,
                RateCoefficientModifier.TYPE_CHOICES.company,
                started_at,
                worked_hours,
                break_started=timesheet.break_started_at,
                break_ended=timesheet.break_ended_at,
            )

            lines_iter = self.lines_iter(
                coeffs_hours, skill, price_list_rate.hourly_rate
            )

            for raw_line in lines_iter:
                rate = raw_line['rate']
                notes = raw_line['notes']
                units = Decimal(raw_line['hours'].total_seconds() / 3600)

                if not units:
                    continue

                if show_candidate:
                    notes = '{} - {}'.format(
                        notes, str(timesheet.vacancy_offer.candidate_contact)
                    )

                vat_name = 'GST' if company.registered_for_gst else 'GNR'
                lines.append({
                    'date': started_at.date(),
                    'units': units,
                    'notes': notes,
                    'unit_price': rate,
                    'amount': rate * units,
                    'vat': VAT.objects.get(name=vat_name),
                    'timesheet': timesheet,
                })
                jobsites.add(str(jobsite))

        return lines, jobsites

    @classmethod
    def generate_pdf(cls, invoice):
        template = get_template('payment/invoices.html')

        code_data = {
            'code': 'GNR',
            'rate': '0',
            'tax': '0',
            'amount': '{0:.2f}'.format(invoice.total)
        }
        if invoice.customer_company.registered_for_gst:
            code_data = {
                'code': 'GST',
                'rate': '10',
                'tax': '{0:.2f}'.format(invoice.total * Decimal(0.1)),
                'amount': '{0:.2f}'.format(invoice.total)
            }

        domain = Site.objects.get_current().domain

        context = Context({
            'lines': invoice.invoice_lines.all(),
            'invoice': invoice,
            'company': invoice.customer_company,
            'code_data': code_data,
            'master_company': invoice.provider_company,
            'STATIC_URL': 'https://%s/static' % domain
        })

        pdf_file = cls._get_file_from_str(str(template.render(context)))

        folder, created = Folder.objects.get_or_create(
            parent=invoice.customer_company.files,
            name='invoices',
        )

        file_name = 'invoice_{}_{}.pdf'.format(
            invoice.number,
            date_format(invoice.date, 'Y_m_d')
        )

        file_obj, _ = File.objects.get_or_create(
            folder=folder,
            name='invoice_{}_{}.pdf'.format(
                invoice.number,
                date_format(invoice.date, 'Y_m_d')
            ),
            file=ContentFile(pdf_file.read(), name=file_name)
        )

        return file_obj

    def _prepare_invoice(self, company, from_date=None, timesheets=None,
                         show_candidate=False):

        if hasattr(company, 'subcontractor'):
            candidate = company.subcontractor.primary_contact
            timesheets = TimeSheet.objects.filter(
                vacancy_offer__candidate_contact=candidate
            )

        lines, jobsites = self.calculate(company, from_date, timesheets,
                                         show_candidate)

        if lines:
            master_company = company.get_master_company()
            provider_company = master_company[0] if master_company else company
            invoice_rule = company.invoice_rules.first()
            invoice = Invoice.objects.create(
                provider_company=provider_company,
                customer_company=company,
                order_number=', '.join(jobsites),
                period=invoice_rule.period,
                separation_rule=invoice_rule.separation_rule
            )

            invoice_lines = []
            total = Decimal()
            for line in lines:
                total += line['amount']
                invoice_lines.append(InvoiceLine(invoice=invoice, **line))

            InvoiceLine.objects.bulk_create(invoice_lines)

            invoice.save(update_fields=['total', 'tax', 'total_with_tax'])

            self.generate_pdf(invoice)

            return invoice

    def prepare(self, company, from_date):
        try:
            return Invoice.objects.filter(
                customer_company=company,
                date__gte=from_date
            ).latest('date')
        except Invoice.DoesNotExist:
            pass

        invoice_rule = get_invoice_rule(company)
        separation_rule = invoice_rule.separation_rule
        if separation_rule == InvoiceRule.SEPARATION_CHOICES.one_invoce:
            self._prepare_invoice(
                company, from_date,
                show_candidate=invoice_rule.show_candidate_name
            )
        elif separation_rule == InvoiceRule.SEPARATION_CHOICES.per_jobsite:
            jobsites = [x.jobsite for x in company.jobsite_addresses.all()]
            for jobsite in set(jobsites):
                timesheets = TimeSheet.objects.filter(
                    vacancy_offer__shift__date__vacancy__jobsite=jobsite
                )
                self._prepare_invoice(
                    company, from_date, timesheets,
                    show_candidate=invoice_rule.show_candidate_name
                )
        elif separation_rule == InvoiceRule.SEPARATION_CHOICES.per_candidate:
            timesheets = self._get_timesheets(None, from_date, company=company)
            candidates = set(timesheets.values_list(
                'vacancy_offer__candidate_contact', flat=True
            ))

            for candidate in candidates:
                timesheets = TimeSheet.objects.filter(
                    vacancy_offer__candidate_contact_id=candidate
                )
                self._prepare_invoice(
                    company, from_date, timesheets,
                    show_candidate=invoice_rule.show_candidate_name,
                )
