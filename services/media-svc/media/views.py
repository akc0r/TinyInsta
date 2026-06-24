from rest_framework.views import APIView


class UploadUrl(APIView):
    def post(self, request):
        raise NotImplementedError


class MediaList(APIView):
    def post(self, request):
        raise NotImplementedError


class MediaDetail(APIView):
    def get(self, request, media_id):
        raise NotImplementedError
