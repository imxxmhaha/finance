"""知识库检索 API — 直连 Milvus."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field
from atguigu.api.logger import logger

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


class KnowledgeSearchRequest(BaseModel):
    """知识库搜索请求."""
    query: str = Field(min_length=1, max_length=500, description="查询文本")
    top_k: int = Field(default=5, ge=1, le=20, description="返回条数")
    source_type: str | None = Field(default=None, description="来源类型过滤: loan/wealth/account/service")


@router.post("/search")
async def knowledge_search(body: KnowledgeSearchRequest) -> dict[str, Any]:
    """知识库混合检索：稠密向量 + BM25 稀疏向量，RRF 融合排序."""
    from atguigu.knowledge.milvus_service import search

    try:
        results = await search(
            query=body.query,
            top_k=body.top_k,
            source_type=body.source_type,
        )
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "query": body.query,
                "results": results,
                "total": len(results),
            },
        }
    except Exception as e:
        logger.error(f"知识库检索失败: {e}")
        return {"code": "KNOWLEDGE_SEARCH_FAILED", "message": str(e), "data": None}


@router.get("/stats")
async def knowledge_stats() -> dict[str, Any]:
    """知识库统计信息."""
    from atguigu.knowledge.milvus_service import get_stats

    try:
        stats = get_stats()
        return {"code": 0, "message": "ok", "data": stats}
    except Exception as e:
        logger.error(f"知识库统计失败: {e}")
        return {"code": "KNOWLEDGE_STATS_FAILED", "message": str(e), "data": None}
