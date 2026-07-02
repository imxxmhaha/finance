"""
数据库连接池管理器（线程安全单例模式）
支持 SQLAlchemy 异步引擎和会话管理
"""
import os
import threading
from typing import Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.pool import AsyncAdaptedQueuePool
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 线程锁
_db_lock = threading.Lock()


class DatabasePool:
    """数据库连接池管理器（单例模式）"""

    _instance: Optional['DatabasePool'] = None
    _engine: Optional[AsyncEngine] = None
    _session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(
        self,
        url: Optional[str] = None,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 1800,
        pool_pre_ping: bool = True,
        echo: bool = False
    ):
        """初始化数据库连接池"""
        if self._engine is None:
            db_url = url or os.getenv(
                "DATABASE_URL",
                "mysql+aiomysql://root:root@localhost:3306/finance-bot-service"
            )
            self._engine = create_async_engine(
                url=db_url,
                poolclass=AsyncAdaptedQueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout,
                pool_recycle=pool_recycle,
                pool_pre_ping=pool_pre_ping,
                echo=echo
            )
            self._session_factory = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

    @property
    def engine(self) -> AsyncEngine:
        """获取数据库引擎"""
        if self._engine is None:
            raise RuntimeError("DatabasePool 未初始化，请先调用 initialize()")
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """获取会话工厂"""
        if self._session_factory is None:
            raise RuntimeError("DatabasePool 未初始化，请先调用 initialize()")
        return self._session_factory

    @asynccontextmanager
    async def get_session(self):
        """获取数据库会话（上下文管理器）"""
        if self._session_factory is None:
            raise RuntimeError("DatabasePool 未初始化，请先调用 initialize()")
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def close(self):
        """关闭连接池"""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None


# 全局实例
_db_pool: Optional[DatabasePool] = None


def get_db_pool() -> DatabasePool:
    """获取全局数据库连接池（线程安全，双重检查锁定）"""
    global _db_pool
    if _db_pool is None:
        with _db_lock:
            if _db_pool is None:
                _db_pool = DatabasePool()
    return _db_pool


def init_db_pool(
    url: Optional[str] = None,
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_timeout: int = 30,
    pool_recycle: int = 1800,
    pool_pre_ping: bool = True,
    echo: bool = False
):
    """初始化全局数据库连接池"""
    pool = get_db_pool()
    pool.initialize(
        url=url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        pool_pre_ping=pool_pre_ping,
        echo=echo
    )


async def close_db_pool():
    """关闭全局数据库连接池"""
    global _db_pool
    if _db_pool:
        await _db_pool.close()
        _db_pool = None


@asynccontextmanager
async def get_db_session():
    """获取数据库会话（便捷函数）"""
    pool = get_db_pool()
    async with pool.get_session() as session:
        yield session
