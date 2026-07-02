"""
对话状态持久化仓库
- dialogue_states 表：存储非 session 的状态数据
- dialogue_sessions 表：存储每个 session 的对话轮次
"""
import json
from datetime import datetime, timezone

from sqlalchemy import select, delete
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.domain.state import DialogueState, Session, Turn
from atguigu.models.dialogue_state import DialogueStateRecord
from atguigu.models.dialogue_session import DialogueSessionRecord


class DialogueStateRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def load_state(self, sender_id: str) -> DialogueState:
        """加载对话状态（从两张表合并）"""
        # 1. 加载主状态
        sql = select(DialogueStateRecord).where(DialogueStateRecord.sender_id == sender_id)
        result = await self.session.execute(sql)
        state_record = result.scalar_one_or_none()

        if state_record and state_record.state_json:
            data = json.loads(state_record.state_json)
        else:
            data = {"sender_id": sender_id}

        data["sender_id"] = sender_id

        # 2. 加载所有 session 记录
        session_sql = (
            select(DialogueSessionRecord)
            .where(DialogueSessionRecord.sender_id == sender_id)
            .order_by(DialogueSessionRecord.started_at.asc())
        )
        session_result = await self.session.execute(session_sql)
        session_records = session_result.scalars().all()

        # 3. 将 session 记录转换为 Session 对象
        sessions = []
        for record in session_records:
            turns_data = json.loads(record.turns_json) if record.turns_json else []
            turns = [Turn.model_validate(t) for t in turns_data]

            session_obj = Session(
                session_id=record.session_id,
                started_at=_datetime_to_timestamp(record.started_at),
                last_activity_at=_datetime_to_timestamp(record.last_activity_at),
                closed_at=_datetime_to_timestamp(record.closed_at) if record.closed_at else None,
                turns=turns,
            )
            sessions.append(session_obj)

        data["sessions"] = [s.model_dump() for s in sessions]

        return DialogueState.model_validate(data)

    async def save_state(self, state: DialogueState):
        """保存对话状态（拆分到两张表）"""
        # 1. 序列化主状态（不含 sessions）
        state_dict = state.model_dump(mode="json")
        sessions_data = state_dict.pop("sessions", [])
        state_dict["sessions"] = []  # state_json 中 sessions 为空数组
        state_json = json.dumps(state_dict, ensure_ascii=False)

        # 2. Upsert 主状态
        insert_stmt = insert(DialogueStateRecord).values(
            sender_id=state.sender_id,
            state_json=state_json,
        )
        upsert_stmt = insert_stmt.on_duplicate_key_update(
            state_json=insert_stmt.inserted.state_json,
        )
        await self.session.execute(upsert_stmt)

        # 3. Upsert 每个 session
        saved_session_ids = set()
        for session_data in sessions_data:
            session_obj = Session.model_validate(session_data)
            saved_session_ids.add(session_obj.session_id)

            turns_json = json.dumps(
                [t.model_dump(mode="json") for t in session_obj.turns],
                ensure_ascii=False,
            )

            # 计算消息数、最后一条消息、生成标题
            message_count = 0
            last_message = ""
            user_messages = []
            for turn in session_obj.turns:
                if turn.user_message and turn.user_message.text:
                    message_count += 1
                    last_message = turn.user_message.text
                    user_messages.append(turn.user_message.text)
                for bot_msg in turn.bot_messages:
                    message_count += 1
                    if bot_msg.text:
                        last_message = bot_msg.text

            # 智能生成标题
            title = _generate_smart_title(user_messages)

            session_insert = insert(DialogueSessionRecord).values(
                sender_id=state.sender_id,
                session_id=session_obj.session_id,
                started_at=_timestamp_to_datetime(session_obj.started_at),
                last_activity_at=_timestamp_to_datetime(session_obj.last_activity_at),
                closed_at=_timestamp_to_datetime(session_obj.closed_at) if session_obj.closed_at else None,
                turns_json=turns_json,
                title=title,
                message_count=message_count,
                last_message=last_message[:500] if last_message else None,
            )
            session_upsert = session_insert.on_duplicate_key_update(
                last_activity_at=session_insert.inserted.last_activity_at,
                closed_at=session_insert.inserted.closed_at,
                turns_json=session_insert.inserted.turns_json,
                title=session_insert.inserted.title,
                message_count=session_insert.inserted.message_count,
                last_message=session_insert.inserted.last_message,
            )
            await self.session.execute(session_upsert)

        # 4. 删除已不存在的 session（清理）
        if saved_session_ids:
            # 使用 NOT IN 查询删除
            stmt = (
                delete(DialogueSessionRecord)
                .where(
                    DialogueSessionRecord.sender_id == state.sender_id,
                    DialogueSessionRecord.session_id.notin_(list(saved_session_ids)),
                )
            )
            await self.session.execute(stmt)
        else:
            # 如果没有 session，删除该用户的所有 session
            stmt = delete(DialogueSessionRecord).where(
                DialogueSessionRecord.sender_id == state.sender_id,
            )
            await self.session.execute(stmt)

        await self.session.commit()


