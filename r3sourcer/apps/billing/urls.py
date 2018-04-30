from django.conf.urls import url

from r3sourcer.apps.billing import views


urlpatterns = [
    url(r'^$', views.billing_index, name='billing_index'),
]
