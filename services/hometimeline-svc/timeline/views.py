from rest_framework.views import APIView


class HomeTimeline(APIView):
    def get(self, request):
        raise NotImplementedError
