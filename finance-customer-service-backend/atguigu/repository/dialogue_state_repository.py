from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.domain.state import DialogueState
from atguigu.models.dialogue_state import DialogueStateRecord


class DialogueStateRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def load_state(self, sender_id: str) -> DialogueState:
        """加载对话状态"""
        sql = select(DialogueStateRecord).where(DialogueStateRecord.sender_id == sender_id)
        result = await self.session.execute(sql)
        state = result.scalar_one_or_none()

        if state and state.state_json:
            return _deserialize_dialogue_state(sender_id, state.state_json)
        else:
            return DialogueState(sender_id=sender_id)

    async def save_state(self, state: DialogueState):
        """保存对话状态"""
        state_json = _serialize_dialogue_state(state)

        insert_stmt = insert(DialogueStateRecord).values(
            sender_id=state.sender_id,
            state_json=state_json
        )
        upsert_stmt = insert_stmt.on_duplicate_key_update(
            state_json=insert_stmt.inserted.state_json
        )

        await self.session.execute(upsert_stmt)
        await self.session.commit()


# ============================================================
# 序列化 / 反序列化辅助函数
# ============================================================

def _serialize_dialogue_state(state: DialogueState) -> str:
    """将 DialogueState 序列化为 JSON 字符串"""
    return state.model_dump_json()


def _deserialize_dialogue_state(sender_id: str, state_json: str) -> DialogueState:
    """将 JSON 字符串反序列化为 DialogueState"""
    import json
    data = json.loads(state_json)
    data["sender_id"] = sender_id
    return DialogueState.model_validate(data)
