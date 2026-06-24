from django.urls import path

from media import views

urlpatterns = [
    path("upload-url", views.UploadUrl.as_view()),
    path("", views.MediaList.as_view()),
    path("<uuid:media_id>", views.MediaDetail.as_view()),
]
