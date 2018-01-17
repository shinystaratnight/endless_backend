from django.conf.urls import url

from r3sourcer.apps.hr.api import views


urlpatterns = [
    url(r'^distances/', views.CandidateDistanceView.as_view(), name='get_candidate_distance'),
]
