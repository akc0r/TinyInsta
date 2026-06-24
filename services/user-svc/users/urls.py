from django.urls import path

from users import views

urlpatterns = [
    path("me", views.Me.as_view()),
    path("me/suggestions", views.Suggestions.as_view()),
    path("<uuid:user_id>", views.ProfileDetail.as_view()),
    path("<uuid:user_id>/follow", views.Follow.as_view()),
    path("<uuid:user_id>/followers", views.Followers.as_view()),
    path("<uuid:user_id>/following", views.Following.as_view()),
]
