from django.http import Http404
from django.shortcuts import get_object_or_404
from django.views import generic
from rest_framework.views import APIView
from rest_framework.response import Response

from r3sourcer.apps.core.models import Form, Company, Invoice
from r3sourcer.apps.myob.models import MYOBSyncObject
from r3sourcer.apps.myob.tasks import sync_invoice


class FormView(generic.TemplateView):

    template_name = 'form_builder.html'

    def get_context_data(self, **kwargs):
        context = super(FormView, self).get_context_data(**kwargs)
        context['company'] = get_object_or_404(Company, pk=self.kwargs['company'])
        context['company_id'] = str(context['company'].pk)
        if Form.objects.filter(pk=self.kwargs['pk'], company=context['company']).exists():
            company = context['company']
        elif Form.objects.filter(pk=self.kwargs['pk'], company=None).exists():
            company = None
        else:
            raise Http404
        context['form'] = get_object_or_404(Form, pk=self.kwargs['pk'], company=company)
        return context


class ApproveInvoiceView(APIView):
    def get(self, *args, **kwargs):
        invoice = get_object_or_404(Invoice, id=self.kwargs['id'])
        invoice.approved = True
        invoice.save()
        sync_invoice.delay(invoice.id)
        return Response()


class SyncInvoicesView(APIView):
    """
    Fetches unsynced invoices and triggers delayed task to sync them to MYOB
    """
    def get(self, *args, **kwargs):
        synced_objects = MYOBSyncObject.objects.filter(app='core',
                                                       model='Invoice',
                                                       direction='myob') \
                                               .values_list('record', flat=True)
        invoice_list = Invoice.objects.exclude(id__in=synced_objects)

        for invoice in invoice_list:
            sync_invoice.delay(invoice.id)
