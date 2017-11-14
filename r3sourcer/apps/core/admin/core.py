from django.conf import settings
from django.conf.urls import url
from django.contrib import admin, messages
from django.contrib.admin.options import csrf_protect_m
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.sites.models import Site
from django.forms import Textarea
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from functools import reduce

from mptt.admin import MPTTModelAdmin


# Register your models here.
from r3sourcer.apps.core_utils.filters import RelatedDropDownFilter
from r3sourcer.apps.core_utils.mixins import ExtendedDraggableMPTTAdmin

from .. import forms
from .. import models
from ..utils.companies import get_closest_companies


class BaseAdminPermissionMixin(object):
    def get_queryset(self, request):
        qs = super(BaseAdminPermissionMixin, self).get_queryset(request)

        if not request.user.is_superuser:
            master_companies = get_closest_companies(request)
            if len(master_companies) > 0:
                lookups = []
                for master_company in master_companies:
                    regular_companies = master_company.get_regular_companies()
                    for rc in regular_companies:
                        temp = self.model.get_master_company_lookup(rc)
                        if temp:
                            lookups.append(temp)

                    temp = self.model.get_master_company_lookup(master_company)
                    if temp:
                        lookups.append(temp)

                if lookups:
                    from operator import __or__ as OR
                    return qs.filter(reduce(OR, lookups)).distinct()
                else:
                    return qs.none()
            else:
                return qs.none()
        return qs


class ContactInlineAdmin(admin.TabularInline):

    verbose_name_plural = _("Contact information")
    form = forms.ContactForm
    model = models.Contact
    extra = 0
    min_num = 1
    max_num = 1


class UserAdmin(BaseUserAdmin):

    change_form_template = 'loginas/change_form.html'

    filter_horizontal = ('groups',)

    fieldsets = (
        (_("Permissions"), {
            'classes': ['collapse'],
            'fields': ['is_active', ('is_staff', 'is_superuser'), 'groups', 'user_permissions']
        }),
        (_("Details"), {
            'classes': ['collapse'],
            'fields': ['date_joined', 'last_login']
        })
    )

    readonly_fields = ('date_joined', 'last_login')

    list_display = ('get_full_name', 'email', 'phone_mobile')
    list_display_links = list_display
    ordering = ('date_joined',)
    search_fields = ('contact__email', 'contact__phone_mobile')

    inlines = [ContactInlineAdmin]

    def get_readonly_fields(self, request, obj=None):
        fields = self.readonly_fields
        if hasattr(self.model, 'created_by'):
            fields += ('created_by',)
        return fields

    def get_fieldsets(self, request, obj=None):
        fieldsets = self.fieldsets
        if hasattr(self.model, 'created_by'):
            fieldsets += ((None, {'fields': ['created_by']}),)
        if obj is None:
            return (
                (_("Password"), {
                    'fields': ['password1', 'password2']
                }),
            ) + fieldsets
        return (
            (_("Password"), {
                'fields': ['password']
            }),
        ) + fieldsets


class CompanyAdmin(BaseAdminPermissionMixin, admin.ModelAdmin):
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj:

            if obj.company_addresses.exists():
                company_address = obj.company_addresses.filter(hq=True).first()
                country = company_address.address.country
                fields_data = models.CompanyLocalization.get_company_metadata(country=country)

                for key, value in fields_data.items():
                    if key in form.base_fields:
                        if not value["active"]:
                            del form.base_fields[key]
                            continue

                        form.base_fields[key].label = value["verbose_value"]
                        form.base_fields[key].help_text = value["help_text"]
        return form


class BaseAdmin(BaseAdminPermissionMixin, admin.ModelAdmin):
    pass


