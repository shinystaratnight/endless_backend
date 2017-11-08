from django.conf.urls import url, include

from r3sourcer.apps.company_settings import views


urlpatterns = [
    url(r'^company_settings/$', views.CompanySettingsView.as_view(), name='company_settings'),
]
