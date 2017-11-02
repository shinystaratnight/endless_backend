from django.conf.urls import url
from .views import TemplateCompileView, ContentTypeListView, TemplateSMSMessageListView

urlpatterns = [
    url('^templates/$', TemplateSMSMessageListView.as_view(), name='templates'),
    url('^templates/compile/$', TemplateCompileView.as_view(), name='template-compile'),
    url('^find/contenttypes/$', ContentTypeListView.as_view(), name='find-contenttypes')
]