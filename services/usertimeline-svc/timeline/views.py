from rest_framework.views import APIView


class UserTimeline(APIView):
    def get(self, request, author_id):
        raise NotImplementedError
