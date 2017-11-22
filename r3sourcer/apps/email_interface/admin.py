from django.contrib import admin

from r3sourcer.apps.email_interface import models as email_models


class EmailTemplateAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}


admin.site.register(email_models.EmailMessage)
admin.site.register(email_models.EmailBody)
admin.site.register(email_models.EmailTemplate, EmailTemplateAdmin)
