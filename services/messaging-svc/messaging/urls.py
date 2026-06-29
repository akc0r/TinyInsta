from django.urls import path

from messaging import views

urlpatterns = [
    path("conversations", views.Conversations.as_view()),
    path("conversations/start", views.StartConversation.as_view()),
    path("conversations/<str:conversation_id>/messages", views.Messages.as_view()),
]
