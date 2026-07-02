"""Milvus + 阿里百炼 Embedding 知识库服务."""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

# 修复 OpenBLAS 内存分配问题
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import httpx
from pymilvus import (
    AnnSearchRequest,
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    Function,
    FunctionType,
    MilvusClient,
    RRFRanker,
    connections,
    utility,
)

from .config import DASHSCOPE_API_KEY, MILVUS_HOST, MILVUS_PORT

logger = logging.getLogger(__name__)

# 常量
COLLECTION_NAME = "knowledge_chunks"
EMBEDDING_MODEL = "text-embedding-v3"
EMBEDDING_DIM = 1024
EMBEDDING_API_URL = (
    "https://dashscope.aliyuncs.com/api/v1/services/embeddings/"
    "text-embedding/text-embedding"
)
BM25_FUNCTION_NAME = "bm25_fn"


# ---------------------------------------------------------------------------
# Milvus 连接
# ---------------------------------------------------------------------------

def connect_milvus() -> None:
    """建立 Milvus 连接（幂等）."""
    try:
        connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT)
        logger.info("Milvus 连接成功: %s:%s", MILVUS_HOST, MILVUS_PORT)
    except Exception:
        logger.exception("Milvus 连接失败")
        raise


def get_client() -> MilvusClient:
    """获取 MilvusClient 实例."""
    return MilvusClient(host=MILVUS_HOST, port=MILVUS_PORT)


# ---------------------------------------------------------------------------
# Collection 管理
# ---------------------------------------------------------------------------

def create_collection() -> None:
    """创建 knowledge_chunks collection（含 BM25 稀疏向量函数）."""
    if utility.has_collection(COLLECTION_NAME):
        logger.info("Collection '%s' 已存在，跳过创建", COLLECTION_NAME)
        return

    fields = [
        FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
        FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="source_file", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="source_type", dtype=DataType.VARCHAR, max_length=32),
        FieldSchema(name="chunk_text", dtype=DataType.VARCHAR, max_length=4096, enable_analyzer=True),
        FieldSchema(name="metadata", dtype=DataType.JSON),
        FieldSchema(
            name="dense_vector",
            dtype=DataType.FLOAT_VECTOR,
            dim=EMBEDDING_DIM,
        ),
        FieldSchema(
            name="sparse_vector",
            dtype=DataType.SPARSE_FLOAT_VECTOR,
        ),
        FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=32),
    ]

    schema = CollectionSchema(fields=fields, description="金融知识库切片")

    # 添加 BM25 稀疏向量函数 — 从 chunk_text 自动生成 sparse_vector
    bm25_function = Function(
        name=BM25_FUNCTION_NAME,
        function_type=FunctionType.BM25,
        input_field_names=["chunk_text"],
        output_field_names=["sparse_vector"],
    )
    schema.add_function(bm25_function)

    collection = Collection(name=COLLECTION_NAME, schema=schema)

    # 稠密向量索引 — IVF_FLAT
    collection.create_index(
        field_name="dense_vector",
        index_params={
            "index_type": "IVF_FLAT",
            "metric_type": "COSINE",
            "params": {"nlist": 128},
        },
    )

    # 稀疏向量索引 — BM25
    collection.create_index(
        field_name="sparse_vector",
        index_params={
            "index_type": "AUTOINDEX",
            "metric_type": "BM25",
        },
    )

    logger.info("Collection '%s' 创建成功", COLLECTION_NAME)


def drop_collection() -> None:
    """删除 collection（重建用）."""
    if utility.has_collection(COLLECTION_NAME):
        utility.drop_collection(COLLECTION_NAME)
        logger.info("Collection '%s' 已删除", COLLECTION_NAME)


def get_collection_stats() -> dict[str, Any]:
    """获取 collection 统计信息."""
    if not utility.has_collection(COLLECTION_NAME):
        return {"exists": False, "count": 0}
    col = Collection(COLLECTION_NAME)
    col.load()
    return {"exists": True, "count": col.num_entities}


# ---------------------------------------------------------------------------
# 阿里百炼 Embedding API
# ---------------------------------------------------------------------------

