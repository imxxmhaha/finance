from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.engine.builder import build_dialogue_engine
from atguigu.engine.dialogue_engine import DialogueEngine
from atguigu.infrastructure.database import get_db_pool
from atguigu.repository.dialogue_state_repository import DialogueStateRepository
from atguigu.service.dialogue_service import DialogueService

# 全局单例
_dialogue_engine: DialogueEngine | None = None


def get_dialogue_engine() -> DialogueEngine:
    """获取 DialogueEngine（应用级单例）"""
    global _dialogue_engine
    if _dialogue_engine is None:
        _dialogue_engine = build_dialogue_engine()
    return _dialogue_engine


async def get_async_session() -> AsyncSession:
    """获取数据库会话（请求级生命周期）"""
    pool = get_db_pool()
    async with pool.get_session() as session:
        yield session


def get_dialogue_state_repository(
        session: AsyncSession = Depends(get_async_session)
) -> DialogueStateRepository:
    """获取 DialogueStateRepository（请求级）"""
    return DialogueStateRepository(session)


def get_dialogue_service(
        repo: DialogueStateRepository = Depends(get_dialogue_state_repository),
        engine: DialogueEngine = Depends(get_dialogue_engine)
) -> DialogueService:
    """获取 DialogueService（请求级）"""
    return DialogueService(
        dialogue_state_repository=repo,
        dialogue_engine=engine
    )
