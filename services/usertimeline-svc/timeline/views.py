from rest_framework.response import Response
from rest_framework.views import APIView

from timeline import store


class UserTimeline(APIView):
    def get(self, request, author_id):
        cursor = request.query_params.get("cursor")
        try:
            limit = min(int(request.query_params.get("limit", 20)), 100)
        except ValueError:
            limit = 20
        return Response(store.page(str(author_id), cursor, limit))
