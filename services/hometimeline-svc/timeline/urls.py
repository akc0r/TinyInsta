from django.urls import path

from timeline import views

urlpatterns = [
    path("home", views.HomeTimeline.as_view()),
]
