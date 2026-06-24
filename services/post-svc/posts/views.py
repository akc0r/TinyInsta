from rest_framework.views import APIView


class PostList(APIView):
    def post(self, request):
        raise NotImplementedError


class PostDetail(APIView):
    def get(self, request, post_id):
        raise NotImplementedError

    def delete(self, request, post_id):
        raise NotImplementedError


class Comments(APIView):
    def get(self, request, post_id):
        raise NotImplementedError

    def post(self, request, post_id):
        raise NotImplementedError
