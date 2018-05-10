from django.conf.urls import url

from r3sourcer.apps.billing import views


urlpatterns = [
    url(r'^subscription/list/$', views.SubscriptionListView.as_view(), name='subscription_list'),
    url(r'^subscription/create/$', views.SubscriptionCreateView.as_view(), name='subscription_create'),
    url(r'^subscription/status/$', views.SubscriptionStatusView.as_view(), name='subscription_status'),
    url(r'^stripe_customer/$', views.StripeCustomerCreateView.as_view(), name='stripe_customer_create'),
]
