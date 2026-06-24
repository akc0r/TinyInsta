from rest_framework.views import APIView


class ProfileDetail(APIView):
    def get(self, request, user_id):
        raise NotImplementedError


class Me(APIView):
    def patch(self, request):
        raise NotImplementedError


class Follow(APIView):
    def post(self, request, user_id):
        raise NotImplementedError

    def delete(self, request, user_id):
        raise NotImplementedError


class Followers(APIView):
    def get(self, request, user_id):
        raise NotImplementedError


class Following(APIView):
    def get(self, request, user_id):
        raise NotImplementedError


class Suggestions(APIView):
    def get(self, request):
        raise NotImplementedError
