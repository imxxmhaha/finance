import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from atguigu.api.logger import set_request_context, reset_request_context


class RequestContextMiddleware(BaseHTTPMiddleware):
    """请求上下文中间件：为每个请求注入 request_id 和 user_id 到日志"""

    async def dispatch(self, request: Request, call_next):
        # 从请求头或查询参数获取 request_id
        request_id = request.headers.get("X-Request-Id", str(uuid.uuid4())[:8])
        # 从请求头或 sender_id 获取 user_id
        user_id = request.headers.get("X-User-Id", "-")

        # 尝试从请求体中解析 sender_id
        if user_id == "-":
            try:
                body = await request.body()
                if body:
                    import json
                    data = json.loads(body)
                    user_id = data.get("sender_id", "-")
            except Exception:
                pass

        # 设置请求上下文
        set_request_context(request_id=request_id, user_id=user_id)

        try:
            response = await call_next(request)
            response.headers["X-Request-Id"] = request_id
            return response
        finally:
            reset_request_context()
