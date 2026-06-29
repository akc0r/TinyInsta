from django.urls import path

from ranking import views

urlpatterns = [
    path("score", views.Score.as_view()),
]
