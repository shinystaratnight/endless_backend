from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.views import generic

from r3sourcer.apps.core.models import Form, Company
from r3sourcer.apps.core.utils.user import get_default_company


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


class RegisterFormView(generic.TemplateView):

    template_name = 'form_builder.html'

    def get_context_data(self, **kwargs):
        context = super(RegisterFormView, self).get_context_data(**kwargs)
        context['company'] = get_default_company()
        context['company_id'] = str(context['company'].pk)

        form = Form.objects.filter(Q(company=context['company']) | Q(company=None), is_active=True).first()
        if not form:
            raise Http404

        context['form'] = form
        return context
