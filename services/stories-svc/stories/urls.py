from django.urls import path

from stories import views

urlpatterns = [
    path("", views.StoryList.as_view()),
    path("feed", views.StoryFeed.as_view()),
    path("<uuid:story_id>/view", views.StoryView.as_view()),
    path("<uuid:story_id>/views", views.StoryViews.as_view()),
]
