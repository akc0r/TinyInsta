from django.urls import path

from realtime import views

urlpatterns = [
    path("notifications", views.Notifications.as_view()),
    path("notifications/<uuid:notification_id>/read", views.NotificationRead.as_view()),
]
