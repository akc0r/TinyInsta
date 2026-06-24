from rest_framework.views import APIView


class Search(APIView):
    def get(self, request):
        raise NotImplementedError


class Hashtag(APIView):
    def get(self, request, tag):
        raise NotImplementedError


class Explore(APIView):
    def get(self, request):
        raise NotImplementedError
