from django.conf.urls import url

from r3sourcer.apps.billing import views


urlpatterns = [
    url(r'^$', views.billing_index, name='billing_index'),
    url(r'^callback/$', views.billing_callback, name='billing_callback'),
    url(r'^plans/$', views.PlanListView.as_view(), name='plan_list'),
    url(r'^plans/create/$', views.PlanCreateView.as_view(), name='plan_create'),
    url(r'^stripe_customer/$', views.StripeCustomerCreateView.as_view(), name='stripe_customer_create'),
]
