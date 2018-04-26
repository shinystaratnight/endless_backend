from django.conf import settings
from django.conf.urls import url, include
from django.conf.urls.static import static
from django.contrib import admin
from drf_auto_endpoint.router import router

from r3sourcer.apps.logger.admin import admin_logger
from r3sourcer.apps.logger.api.viewsets import journal_list, journal_detail
from r3sourcer.apps.logger.main import autodiscover

from r3sourcer.apps.core.api.viewsets import AppsList, ModelsList, FunctionsList
from r3sourcer.apps.core.views import FormView, RegisterFormView
from r3sourcer.apps.core.forms import CoreAdminAuthenticationForm

autodiscover()

router.registry.append(('apps', AppsList, 'apps'))
router.registry.append(('models', ModelsList, 'models'))
router.registry.append(('functions', FunctionsList, 'functions'))

admin.site.login_form = CoreAdminAuthenticationForm

api_versions = '(?P<version>v2)'

_urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^form-builds/(?P<company>.+)/(?P<pk>.+)/$', FormView.as_view(), name='form-builder-view'),
    url(r'^register/$', RegisterFormView.as_view(), name='form-builder-register'),
    url(r'^rosetta/', include('rosetta.urls')),
    url(r'^twilio/', include('r3sourcer.apps.twilio.urls', namespace='twilio')),
    url(r'^sms_interface/api/', include('r3sourcer.apps.sms_interface.urls', namespace='sms_interface')),
    url(r'^myob/', include('r3sourcer.apps.myob.urls', namespace='myob')),
    url(r'^admin/', admin_logger.urls),
    url(r'^api/{}/journal/(?P<app_path>.+)/(?P<model>.+)/(?P<pk>\d+?)/'.format(api_versions), journal_detail),
    url(r'^api/{}/journal/(?P<app_path>.+)/(?P<model>.+)/'.format(api_versions), journal_list),
    url(r'^api/{}/'.format(api_versions), include('r3sourcer.apps.company_settings.urls')),
    url(r'^api/{}/'.format(api_versions), include('r3sourcer.apps.core.urls')),
    url(r'^api/{}/'.format(api_versions), include('r3sourcer.apps.hr.urls')),
    url(r'^api/{}/'.format(api_versions), include('r3sourcer.apps.skills.urls')),
    url(r'^api/{}/'.format(api_versions), include('r3sourcer.apps.pricing.urls')),
    url(r'^api/{}/'.format(api_versions), include(router.urls, namespace='api')),
    url(r'^', include('filer.urls', namespace='filer')),
    url(r'^admin/', include('loginas.urls')),
]

urlpatterns = [
    url('^{}'.format(settings.DJANGO_STUFF_URL_PREFIX), include(_urlpatterns))
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
