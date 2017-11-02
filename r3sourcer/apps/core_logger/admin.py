from django.contrib import admin
from django.contrib.admin.sites import NotRegistered

from endless_logger.admin import LoggerMixin
from r3sourcer.apps.core import models
from r3sourcer.apps.core.admin import (
    BaseAdmin, UserAdmin, CompanyAdmin, SuperuserAdmin
)


DEFAULT_MODELS_LIST = [models.Contact, models.BankAccount, models.Address,
                       models.WorkflowObject, models.CompanyLocalization,
                       models.InvoiceLine, models.Note, models.VAT,
                       models.InvoiceRule]

BASE_MODELS_LIST = [models.CompanyRel, models.CompanyAddress,
                    models.CompanyContact, models.CompanyContactAddress,
                    models.CompanyContactRelationship, models.Invoice,
                    models.SiteCompany]

SUPERUSER_MODELS_LIST = [models.WorkflowNode, models.Workflow]

try:
    admin.site.unregister(DEFAULT_MODELS_LIST)
except NotRegistered:
    pass

try:
    admin.site.unregister(BASE_MODELS_LIST)
except NotRegistered:
    pass

try:
    admin.site.unregister(SUPERUSER_MODELS_LIST)
except NotRegistered:
    pass

try:
    admin.site.unregister([models.User, models.Company])
except NotRegistered:
    pass


class LoggerAdmin(LoggerMixin, admin.ModelAdmin):
    pass


class LoggerBaseAdmin(LoggerMixin, BaseAdmin):
    pass


class UserLoggerAdmin(LoggerMixin, UserAdmin):
    pass


class CompanyLoggerAdmin(LoggerMixin, CompanyAdmin):
    pass


class SuperuserLoggerAdmin(LoggerMixin, SuperuserAdmin):
    pass


admin.site.register(models.User, UserLoggerAdmin)
admin.site.register(models.Company, CompanyLoggerAdmin)
admin.site.register(DEFAULT_MODELS_LIST, LoggerAdmin)
admin.site.register(BASE_MODELS_LIST, LoggerBaseAdmin)
admin.site.register(SUPERUSER_MODELS_LIST, SuperuserLoggerAdmin)
