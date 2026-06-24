from django.urls import path

from timeline import views

urlpatterns = [
    path("<uuid:author_id>", views.UserTimeline.as_view()),
]
