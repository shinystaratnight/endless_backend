from django.db.models import Q
from filer.models import Folder


class MasterCompanyLookupMixin(object):
    """
    Mixin for providing access only for master_company linked models
    master_company_lookup_string must be set up or get_master_company method must be overridden for complicated cases
    """
    master_company_lookup_string = 'master_company'

    @classmethod
    def get_master_company_lookup(cls, master_company):
        if cls.master_company_lookup_string:
            return Q(**{cls.master_company_lookup_string: master_company})
        raise NotImplementedError

    def get_master_company(self):
        """
        Get list of master companies
        """
        raise NotImplementedError


class CompanyLookupMixin(object):
    """
    Mixin for providing access only for company linked models
    closest_company_lookup_string must be set up or get_closest_company method must be overridden for complicated cases
    """
    closest_company_lookup_string = 'company'

    @classmethod
    def get_closest_company_lookup(cls, company):
        if cls.closest_company_lookup_string:
            return Q(**{cls.closest_company_lookup_string: company})
        raise NotImplementedError

    def get_closest_company(self):
        """
        Get closest company
        """
        raise NotImplementedError


class CategoryFolderMixin(object):
    def save(self, *args, **kwargs):
        if self._state.adding:
            # create folder for model by it's verbose name
            parent_folder, created = Folder.objects.get_or_create(name=self._meta.verbose_name_plural)
            self.files = Folder.objects.create(name=self.id, parent=parent_folder)
        super().save(*args, **kwargs)
