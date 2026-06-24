from django.urls import path

from search import views

urlpatterns = [
    path("search", views.Search.as_view()),
    path("hashtags/<str:tag>", views.Hashtag.as_view()),
    path("explore", views.Explore.as_view()),
]
