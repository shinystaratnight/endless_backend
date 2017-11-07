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
