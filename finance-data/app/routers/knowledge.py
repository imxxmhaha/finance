"""知识库检索 API."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Query
from pydantic import BaseModel, Field

from ..dependencies import RequestContext, get_request_context
from ..errors import bad_request
from ..idempotency import idempotent_result, save_idempotent_result
from ..knowledge_service import get_collection_stats, search
from ..response import ok

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["knowledge"])


# ---------------------------------------------------------------------------
# 请求/响应模型
# ---------------------------------------------------------------------------

class KnowledgeSearchRequest(BaseModel):
    """知识库搜索请求."""
    query: str = Field(min_length=1, max_length=500, description="查询文本")
    top_k: int = Field(default=5, ge=1, le=20, description="返回条数")
    source_type: str | None = Field(default=None, description="来源类型过滤: loan/wealth/account/service")


class KnowledgeReindexRequest(BaseModel):
    """重建索引请求."""
    request_no: str


# ---------------------------------------------------------------------------
# 接口
# ---------------------------------------------------------------------------

@router.post("/knowledge/search", summary="知识库检索")
def knowledge_search(
    body: Annotated[KnowledgeSearchRequest, Body(description="搜索请求")],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> dict[str, Any]:
    """混合检索知识库：稠密向量 + BM25 稀疏向量，RRF 融合排序."""
    try:
        results = search(
            query=body.query,
            top_k=body.top_k,
            source_type=body.source_type,
        )
    except Exception as e:
        logger.exception("知识库检索失败")
        raise bad_request("KNOWLEDGE_SEARCH_FAILED", f"检索失败: {e}")

    data = {
        "query": body.query,
        "results": results,
        "total": len(results),
    }
    return ok(data, ctx.request_id)


@router.get("/knowledge/stats", summary="知识库统计")
def knowledge_stats(
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> dict[str, Any]:
    """获取知识库 collection 统计信息."""
    stats = get_collection_stats()
    return ok(stats, ctx.request_id)


@router.post("/knowledge/reindex", summary="重建知识库索引")
def knowledge_reindex(
    body: Annotated[KnowledgeReindexRequest, Body(description="重建请求")],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> dict[str, Any]:
    """清空并重建知识库索引（仅管理员）."""
    cached = idempotent_result(
        ctx.channel_code, "knowledge_reindex", body.request_no, body.model_dump()
    )
    if cached is not None:
        return ok(cached, ctx.request_id)

    from scripts.seed_knowledge import collect_all_chunks
    from ..knowledge_service import connect_milvus, create_collection, drop_collection, insert_chunks

    connect_milvus()
    drop_collection()
    create_collection()

    chunks = collect_all_chunks()
    batch_size = 50
    total = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        count = insert_chunks(batch)
        total += count

    data = {"inserted": total, "status": "completed"}
    save_idempotent_result(
        ctx.channel_code, "knowledge_reindex", body.request_no, body.model_dump(), data
    )
    return ok(data, ctx.request_id)
