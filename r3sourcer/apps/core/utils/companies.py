from urllib.parse import urlparse

from django.contrib.sites.shortcuts import get_current_site
from django.contrib.sites.models import Site
from django.core.cache import cache


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


def get_site_url(request=None, user=None):
    domain = get_current_site(request).domain

    if user:
        domain = cache.get('user_site_%s' % str(user.id), domain)

    url_parts = urlparse(domain)

    return '{}://{}'.format(url_parts.scheme or 'https', url_parts.netloc or url_parts.path)


def get_site_master_company(site=None, request=None, user=None, default=True):
    from r3sourcer.apps.core.models import Company

    if isinstance(site, str):
        site = Site.objects.get_by_natural_key(site)
    elif request:
        site = Site.objects.filter(domain=request.get_host()).first()

    if site is None:
        if not default:
            return None

        site = get_current_site(request)

    if user:
        try:
            site = Site.objects.get_by_natural_key(cache.get('user_site_%s' % str(user.id), site.domain))
        except Site.DoesNotExist:
            pass

    site_company = site.site_companies.filter(company__type=Company.COMPANY_TYPES.master).first()

    return site_company and site_company.company
