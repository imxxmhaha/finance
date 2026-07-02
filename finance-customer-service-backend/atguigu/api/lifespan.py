"""
应用生命周期管理
负责初始化和清理应用资源（连接池等）
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from atguigu.infrastructure.database import init_db_pool, close_db_pool
from atguigu.infrastructure.http_client import init_http_pool, close_http_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理（替代已废弃的 @app.on_event）"""
    # 启动时初始化 HTTP 连接池（内部服务调用优化配置）
    try:
        init_http_pool(
            max_connections=50,
            max_keepalive_connections=20,
            connect_timeout=5.0,
            read_timeout=10.0,
            write_timeout=10.0,
            pool_timeout=5.0
        )
        print("[OK] HTTP connection pool initialized")
    except Exception as e:
        print(f"[WARN] HTTP pool init failed: {e}")

    # 启动时初始化数据库连接池（可选，失败不影响启动）
    try:
        init_db_pool(
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=1800,
            pool_pre_ping=True,
            echo=False
        )
        print("[OK] Database connection pool initialized")
    except Exception as e:
        print(f"[WARN] Database pool init failed: {e}")
        print("[WARN] Database features will be unavailable")

    yield  # 应用运行期间

    # 关闭时清理资源
    try:
        await close_http_pool()
        print("[OK] HTTP connection pool closed")
    except Exception as e:
        print(f"[WARN] HTTP pool close failed: {e}")

    try:
        await close_db_pool()
        print("[OK] Database connection pool closed")
    except Exception as e:
        print(f"[WARN] Database pool close failed: {e}")
