from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from timeline import store


class UserTimeline(APIView):
    # A profile's post list is a public read model: the frontend reads it for
    # any profile, and hometimeline-svc reads it server-to-server (no user JWT)
    # to back-fill a follower's home timeline on follow.
    permission_classes = [AllowAny]

    def get(self, request, author_id):
        cursor = request.query_params.get("cursor")
        with_scores = request.query_params.get("withscores") in ("1", "true")
        try:
            limit = min(int(request.query_params.get("limit", 20)), 100)
        except ValueError:
            limit = 20
        return Response(store.page(str(author_id), cursor, limit, with_scores))