def embed_texts(texts: list[str], batch_size: int = 10) -> list[list[float]]:
    """调用百炼 text-embedding-v3 批量生成稠密向量.

    Args:
        texts: 待嵌入的文本列表
        batch_size: 每批最多 10 条（百炼 API 限制）

    Returns:
        与 texts 等长的向量列表
    """
    if not DASHSCOPE_API_KEY:
        raise ValueError("DASHSCOPE_API_KEY 未配置")

    all_vectors: list[list[float]] = []
    headers = {
        "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
        "Content-Type": "application/json",
    }

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        payload = {
            "model": EMBEDDING_MODEL,
            "input": {"texts": batch},
            "parameters": {"dimension": EMBEDDING_DIM},
        }

        for attempt in range(3):
            try:
                resp = httpx.post(
                    EMBEDDING_API_URL,
                    json=payload,
                    headers=headers,
                    timeout=60,
                )
                if resp.status_code != 200:
                    logger.error("Embedding API 错误 %d: %s", resp.status_code, resp.text[:500])
                resp.raise_for_status()
                result = resp.json()

                # 百炼返回格式: {"output": {"embeddings": [{"text_index": 0, "embedding": [...]}]}}
                embeddings = result["output"]["embeddings"]
                # 按 text_index 排序确保顺序正确
                embeddings.sort(key=lambda e: e["text_index"])
                vectors = [e["embedding"] for e in embeddings]
                all_vectors.extend(vectors)
                break
            except Exception as e:
                logger.warning("Embedding 批次 %d 第 %d 次失败: %s", i // batch_size, attempt + 1, e)
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    raise

        # 限速：批次间稍作延迟
        if i + batch_size < len(texts):
            time.sleep(0.5)

    return all_vectors


# ---------------------------------------------------------------------------
# 数据写入
# ---------------------------------------------------------------------------

def insert_chunks(chunks: list[dict[str, Any]]) -> int:
    """批量写入知识切片到 Milvus.

    每个 chunk 需包含:
        - id: 唯一标识
        - doc_id: 文档ID
        - source_file: 来源文件
        - source_type: 类型
        - chunk_text: 文本内容
        - metadata: 附加信息 (dict)
        - created_at: 时间戳

    稠密向量由本函数调用百炼 API 生成，稀疏向量由 Milvus BM25 函数自动生成。
    """
    if not chunks:
        return 0

    connect_milvus()
    create_collection()

    # 生成稠密向量
    texts = [c["chunk_text"] for c in chunks]
    logger.info("开始嵌入 %d 条文本...", len(texts))
    vectors = embed_texts(texts)
    logger.info("嵌入完成")

    # 组装 Milvus 行数据（pymilvus 3.0 格式）
    rows = []
    for i, c in enumerate(chunks):
        rows.append({
            "id": c["id"],
            "doc_id": c["doc_id"],
            "source_file": c["source_file"],
            "source_type": c["source_type"],
            "chunk_text": c["chunk_text"],
            "metadata": c.get("metadata", {}),
            "dense_vector": vectors[i],
            "created_at": c["created_at"],
        })

    collection = Collection(COLLECTION_NAME)
    result = collection.insert(rows)
    collection.flush()
    logger.info("成功写入 %d 条记录", len(chunks))
    return len(chunks)


# ---------------------------------------------------------------------------
# 混合检索
# ---------------------------------------------------------------------------

def search(
    query: str,
    top_k: int = 5,
    source_type: str | None = None,
) -> list[dict[str, Any]]:
    """混合检索：稠密向量 + BM25 稀疏向量，RRF 融合排序.

    Args:
        query: 用户查询文本
        top_k: 返回条数
        source_type: 可选过滤条件 (loan/wealth/account/service/risk)

    Returns:
        检索结果列表，每条含 chunk_text, score, source_file, source_type, metadata
    """
    connect_milvus()
    collection = Collection(COLLECTION_NAME)
    collection.load()

    # 查询文本 → 稠密向量
    query_vectors = embed_texts([query])
    dense_vector = query_vectors[0]

    # 构建过滤表达式
    expr = None
    if source_type:
        expr = f'source_type == "{source_type}"'

    output_fields = ["chunk_text", "source_file", "source_type", "metadata", "doc_id"]

    # 稠密向量检索请求
    dense_req = AnnSearchRequest(
        data=[dense_vector],
        anns_field="dense_vector",
        param={"metric_type": "COSINE", "params": {"nprobe": 16}},
        limit=top_k * 2,
        expr=expr,
    )

    # 稀疏向量检索请求 (BM25)
    sparse_req = AnnSearchRequest(
        data=[query],
        anns_field="sparse_vector",
        param={"metric_type": "BM25", "params": {"drop_ratio_search": 0.2}},
        limit=top_k * 2,
        expr=expr,
    )

    # RRF 融合排序
    results = collection.hybrid_search(
        reqs=[dense_req, sparse_req],
        rerank=RRFRanker(k=60),
        limit=top_k,
        output_fields=output_fields,
    )

    # 组装返回
    hits = []
    for hit in results[0]:
        entity = hit.entity
        hits.append(
            {
                "chunk_text": entity.get("chunk_text"),
                "score": round(hit.score, 4),
                "source_file": entity.get("source_file"),
                "source_type": entity.get("source_type"),
                "doc_id": entity.get("doc_id"),
                "metadata": entity.get("metadata"),
            }
        )

    return hits
