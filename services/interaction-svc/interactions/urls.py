from django.urls import path

from interactions import views

urlpatterns = [
    path("posts/<uuid:post_id>/like", views.Like.as_view()),
    path("posts/<uuid:post_id>/likes", views.LikeCount.as_view()),
]
