"""
槽位值解析工具（统一管理）
通过 LLM 将用户自然语言输入解析为标准数值

支持的解析类型:
  - 时间: "最近三个月" -> (start_time, end_time)
  - 金额: "一亿" -> 100000000
  - 期限: "3年" -> 36 (个月)
"""
import json
import time as _time
from datetime import datetime
from typing import Optional, Tuple

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from atguigu.api.logger import logger
from atguigu.infrastructure.llm import llm
from atguigu.prompts.loader import load_prompt


async def _parse(slot_type: str, user_text: str, **extra) -> dict:
    """通用 LLM 解析方法"""
    prompt_text = load_prompt("slot_parser")
    prompt_template = PromptTemplate.from_template(
        template=prompt_text, template_format="jinja2"
    )
    chain = prompt_template | llm | JsonOutputParser()

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[LLM] >>> 槽位解析 | type={slot_type} | text={user_text}")

    start = _time.time()
    try:
        result: dict = await chain.ainvoke({
            "current_time": current_time,
            "slot_type": slot_type,
            "user_text": user_text,
            **extra,
        })
        elapsed = (_time.time() - start) * 1000
        logger.info(f"[LLM] <<< 槽位解析完成 | {elapsed:.0f}ms | type={slot_type} | result={json.dumps(result, ensure_ascii=False)}")
        return result
    except Exception as e:
        elapsed = (_time.time() - start) * 1000
        logger.error(f"[LLM] <<< 槽位解析异常 | {elapsed:.0f}ms | type={slot_type} | error={e}")
        return {}


# ============================================================
# 时间解析
# ============================================================

async def parse_period(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    解析自然语言时间段 -> (start_time, end_time) 格式 "YYYY-MM-DD"

    示例: "最近三个月" -> ("2026-04-02", "2026-07-02")
    """
    if not text or not text.strip():
        return None, None

    result = await _parse("时间", text.strip())
    return result.get("start_time"), result.get("end_time")


# ============================================================
# 金额解析
# ============================================================

async def parse_amount(text: str) -> Optional[float]:
    """
    解析中文金额表达式 -> 金额数值（单位：元）

    示例: "一亿" -> 100000000, "50万" -> 500000
    """
    if not text or not text.strip():
        return None

    result = await _parse("金额", text.strip())
    return result.get("value")


# ============================================================
# 期限解析
# ============================================================

async def parse_term(text: str) -> Optional[int]:
    """
    解析贷款期限表达式 -> 月数

    示例: "3年" -> 36, "半年" -> 6
    """
    if not text or not text.strip():
        return None

    result = await _parse("期限", text.strip())
    return result.get("value")