# ============================================================
# 时间戳 / datetime 转换
# ============================================================

def _timestamp_to_datetime(ts: float | None) -> datetime | None:
    """epoch timestamp -> datetime (UTC)"""
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _datetime_to_timestamp(dt: datetime | None) -> float | None:
    """datetime -> epoch timestamp"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).timestamp()
    return dt.timestamp()


# ============================================================
# 智能标题生成
# ============================================================

# 关键词到标题的映射
KEYWORD_TITLE_MAP = {
    # 贷款相关
    "贷款": "贷款咨询",
    "借钱": "贷款咨询",
    "借款": "贷款咨询",
    "申请贷款": "贷款申请",
    "贷款申请": "贷款申请",
    "房贷": "房贷咨询",
    "车贷": "车贷咨询",
    "消费贷": "消费贷咨询",
    "经营贷": "经营贷咨询",
    "信用贷": "信用贷咨询",

    # 理财相关
    "理财": "理财咨询",
    "投资": "投资咨询",
    "基金": "基金咨询",
    "存款": "存款咨询",
    "定期": "定期存款",
    "活期": "活期存款",
    "收益": "收益查询",
    "收益率": "收益率查询",
    "产品推荐": "产品推荐",
    "理财产品": "理财咨询",

    # 账户相关
    "余额": "余额查询",
    "账户": "账户查询",
    "账户余额": "余额查询",
    "查询余额": "余额查询",
    "查余额": "余额查询",
    "多少钱": "余额查询",
    "账户信息": "账户查询",

    # 交易相关
    "交易": "交易记录",
    "交易记录": "交易记录",
    "交易明细": "交易记录",
    "流水": "交易记录",
    "转账": "转账咨询",
    "汇款": "转账咨询",

    # 信用卡相关
    "信用卡": "信用卡咨询",
    "挂失": "卡片挂失",
    "卡片丢失": "卡片挂失",
    "补卡": "补卡咨询",
    "额度": "额度查询",

    # 其他业务
    "开户": "开户咨询",
    "销户": "销户咨询",
    "密码": "密码相关",
    "手续费": "费用咨询",
    "利率": "利率查询",
}


def _generate_smart_title(user_messages: list[str]) -> str:
    """
    智能生成对话标题
    1. 提取用户消息中的关键词
    2. 匹配预定义的标题模板
    3. 如果没有匹配，提取核心内容作为标题
    """
    if not user_messages:
        return "新对话"

    # 合并所有用户消息
    all_text = " ".join(user_messages)

    # 1. 尝试匹配关键词
    for keyword, title in KEYWORD_TITLE_MAP.items():
        if keyword in all_text:
            return title

    # 2. 提取第一条消息的核心内容
    first_msg = user_messages[0].strip()

    # 移除常见的无意义前缀
    remove_prefixes = [
        "我想", "我要", "帮我", "请问", "你好", "您好",
        "我想问", "我想查", "我想看", "我想了解",
        "请帮", "麻烦", "可以", "能",
    ]
    for prefix in remove_prefixes:
        if first_msg.startswith(prefix):
            first_msg = first_msg[len(prefix):]
            break

    # 移除标点符号
    first_msg = first_msg.rstrip("。，！？,.!?")

    # 3. 如果消息很短，直接使用
    if len(first_msg) <= 8:
        return first_msg if first_msg else "新对话"

    # 4. 截取核心内容（取前8个字符）
    title = first_msg[:8]

    # 5. 尝试在有意义的位置截断（如"的"、"了"、"吗"等）
    break_chars = ["的", "了", "吗", "呢", "吧", "啊", "呀"]
    for i in range(min(8, len(first_msg)), 0, -1):
        if first_msg[i-1] in break_chars:
            title = first_msg[:i]
            break

    return title + "..." if len(title) < len(first_msg) else title
