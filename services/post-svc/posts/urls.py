from django.urls import path

from posts import views

urlpatterns = [
    path("", views.PostList.as_view()),
    path("<str:post_id>", views.PostDetail.as_view()),
    path("<str:post_id>/comments", views.Comments.as_view()),
]
