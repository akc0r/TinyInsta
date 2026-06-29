from django.urls import path

from posts import views

urlpatterns = [
    # Specific routes first: `saves` / `reposts` must not be captured by the
    # `<post_id>` pattern below (Django matches in order).
    path("posts", views.PostList.as_view()),
    path("posts/reels", views.ReelsFeed.as_view()),
    path("posts/saves", views.Saves.as_view()),
    path("posts/reposts", views.Reposts.as_view()),
    path("posts/reposts/<str:repost_id>", views.Reposts.as_view()),
    path("posts/<str:post_id>", views.PostDetail.as_view()),
    path("posts/<str:post_id>/comments", views.Comments.as_view()),
    path("posts/<str:post_id>/comments/<str:comment_id>", views.CommentDetail.as_view()),
]
