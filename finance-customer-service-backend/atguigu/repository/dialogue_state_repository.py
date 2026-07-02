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

            # 计算消息数和最后一条消息
            message_count = 0
            last_message = ""
            for turn in session_obj.turns:
                if turn.user_message and turn.user_message.text:
                    message_count += 1
                    last_message = turn.user_message.text
                for bot_msg in turn.bot_messages:
                    message_count += 1
                    if bot_msg.text:
                        last_message = bot_msg.text

            session_insert = insert(DialogueSessionRecord).values(
                sender_id=state.sender_id,
                session_id=session_obj.session_id,
                started_at=_timestamp_to_datetime(session_obj.started_at),
                last_activity_at=_timestamp_to_datetime(session_obj.last_activity_at),
                closed_at=_timestamp_to_datetime(session_obj.closed_at) if session_obj.closed_at else None,
                turns_json=turns_json,
                message_count=message_count,
                last_message=last_message[:500] if last_message else None,
            )
            session_upsert = session_insert.on_duplicate_key_update(
                last_activity_at=session_insert.inserted.last_activity_at,
                closed_at=session_insert.inserted.closed_at,
                turns_json=session_insert.inserted.turns_json,
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
