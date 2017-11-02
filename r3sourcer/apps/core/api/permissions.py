from dry_rest_permissions.generics import DRYPermissions, DRYPermissionFiltersBase
from rest_framework import permissions

from ..service import factory
from ..utils.companies import get_master_companies, get_closest_companies


class SitePermissions(DRYPermissions):
    def has_permission(self, request, view):
        if not self.global_permissions:
            return True

        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated()
        else:
            return request.user and request.user.is_superuser

    def has_object_permission(self, request, view, obj):
        if not self.object_permissions:
            return True

        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated()
        is_superuser = request.user and request.user.is_superuser
        return is_superuser or self.is_master_related(request.user, obj)

    def is_master_related(self, user, obj):
        return False


class SiteContactPermissions(SitePermissions):
    def has_permission(self, request, view):
        if not self.object_permissions:
            return True

        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated()
        return request.user and request.user.is_staff and request.user.contact.is_master_related()

    def has_object_permission(self, request, view, obj):
        if not self.object_permissions:
            return True

        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated()
        return request.user and request.user.is_staff and self.is_master_related(request.user, obj)

    def is_master_related(self, user, obj):
        master_getter = factory.get_instance('MasterCompanyGetter')
        return user.contact.get_company_contact_by_company(master_getter.get_master_company_for_obj(obj)) is not None


class SiteMasterCompanyFilterBackend(DRYPermissionFiltersBase):
    action_routing = True

    def filter_list_queryset(self, request, queryset, view):
        if request.user.is_superuser:
            return queryset
        master_companies = get_master_companies(request)
        return queryset.filter(site_companies__company__in=master_companies)


class SiteClosestCompanyFilterBackend(DRYPermissionFiltersBase):
    action_routing = True

    def filter_list_queryset(self, request, queryset, view):
        if request.user.is_superuser:
            return queryset

        closest_companies = get_closest_companies(request)
        return queryset.filter(site_companies__company__in=closest_companies)


class SiteRelatedClosestCompanyFilterBackend(DRYPermissionFiltersBase):
    action_routing = True
    queryset_filter = 'site__site_companies__company__in'

    def filter_list_queryset(self, request, queryset, view):
        if request.user.is_superuser:
            return queryset

        if request.user.is_staff and request.user.contact.is_master_related():
            related_companies = get_closest_companies(request)
        else:
            related_companies = get_master_companies(request)
        return queryset.filter(**{self.queryset_filter: related_companies})


class SiteRelatedViaPageCompanyFilterBackend(SiteRelatedClosestCompanyFilterBackend):
    queryset_filter = 'page__site__site_companies__company__in'


class ReadonlyOrIsSuperUser(DRYPermissions):
    """
    Would be used only for superusers.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated()
        return request.user.is_superuser

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class ReadOnly(DRYPermissions):
    """
    Readonly permissions. 
    Would be used for permissions.SAFE_METHODS.
    """

    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
