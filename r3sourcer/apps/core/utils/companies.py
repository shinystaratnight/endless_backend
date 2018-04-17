from urllib.parse import urlparse, urljoin

from django.contrib.sites.shortcuts import get_current_site
from django.contrib.sites.models import Site

from r3sourcer.apps.core.models import Company


def get_closest_companies(request):
    """
    Gets list of the companies to which contact is straightly related
    """
    contact = request.user.contact
    closest_companies = list()
    if contact.is_company_contact():
        for cc in contact.company_contact.all():
            for rel in cc.relationships.all():
                closest_company = rel.get_closest_company()
                if closest_company:
                    closest_companies.append(rel.get_closest_company())
    return closest_companies


def get_master_companies(request):
    """
    Gets list of the master companies to which contact is related via other companies or itself
    """
    return get_master_companies_by_contact(request.user.contact)


def get_master_companies_by_contact(contact):
    master_companies = list()
    if contact.is_company_contact():
        for cc in contact.company_contact.all():
            master_companies.extend(cc.get_master_company())
    return master_companies


def get_site_url(request=None):
    site = get_current_site(request)
    url_parts = urlparse(site.domain)

    return '{}://{}'.format(url_parts.scheme or 'https', url_parts.netloc)


def get_site_master_company(site=None, request=None):
    if isinstance(site, str):
        site = Site.objects.get_by_natural_key(site)
    elif site is None:
        site = get_current_site(request)

    site_company = site.site_companies.filter(company__type=Company.COMPANY_TYPES.master).first()

    return site_company and site_company.company
