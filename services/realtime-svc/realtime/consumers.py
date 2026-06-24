from channels.generic.websocket import AsyncJsonWebsocketConsumer


class RealtimeConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        # TODO: join group user:{user_id} before accept
        await self.accept()

    async def disconnect(self, code):
        # TODO: leave joined groups
        pass

    async def receive_json(self, content, **kwargs):
        # TODO: handle subscribe/unsubscribe
        pass

    async def post_liked(self, event):
        await self.send_json(event["data"])

    async def notification(self, event):
        await self.send_json(event["data"])
