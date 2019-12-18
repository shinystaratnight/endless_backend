from django.contrib import admin

from . import models


class SMSTemplateAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ['name', 'company', ]


class SMSMessageAdmin(admin.ModelAdmin):
    list_display = ['sent_at', '__str__', 'company', 'related_content_type', 'text']


admin.site.register(models.SMSMessage, SMSMessageAdmin)
admin.site.register(models.SMSRelatedObject)
admin.site.register(models.SMSTemplate, SMSTemplateAdmin)
