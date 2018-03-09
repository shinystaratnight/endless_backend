from django.http import Http404
from django.shortcuts import get_object_or_404
from django.views import generic
from rest_framework.views import APIView
from rest_framework.response import Response

from r3sourcer.apps.core.models import Form, Company, Invoice


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
        return Response()
