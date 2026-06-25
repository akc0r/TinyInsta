from django.urls import path

from stories import views

urlpatterns = [
    path("stories", views.StoryList.as_view()),
    path("stories/feed", views.StoryFeed.as_view()),
    path("stories/<uuid:story_id>/view", views.StoryView.as_view()),
    path("stories/<uuid:story_id>/views", views.StoryViews.as_view()),
]
