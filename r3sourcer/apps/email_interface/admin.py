from django.contrib import admin

from r3sourcer.apps.email_interface import models as email_models
from r3sourcer.helpers.admin.filters import LanguageListFilter, CompanyListFilter


class EmailTemplateAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ['company', 'name', 'slug', 'language_name']
    ordering = ['company', 'slug', 'language']
    list_filter = (CompanyListFilter, LanguageListFilter, 'name')

    @classmethod
    def language_name(cls, obj):
        return obj.language.name


class DefaultEmailTemplateAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ['name', 'slug', 'language_name']
    ordering = ['slug', 'language']
    list_filter = (LanguageListFilter, 'name')

    @classmethod
    def language_name(cls, obj):
        return obj.language.name


admin.site.register(email_models.EmailMessage, list_display=['from_email', 'to_addresses', 'created_at'])
admin.site.register(email_models.EmailBody, list_display=['message', 'created_at'])
admin.site.register(email_models.DefaultEmailTemplate, DefaultEmailTemplateAdmin)
admin.site.register(email_models.EmailTemplate, EmailTemplateAdmin)
