from django.contrib import admin

from r3sourcer.apps.email_interface import models as email_models


class EmailTemplateAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ['company', 'name', 'slug']
    ordering = ['company', 'slug']


admin.site.register(email_models.EmailMessage, list_display=['from_email', 'to_addresses', 'created_at'])
admin.site.register(email_models.EmailBody, list_display=['message', 'created_at'])
admin.site.register(email_models.DefaultEmailTemplate, list_display=['name', 'slug'])
admin.site.register(email_models.EmailTemplate, EmailTemplateAdmin)
