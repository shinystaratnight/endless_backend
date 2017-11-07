from django.shortcuts import get_object_or_404
from django.views import generic

from .models import Form


class FormView(generic.TemplateView):

    template_name = 'form_builder.html'

    def get_context_data(self, **kwargs):
        context = super(FormView, self).get_context_data(**kwargs)
        context['form'] = get_object_or_404(Form, pk=self.kwargs['pk'])
        return context
