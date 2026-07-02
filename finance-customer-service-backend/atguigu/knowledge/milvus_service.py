"""Milvus + 阿里百炼 Embedding 知识库检索服务 (MilvusClient API)."""

from __future__ import annotations

import asyncio
import os
from typing import Any

# 修复 OpenBLAS 内存分配问题
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import httpx
from pymilvus import MilvusClient

from atguigu.api.logger import logger
from atguigu.conf.config import settings

# 常量
COLLECTION_NAME = "knowledge_chunks"
EMBEDDING_MODEL = "text-embedding-v3"
EMBEDDING_DIM = 1024
EMBEDDING_API_URL = (
    "https://dashscope.aliyuncs.com/api/v1/services/embeddings/"
    "text-embedding/text-embedding"
)

# 全局客户端
_client: MilvusClient | None = None


def _get_client() -> MilvusClient:
    """获取 MilvusClient 单例."""
    global _client
    if _client is None:
        uri = f"http://{settings.milvus_host}:{settings.milvus_port}"
        _client = MilvusClient(uri=uri)
        logger.info(f"Milvus 连接成功: {uri}")
    return _client


# ---------------------------------------------------------------------------
# 百炼 Embedding API
# ---------------------------------------------------------------------------

async def embed_texts(texts: list[str]) -> list[list[float]]:
    """调用百炼 text-embedding-v3 生成稠密向量（异步）."""
    if not settings.dashscope_api_key:
        raise ValueError("DASHSCOPE_API_KEY 未配置")

    headers = {
        "Authorization": f"Bearer {settings.dashscope_api_key}",
        "Content-Type": "application/json",
    }

    all_vectors: list[list[float]] = []
    batch_size = 10

    async with httpx.AsyncClient(timeout=60) as client:
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            payload = {
                "model": EMBEDDING_MODEL,
                "input": {"texts": batch},
                "parameters": {"dimension": EMBEDDING_DIM},
            }

            for attempt in range(3):
                try:
                    resp = await client.post(
                        EMBEDDING_API_URL, json=payload, headers=headers
                    )
                    if resp.status_code != 200:
                        logger.error(f"Embedding API 错误 {resp.status_code}: {resp.text[:300]}")
                    resp.raise_for_status()
                    result = resp.json()
                    embeddings = result["output"]["embeddings"]
                    embeddings.sort(key=lambda e: e["text_index"])
                    all_vectors.extend([e["embedding"] for e in embeddings])
                    break
                except Exception as e:
                    logger.warning(f"Embedding 批次 {i // batch_size} 第 {attempt + 1} 次失败: {e}")
                    if attempt < 2:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        raise

            if i + batch_size < len(texts):
                await asyncio.sleep(0.3)

    return all_vectors


# ---------------------------------------------------------------------------
# 向量检索
# ---------------------------------------------------------------------------

async def search(
    query: str,
    top_k: int = 5,
    source_type: str | None = None,
) -> list[dict[str, Any]]:
    """稠密向量检索 (COSINE)."""
    client = _get_client()

    # 生成查询向量
    vectors = await embed_texts([query])
    dense_vector = vectors[0]

    # 构建过滤表达式
    expr = None
    if source_type:
        expr = f'source_type == "{source_type}"'

    # 在线程池中执行同步的 Milvus 操作
    def _do_search():
        results = client.search(
            collection_name=COLLECTION_NAME,
            data=[dense_vector],
            anns_field="dense_vector",
            limit=top_k,
            output_fields=["chunk_text", "source_file", "source_type", "metadata", "doc_id"],
            search_params={"metric_type": "COSINE", "params": {"nprobe": 16}},
            filter=expr,
        )
        hits = []
        for hit in results[0]:
            entity = hit.get("entity", {})
            hits.append({
                "chunk_text": entity.get("chunk_text"),
                "score": round(hit.get("distance", 0), 4),
                "source_file": entity.get("source_file"),
                "source_type": entity.get("source_type"),
                "doc_id": entity.get("doc_id"),
                "metadata": entity.get("metadata"),
            })
        return hits

    return await asyncio.to_thread(_do_search)


def get_stats() -> dict[str, Any]:
    """获取 collection 统计信息."""
    client = _get_client()
    try:
        stats = client.get_collection_stats(collection_name=COLLECTION_NAME)
        count = int(stats.get("row_count", 0))
        return {"exists": True, "count": count}
    except Exception:
        return {"exists": False, "count": 0}
