from rest_framework.views import APIView


class Notifications(APIView):
    def get(self, request):
        raise NotImplementedError


class NotificationRead(APIView):
    def post(self, request, notification_id):
        raise NotImplementedError
