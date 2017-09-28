from django.conf import settings
from django.conf.urls import url, include
from django.conf.urls.static import static
from django.contrib import admin
from drf_auto_endpoint.router import router
from rest_framework_swagger.views import get_swagger_view

from endless_core.api.viewsets import AppsList, ModelsList, FunctionsList
from endless_core.views import FormView
from endless_core.forms import CoreAdminAuthenticationForm
from endless_logger.admin import admin_logger
from endless_logger.api.viewsets import journal_list, journal_detail
from endless_logger.main import autodiscover

autodiscover()

router.registry.append(('apps', AppsList, 'apps'))
router.registry.append(('models', ModelsList, 'models'))
router.registry.append(('functions', FunctionsList, 'functions'))

admin.site.login_form = CoreAdminAuthenticationForm

schema_view = get_swagger_view(title='Pastebin API')

api_versions = '(?P<version>v2)'

_urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^form-builds/(?P<pk>.+)/', FormView.as_view(), name='form-builder-view'),
    url(r'^rosetta/', include('rosetta.urls')),
    url(r'^twilio/', include('endless_twilio.urls', namespace='twilio')),
    url(r'^sms_interface/api/', include('endless_sms_interface.urls', namespace='sms_interface')),
    url(r'^api/swagger/$', schema_view),
    url(r'^admin/', admin_logger.urls),
    url(r'^api/{}/journal/(?P<app_path>.+)/(?P<model>.+)/(?P<pk>\d+?)/'.format(api_versions), journal_detail),
    url(r'^api/{}/journal/(?P<app_path>.+)/(?P<model>.+)/'.format(api_versions), journal_list),
    url(r'^api/{}/'.format(api_versions), include(router.urls, namespace='api')),
    url(r'^', include('filer.urls', namespace='filer')),
    url(r'^admin/', include('loginas.urls')),
    url(r'^', include('cms.urls'))
]

urlpatterns = [
    url('^{}'.format(settings.DJANGO_STUFF_URL_PREFIX), include(_urlpatterns))
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
