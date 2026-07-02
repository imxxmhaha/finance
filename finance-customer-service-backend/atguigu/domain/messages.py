from enum import Enum
from typing import Literal

from pydantic import BaseModel


class FocusedObject(BaseModel):
    type: str
    id: str
    title: str | None = None
    attributes: dict = {}


class MessageType(Enum):
    TEXT = 'text'
    OBJECT = 'object'


class MessageObject(BaseModel):
    type: str
    id: str
    title: str | None = None
    attributes: dict = {}


class UserMessage(BaseModel):
    sender_id: str
    message_id: str
    type: MessageType
    text: str | None = None
    object: FocusedObject | None = None


class BotMessage(BaseModel):
    text: str | None = None
    object: FocusedObject | None = None


class ProcessResult(BaseModel):
    sender_id: str
    message_id: str
    messages: list[BotMessage]


class ChatHistoryMessage(BaseModel):
    session_id: str
    role: Literal["user", "bot"]
    text: str | None = None
    object: FocusedObject | None = None
