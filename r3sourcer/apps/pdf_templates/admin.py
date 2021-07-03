from django.contrib import admin, messages
from django.contrib.admin.helpers import ActionForm
from django import forms
from django.forms import model_to_dict

from . import models
from ..core.models import Language
from ...helpers.admin.filters import LanguageListFilter, CompanyListFilter


class CreateWithLanguage(ActionForm):
    language_id = forms.ModelChoiceField(Language.objects.all(), required=False)

def create_with_languages(modeladmin, request, queryset):
    if not request.POST.get('language_id'):
        modeladmin.message_user(request, "Choose language", messages.ERROR)
        return
    for obj in queryset:
        src_template = model_to_dict(obj, exclude=['id', 'language'])
        unique = dict(slug=src_template['slug'],
                      language_id=request.POST['language_id'])
        qs = models.DefaultPDFTemplate.objects.filter(**unique)
        if qs.all():
            modeladmin.message_user(request,
                                    'Template with slug <{slug}> and language <{language_id}> already exists'
                                    .format(**unique),
                                    messages.ERROR)
            continue
        new_template = models.DefaultPDFTemplate(**src_template)
        new_template.language_id = request.POST['language_id']
        new_template.save()
        modeladmin.message_user(request,
                                "Template with slug <{slug}> and language <language_id> successfully copied"
                                .format(**unique),
                                messages.SUCCESS)

create_with_languages.short_description = 'Copy template with selected language'


class PDFTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'company', 'language')
    ordering = ['name']
    list_filter = (CompanyListFilter, LanguageListFilter, 'name')


class DefaultPDFTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'language')
    ordering = ['name']
    list_filter = (LanguageListFilter, 'name')
    action_form = CreateWithLanguage
    actions = [create_with_languages]

admin.site.register(models.PDFTemplate, PDFTemplateAdmin)
admin.site.register(models.DefaultPDFTemplate, DefaultPDFTemplateAdmin)