class MessageTemplateAdmin(admin.ModelAdmin):
    change_form_template = 'admin/message_templates/change_form.html'
    text_area_attrs = {
        'rows': 20,
        'data-editor': True,
        'data-mode': getattr(settings, 'DJANGOCMS_SNIPPET_THEME', 'html'),
        'data-theme': getattr(settings, 'DJANGOCMS_SNIPPET_MODE', 'github'),
    }

    formfield_overrides = {
        "message_html_template": {'widget': Textarea(attrs=text_area_attrs)}
    }

    def get_list_display(self, request):
        return [f.name for f in self.model._meta.fields if f.name != "id"] + ["get_clone"]

    def get_list_display_links(self, request, list_display):
        return ["name"]

    def get_clone(self, obj):
        return format_html(
            '<a href="{link}?{param_name}={param_value}">{name}</a>',
            link=reverse('admin:{app}_{model}_add'.format(
                app=self.model._meta.app_label,
                model=self.model._meta.model_name,
            )),
            param_name='from',
            param_value=obj.id,
            name=_("Clone"))

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        if request.GET.get('from', None):
            try:
                cloning_obj = self.model.objects.get(id=request.GET.get('from', None))
                for f in self.model._meta.fields:
                    if f.name not in ["id", "updated_at", "created_at"]:
                        form.base_fields[f.name].initial = getattr(cloning_obj, f.name)
            except Exception as e:
                pass
        return form


class SuperuserAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class TagAdmin(MPTTModelAdmin):
    pass


class ExtranetNavigationAdmin(ExtendedDraggableMPTTAdmin):
    pass


class SiteAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class PublicHolidayAdmin(admin.ModelAdmin):

    list_display = ('country', 'date', 'name')
    list_display_links = list_display

    change_list_template = "admin/publicholiday/change_list.html"
    list_filter = (('country', RelatedDropDownFilter),)

    def get_model_perms(self, request):
        # TODO: is supervisor perms
        return {
            'add': self.has_add_permission(request),
            'change': self.has_change_permission(request),
            'delete': self.has_delete_permission(request)
        }

    def changelist_view(self, request, extra_context=None):
        """ Extending context with holiday fetching form """

        extra_context = extra_context or {}
        extra_context['holiday_form'] = forms.PublicHolidayFetchingForm()
        return super(PublicHolidayAdmin, self).changelist_view(request, extra_context)

    def get_urls(self):
        """ Extending admin urls with custom view """

        urls = super(PublicHolidayAdmin, self).get_urls()
        return [url(r'^fetch-holiday-dates/$', self.admin_site.admin_view(self.fetch_public_holidays_view),
                    name='publicholiday_fetch_dates')] + urls

    @csrf_protect_m
    def fetch_public_holidays_view(self, request):
        """ Handler for holiday fetching """

        from r3sourcer.apps.core.tasks import fetch_holiday_dates
        form = forms.PublicHolidayFetchingForm(request.POST)
        if form.is_valid():
            country = form.cleaned_data['country']
            year = form.cleaned_data['year']
            month = form.cleaned_data['month']
            fetch_holiday_dates.apply_async(kwargs={'country_code': country.code3, 'year': year, 'month': month})
            self.message_user(request, _("Dates will be fetched"))
        else:
            self.message_user(request, _("Wrong form"), messages.ERROR)
        return redirect(reverse('admin:%s_%s_changelist' % (self.model._meta.app_label, self.model._meta.model_name)))


if admin.site.is_registered(Site):
    admin.site.unregister(Site)


admin.site.site_header = "Core Administration"
admin.site.register(models.Contact)
admin.site.register(models.User, UserAdmin)
admin.site.register(models.BankAccount)
admin.site.register(models.Company, CompanyAdmin)
admin.site.register(models.Address)
admin.site.register(models.CompanyRel, BaseAdmin)
admin.site.register(models.CompanyAddress, BaseAdmin)
admin.site.register(models.CompanyLocalization)
admin.site.register(models.CompanyContact, BaseAdmin)
admin.site.register(models.CompanyContactAddress, BaseAdmin)
admin.site.register(models.CompanyContactRelationship, BaseAdmin)
admin.site.register(models.Invoice, BaseAdmin)
admin.site.register(models.InvoiceLine)
admin.site.register(models.Tag, TagAdmin)
admin.site.register(models.Note)
admin.site.register(models.Order)
admin.site.register(models.SiteCompany, BaseAdmin)
admin.site.register(models.VAT)
admin.site.register(models.InvoiceRule)
admin.site.register(models.ExtranetNavigation, ExtranetNavigationAdmin)
admin.site.register(models.Workflow)
admin.site.register(models.WorkflowNode, SuperuserAdmin)
admin.site.register(models.WorkflowObject, SuperuserAdmin)
admin.site.register(models.PublicHoliday, PublicHolidayAdmin)
admin.site.register(Site, SiteAdmin)