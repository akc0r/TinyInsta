from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from realtime.models import Notification


def _serialize(note: Notification) -> dict:
    return {
        "id": str(note.id),
        "notification_type": note.type,
        "payload": note.payload,
        "read": note.read,
        "created_at": note.created_at.isoformat(),
    }


class Notifications(APIView):
    def get(self, request):
        uid = str(request.user.user_id)
        qs = Notification.objects.filter(user_id=uid)[:50]
        unread = Notification.objects.filter(user_id=uid, read=False).count()
        return Response({"items": [_serialize(n) for n in qs], "unread": unread})


class NotificationRead(APIView):
    def post(self, request, notification_id):
        uid = str(request.user.user_id)
        updated = Notification.objects.filter(id=notification_id, user_id=uid).update(
            read=True
        )
        if updated == 0:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
