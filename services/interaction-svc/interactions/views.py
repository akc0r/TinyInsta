from rest_framework.views import APIView


class Like(APIView):
    def post(self, request, post_id):
        raise NotImplementedError

    def delete(self, request, post_id):
        raise NotImplementedError


class LikeCount(APIView):
    def get(self, request, post_id):
        raise NotImplementedError
