from django.urls import path

from media import views

urlpatterns = [
    path("media/upload-url", views.UploadUrl.as_view()),
    path("media", views.MediaList.as_view()),
    path("media/<uuid:media_id>", views.MediaDetail.as_view()),
]
