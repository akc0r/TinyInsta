from rest_framework.views import APIView


class StoryList(APIView):
    def post(self, request):
        raise NotImplementedError


class StoryFeed(APIView):
    def get(self, request):
        raise NotImplementedError


class StoryView(APIView):
    def post(self, request, story_id):
        raise NotImplementedError


class StoryViews(APIView):
    def get(self, request, story_id):
        raise NotImplementedError
