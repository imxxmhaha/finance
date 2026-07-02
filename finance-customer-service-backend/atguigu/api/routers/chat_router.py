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
    """获取会话列表"""
    state = await service.load_state(sender_id)
    sessions = []

    if state and state.sessions:
        for session in reversed(state.sessions):
            # 计算消息数量和最后一条消息
            message_count = 0
            last_message = ""
            for turn in session.turns:
                if turn.user_message:
                    message_count += 1
                    last_message = turn.user_message.text or ""
                message_count += len(turn.bot_messages)
                if turn.bot_messages:
                    last_msg = turn.bot_messages[-1]
                    if last_msg.text:
                        last_message = last_msg.text

            sessions.append(SessionInfo(
                session_id=session.session_id,
                started_at=session.started_at,
                last_activity_at=session.last_activity_at,
                message_count=message_count,
                last_message=last_message[:100] if last_message else "",
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


class SummaryRequest(BaseModel):
    messages: List[dict]


class SummaryResponse(BaseModel):
    title: str


@chat_router.post("/api/chat/summary", response_model=SummaryResponse)
async def chat_summary_endpoint(request: SummaryRequest) -> SummaryResponse:
    """生成对话概要标题"""
    if not request.messages:
        return SummaryResponse(title="新对话")

    # 提取消息文本
    msg_texts = []
    for msg in request.messages[:10]:  # 只取前10条消息
        role = "用户" if msg.get("role") == "user" else "客服"
        text = msg.get("text", "")
        if text:
            msg_texts.append(f"{role}：{text}")

    if not msg_texts:
        return SummaryResponse(title="新对话")

    conversation = "\n".join(msg_texts)

    try:
        # 使用 LLM 生成概要标题
        prompt = f"""请根据以下对话内容，生成一个简短的标题（不超过15个字）。

要求：
- 只返回标题，不要其他内容
- 标题要概括对话的主要内容
- 如果是金融相关，可以包含关键词如：账户、理财、贷款、转账等

对话内容：
{conversation}

标题："""

        from langchain_core.messages import HumanMessage
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        title = response.content.strip()

        # 限制标题长度
        if len(title) > 20:
            title = title[:17] + "..."

        return SummaryResponse(title=title or "新对话")
    except Exception as e:
        # 如果 LLM 调用失败，返回默认标题
        return SummaryResponse(title="新对话")


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
