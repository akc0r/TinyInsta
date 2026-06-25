from django.urls import path

from posts import views

urlpatterns = [
    path("posts", views.PostList.as_view()),
    path("posts/<str:post_id>", views.PostDetail.as_view()),
    path("posts/<str:post_id>/comments", views.Comments.as_view()),
]
