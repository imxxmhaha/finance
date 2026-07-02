import uuid
from typing import List, Optional

from fastapi import APIRouter
from fastapi.params import Depends
from pydantic import BaseModel

from atguigu.api.dependencies import get_dialogue_service
from atguigu.api.schemas import ChatRequest, ChatResponse, ChatBotMessage, ChatObject, ChatMessageResponse
from atguigu.domain.messages import UserMessage, ProcessResult, MessageType
from atguigu.service.dialogue_service import DialogueService
from atguigu.domain.messages import FocusedObject
from atguigu.infrastructure.llm import llm

chat_router = APIRouter()


class SessionInfo(BaseModel):
    session_id: str
    started_at: Optional[float] = None
    last_activity_at: Optional[float] = None
    message_count: int = 0
    last_message: str = ""
    title: str = "新对话"


class SessionListResponse(BaseModel):
    sender_id: str
    sessions: List[SessionInfo]


@chat_router.post('/api/chat')
async def chat(
        chat_request: ChatRequest,
        dialogue_service: DialogueService = Depends(get_dialogue_service)
) -> ChatResponse:
    process_result: ProcessResult = await dialogue_service.process_message(_build_user_message(chat_request))
    return _build_chat_response(process_result)


@chat_router.get("/api/chat/history", response_model=ChatMessageResponse)
async def chat_history_endpoint(sender_id: str,
                                service: DialogueService = Depends(get_dialogue_service)
                                ) -> ChatMessageResponse:
    chat_history = await service.load_chat_history(sender_id)
    return ChatMessageResponse(sender_id=sender_id, messages=chat_history)


@chat_router.get("/api/chat/history/sessions", response_model=SessionListResponse)
async def chat_sessions_endpoint(sender_id: str,
                                 service: DialogueService = Depends(get_dialogue_service)
                                 ) -> SessionListResponse:
    """获取会话列表（从 dialogue_sessions 表加载，包含标题）"""
    from atguigu.models.dialogue_session import DialogueSessionRecord
    from sqlalchemy import select

    sql = (
        select(DialogueSessionRecord)
        .where(DialogueSessionRecord.sender_id == sender_id)
        .order_by(DialogueSessionRecord.started_at.desc())
    )
    result = await service.dialogue_state_repository.session.execute(sql)
    session_records = result.scalars().all()

    sessions = []
    for record in session_records:
        sessions.append(SessionInfo(
            session_id=record.session_id,
            started_at=record.started_at.timestamp() if record.started_at else None,
            last_activity_at=record.last_activity_at.timestamp() if record.last_activity_at else None,
            message_count=record.message_count or 0,
            last_message=record.last_message or "",
            title=record.title or "新对话",
        ))

    return SessionListResponse(sender_id=sender_id, sessions=sessions)


def _build_user_message(chat_request: ChatRequest) -> UserMessage:
    return UserMessage(
        sender_id=chat_request.sender_id,
        message_id=chat_request.message_id or str(uuid.uuid4()),
        type=MessageType.TEXT if chat_request.text else MessageType.OBJECT,
        text=chat_request.text,
        object=FocusedObject(type=chat_request.object.type,
                             id=chat_request.object.id,
                             title=chat_request.object.title,
                             attributes=chat_request.object.attributes
                             ) if chat_request.object else None
    )


def _build_chat_response(process_result: ProcessResult) -> ChatResponse:
    return ChatResponse(
        sender_id=process_result.sender_id,
        message_id=process_result.message_id,
        messages=[ChatBotMessage(
            text=message.text,
            object=ChatObject(type=message.object.type,
                              id=message.object.id,
                              title=message.object.title,
                              attributes=message.object.attributes
                              ) if message.object else None
        ) for message in process_result.messages]
    )


class NewSessionRequest(BaseModel):
    sender_id: str


class NewSessionResponse(BaseModel):
    session_id: str
    message: str


