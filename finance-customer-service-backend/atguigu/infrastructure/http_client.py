import asyncio
import uuid
from typing import Optional

from httpx import AsyncClient, Limits, Timeout, Request

from atguigu.api.logger import logger, request_context_var
from atguigu.conf.config import settings


# ============================================================
# 请求头中间件（event hook）
# ============================================================

async def _inject_common_headers(request: Request):
    """
    httpx event hook：在每个请求发出前自动注入中台规范的公共请求头。

    中台接口规范要求的 4 个请求头：
    - Authorization: Bearer <客户号/员工编号/系统服务账号>
    - X-Channel-Code: 渠道编码
    - X-Operator-No: 操作人编号（审计用）
    - X-Request-Id: 请求追踪号（链路排查用）
    """
    # 从请求上下文获取 request_id 和 user_id
    try:
        ctx = request_context_var.get()
        request_id = ctx.get("request_id", "")
        user_id = ctx.get("user_id", "")
    except Exception:
        request_id = ""
        user_id = ""

    # --- Authorization ---
    # Bearer token：中台验证逻辑——先查 customer 表，再查 dim_employee 表。
    # 优先使用请求上下文中的 user_id（客户号），无上下文时使用员工号（客服机器人身份）
    token = user_id if user_id and user_id != "-" else settings.api_operator_no
    request.headers["Authorization"] = f"Bearer {token}"

    # --- X-Channel-Code ---
    request.headers["X-Channel-Code"] = settings.api_channel_code

    # --- X-Operator-No ---
    request.headers["X-Operator-No"] = settings.api_operator_no

    # --- X-Request-Id ---
    if request_id and request_id != "-":
        request.headers["X-Request-Id"] = request_id
    else:
        request.headers["X-Request-Id"] = str(uuid.uuid4())[:16]

    logger.debug(
        f"[HTTP] {request.method} {request.url} | "
        f"Authorization=Bearer {token} | "
        f"X-Channel-Code={settings.api_channel_code} | "
        f"X-Operator-No={settings.api_operator_no}"
    )


class HTTPClientPool:
    """HTTP 客户端连接池管理器（单例模式）"""

    _instance: Optional['HTTPClientPool'] = None
    _client: Optional[AsyncClient] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(
        self,
        max_connections: int = 50,
        max_keepalive_connections: int = 20,
        connect_timeout: float = 5.0,
        read_timeout: float = 10.0,
        write_timeout: float = 10.0,
        pool_timeout: float = 5.0
    ):
        """初始化 HTTP 客户端连接池"""
        if self._client is None:
            limits = Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive_connections
            )
            timeout_config = Timeout(
                connect=connect_timeout,
                read=read_timeout,
                write=write_timeout,
                pool=pool_timeout
            )
            self._client = AsyncClient(
                limits=limits,
                timeout=timeout_config,
                follow_redirects=True,
                event_hooks={"request": [_inject_common_headers]},
            )

    @property
    def client(self) -> AsyncClient:
        """获取 HTTP 客户端实例"""
        if self._client is None:
            raise RuntimeError("HTTPClientPool 未初始化，请先调用 initialize()")
        return self._client

    async def close(self):
        """关闭连接池"""
        if self._client:
            await self._client.aclose()
            self._client = None


def get_http_client() -> AsyncClient:
    """获取全局 HTTP 客户端（便捷函数）"""
    pool = HTTPClientPool()
    return pool.client


def init_http_pool(
    max_connections: int = 50,
    max_keepalive_connections: int = 20,
    connect_timeout: float = 5.0,
    read_timeout: float = 10.0,
    write_timeout: float = 10.0,
    pool_timeout: float = 5.0
):
    """初始化全局 HTTP 连接池"""
    pool = HTTPClientPool()
    pool.initialize(
        max_connections=max_connections,
        max_keepalive_connections=max_keepalive_connections,
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
        write_timeout=write_timeout,
        pool_timeout=pool_timeout
    )


async def close_http_pool():
    """关闭全局 HTTP 连接池"""
    pool = HTTPClientPool()
    await pool.close()
