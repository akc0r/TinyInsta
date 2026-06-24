from channels.middleware import BaseMiddleware


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        # TODO: validate token via tinyinsta.auth_jwt, set scope["user"]
        return await super().__call__(scope, receive, send)