@chat_router.post("/api/chat/new-session", response_model=NewSessionResponse)
async def new_session_endpoint(
    request: NewSessionRequest,
    service: DialogueService = Depends(get_dialogue_service)
) -> NewSessionResponse:
    """创建新会话"""
    try:
        # 加载当前状态
        state = await service.load_state(request.sender_id)

        # 关闭当前会话
        if state.current_session_id:
            state.close_session()

        # 重置运行状态
        state.reset_running_state_for_new_session()

        # 开启新会话
        state.start_session()

        # 保存状态
        await service.save_state(state)

        return NewSessionResponse(
            session_id=state.current_session_id,
            message="新会话已创建"
        )
    except Exception as e:
        return NewSessionResponse(
            session_id="",
            message=f"创建会话失败: {str(e)}"
        )


class UpdateTitleRequest(BaseModel):
    sender_id: str
    session_id: str
    title: str


class UpdateTitleResponse(BaseModel):
    success: bool
    message: str


@chat_router.post("/api/chat/session/title", response_model=UpdateTitleResponse)
async def update_session_title_endpoint(
    request: UpdateTitleRequest,
    service: DialogueService = Depends(get_dialogue_service)
) -> UpdateTitleResponse:
    """更新会话标题"""
    try:
        from atguigu.models.dialogue_session import DialogueSessionRecord
        from sqlalchemy import update

        stmt = (
            update(DialogueSessionRecord)
            .where(
                DialogueSessionRecord.sender_id == request.sender_id,
                DialogueSessionRecord.session_id == request.session_id,
            )
            .values(title=request.title)
        )
        await service.dialogue_state_repository.session.execute(stmt)
        await service.dialogue_state_repository.session.commit()

        return UpdateTitleResponse(success=True, message="标题已更新")
    except Exception as e:
        return UpdateTitleResponse(success=False, message=f"更新失败: {str(e)}")


class ClearHistoryRequest(BaseModel):
    sender_id: str


class ClearHistoryResponse(BaseModel):
    success: bool
    message: str


@chat_router.post("/api/chat/history/clear", response_model=ClearHistoryResponse)
async def clear_history_endpoint(
    request: ClearHistoryRequest,
    service: DialogueService = Depends(get_dialogue_service)
) -> ClearHistoryResponse:
    """清除用户所有历史记录"""
    try:
        from atguigu.models.dialogue_session import DialogueSessionRecord
        from atguigu.models.dialogue_state import DialogueStateRecord
        from sqlalchemy import delete

        # 删除所有会话记录
        session_stmt = delete(DialogueSessionRecord).where(
            DialogueSessionRecord.sender_id == request.sender_id
        )
        await service.dialogue_state_repository.session.execute(session_stmt)

        # 删除对话状态记录
        state_stmt = delete(DialogueStateRecord).where(
            DialogueStateRecord.sender_id == request.sender_id
        )
        await service.dialogue_state_repository.session.execute(state_stmt)

        await service.dialogue_state_repository.session.commit()

        return ClearHistoryResponse(success=True, message="历史记录已清除")
    except Exception as e:
        return ClearHistoryResponse(success=False, message=f"清除失败: {str(e)}")


class DeleteSessionRequest(BaseModel):
    sender_id: str
    session_id: str


class DeleteSessionResponse(BaseModel):
    success: bool
    message: str


@chat_router.post("/api/chat/session/delete", response_model=DeleteSessionResponse)
async def delete_session_endpoint(
    request: DeleteSessionRequest,
    service: DialogueService = Depends(get_dialogue_service)
) -> DeleteSessionResponse:
    """删除单条会话记录"""
    try:
        from atguigu.models.dialogue_session import DialogueSessionRecord
        from sqlalchemy import delete

        # 删除指定会话记录
        stmt = delete(DialogueSessionRecord).where(
            DialogueSessionRecord.sender_id == request.sender_id,
            DialogueSessionRecord.session_id == request.session_id,
        )
        await service.dialogue_state_repository.session.execute(stmt)
        await service.dialogue_state_repository.session.commit()

        return DeleteSessionResponse(success=True, message="会话已删除")
    except Exception as e:
        return DeleteSessionResponse(success=False, message=f"删除失败: {str(e)}")
