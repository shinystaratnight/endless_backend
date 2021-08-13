from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    return value * arg

@register.filter
def index(indexable, i):
    return indexable[i]

@register.filter
def translation(value, user):
    print(user.contact.get_closest_company())
    company_language = user.contact.get_closest_company().get_default_lanuage()
    return value.translation(company_language)
