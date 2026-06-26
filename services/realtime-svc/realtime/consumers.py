from channels.generic.websocket import AsyncJsonWebsocketConsumer


# Channel-layer group names allow only [a-zA-Z0-9-_.]; UUIDs (with hyphens) fit,
# so we namespace with a dot rather than the usual colon.
def user_group(user_id: str) -> str:
    return f"user.{user_id}"


def post_group(post_id: str) -> str:
    return f"post.{post_id}"


class RealtimeConsumer(AsyncJsonWebsocketConsumer):
    """Per-connection gateway.

    On connect the socket joins its own ``user.{id}`` group (notifications). It
    can additionally subscribe to ``post.{id}`` groups for the posts currently on
    screen, to receive live like/comment counters.
    """

    async def connect(self):
        user = self.scope.get("user")
        if user is None or not getattr(user, "user_id", None):
            await self.close(code=4401)  # unauthenticated handshake
            return
        self.user_id = str(user.user_id)
        self._groups = {user_group(self.user_id)}
        await self.channel_layer.group_add(user_group(self.user_id), self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        for group in getattr(self, "_groups", set()):
            await self.channel_layer.group_discard(group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        action = content.get("action")
        post_id = content.get("post_id")
        if not post_id:
            return
        if action == "subscribe":
            group = post_group(str(post_id))
            self._groups.add(group)
            await self.channel_layer.group_add(group, self.channel_name)
        elif action == "unsubscribe":
            group = post_group(str(post_id))
            self._groups.discard(group)
            await self.channel_layer.group_discard(group, self.channel_name)

    # --- channel-layer handlers (type "post.liked"/"post.commented" → these) ---
    async def post_liked(self, event):
        await self.send_json({"type": "post.liked", **event["data"]})

    async def post_commented(self, event):
        await self.send_json({"type": "post.commented", **event["data"]})

    async def notification(self, event):
        await self.send_json({"type": "notification", **event["data"]})
