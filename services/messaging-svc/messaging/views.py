import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from tinyinsta.bus import Producer
from tinyinsta.events import types

from messaging import cql

logger = logging.getLogger(__name__)

_producer = Producer()


class Conversations(APIView):
    """List the requesting user's conversations (inbox), most-recent first."""

    def get(self, request):
        user_id = str(request.user.user_id)
        return Response({"items": cql.list_conversations(user_id)})


class Messages(APIView):
    """Read a conversation's messages, or send a message to a peer."""

    def get(self, request, conversation_id):
        user_id = str(request.user.user_id)
        # A 1:1 conversation id is "a:b" (sorted); only its members may read it.
        if user_id not in conversation_id.split(":"):
            return Response(status=status.HTTP_403_FORBIDDEN)
        cursor = request.query_params.get("cursor")
        try:
            limit = min(int(request.query_params.get("limit", 30)), 100)
        except ValueError:
            limit = 30
        return Response(cql.list_messages(conversation_id, cursor, limit))

    def post(self, request, conversation_id):
        user_id = str(request.user.user_id)
        if user_id not in conversation_id.split(":"):
            return Response(status=status.HTTP_403_FORBIDDEN)
        body = (request.data.get("body") or "").strip()
        if not body:
            return Response({"detail": "body is required."}, status=status.HTTP_400_BAD_REQUEST)
        # Recipient is the other member of the conversation id.
        members = conversation_id.split(":")
        recipient_id = members[0] if members[1] == user_id else members[1]

        msg = cql.send_message(user_id, recipient_id, body)

        # Live delivery is handled by realtime-svc (the WebSocket hub) consuming
        # message.sent — messaging-svc owns persistence, not the socket fan-out.
        try:
            _producer.publish(
                types.MESSAGE_SENT,
                {
                    "message_id": msg["message_id"],
                    "conversation_id": msg["conversation_id"],
                    "sender_id": user_id,
                    "recipient_id": recipient_id,
                    "body": body,
                    "created_at": msg["created_at"],
                },
                key=msg["conversation_id"],  # per-conversation ordering
            )
            _producer.flush()
        except Exception:  # noqa: BLE001 — a bus outage must not fail the send
            logger.warning("failed to publish message.sent", exc_info=True)

        return Response(msg, status=status.HTTP_201_CREATED)


class StartConversation(APIView):
    """Resolve (or create) the conversation id for a peer, then send via Messages."""

    def post(self, request):
        user_id = str(request.user.user_id)
        peer_id = request.data.get("peer_id")
        if not peer_id:
            return Response({"detail": "peer_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"conversation_id": cql.conversation_id_for(user_id, str(peer_id))})
