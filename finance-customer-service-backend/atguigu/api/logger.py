import sys
import uuid
from pathlib import Path
from contextvars import ContextVar

from loguru import logger

# ============================================================
# 请求上下文变量
# ============================================================
request_context_var: ContextVar[dict] = ContextVar(
    "request_context", default={"request_id": "-", "user_id": "-"}
)


def set_request_context(request_id: str = None, user_id: str = None):
    """设置当前请求的上下文信息"""
    ctx = request_context_var.get().copy()
    if request_id is not None:
        ctx["request_id"] = request_id
    if user_id is not None:
        ctx["user_id"] = user_id
    request_context_var.set(ctx)


def reset_request_context():
    """重置请求上下文"""
    request_context_var.set({"request_id": "-", "user_id": "-"})


# ============================================================
# 日志格式
# ============================================================
log_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<magenta>request_id - {extra[request_id]}</magenta> | "
    "<yellow>user_id - {extra[user_id]}</yellow> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


def inject_request_context(record):
    """注入请求上下文信息到日志记录中"""
    try:
        context_data = request_context_var.get()
        request_id = context_data.get("request_id", str(uuid.uuid4())[:8])
        user_id = context_data.get("user_id", "anonymous")
    except Exception:
        request_id = str(uuid.uuid4())[:8]
        user_id = "anonymous"

    record["extra"]["request_id"] = request_id
    record["extra"]["user_id"] = user_id


# ============================================================
# 初始化 logger
# ============================================================
logger.remove()
logger = logger.patch(inject_request_context)

# 控制台输出
logger.add(
    sink=sys.stdout,
    level="DEBUG",
    format=log_format,
)

# 文件输出
_log_dir = Path(__file__).resolve().parents[2] / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)
logger.add(
    sink=_log_dir / "app.log",
    level="INFO",
    format=log_format,
    rotation="10 MB",
    retention="7 days",
    encoding="utf-8",
)


if __name__ == '__main__':
    logger.info("hello world")
    logger.debug("debug message")
    logger.error("error message")
