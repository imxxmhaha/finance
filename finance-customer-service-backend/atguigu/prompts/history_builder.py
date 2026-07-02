from typing import List, Dict, Any
from atguigu.domain.state import Turn, FocusedObject, Session
from atguigu.domain.messages import UserMessage, BotMessage, MessageType, ChatHistoryMessage


class HistoryBuilder:
    """
    1. 将用户消息的UserMessage对象序列化为字符串---->"USER: 我准备查询账户余额"
    2. 将历史对话的Q(UserMessage)A(BotMessage)对象序列化为字符串
    """

    @staticmethod
    def build(turns: List[Turn]) -> str:
        """构建历史对话"""
        msgs: List[str] = []
        for turn in turns:
            # 1. 用户消息
            user_message = turn.user_message
            user_message_str = HistoryBuilder._render_user_message(user_message)
            msgs.append(f"USER: {user_message_str}")
            # 2. 机器人回复消息
            for bot_msg in turn.bot_messages:
                bot_msg_str = HistoryBuilder._render_bot_message(bot_msg)
                msgs.append(f"BOT: {bot_msg_str}")
        return "\n".join(msgs)

    @staticmethod
    def _render_user_message(user_message: UserMessage) -> str:
        """渲染用户消息"""
        if user_message.type is MessageType.TEXT:
            return HistoryBuilder._render_text_msg(user_message.text)
        else:
            return HistoryBuilder._render_obj_msg(user_message.object)

    @staticmethod
    def _render_text_msg(text: str) -> str:
        return text.strip()

    @classmethod
    def _render_obj_msg(cls, object_msg: FocusedObject) -> str:
        label = "账户对象" if object_msg.type == "account" else "银行卡对象"
        id = object_msg.id
        title = object_msg.title
        attributes: Dict[str, Any] = object_msg.attributes
        attributes_str = " ".join([f"{key}={value}" for key, value in attributes.items()])
        return f"[label={label}, id={id}, title={title}, attributes={attributes_str}]"

    @classmethod
    def _render_bot_message(cls, bot_msg: BotMessage) -> str:
        if bot_msg.text:
            return HistoryBuilder._render_text_msg(bot_msg.text)
        else:
            return HistoryBuilder._render_obj_msg(bot_msg.object)

    @staticmethod
    def render_chat_history_user_message(user_message: UserMessage, session: Session):
        return ChatHistoryMessage(
            session_id=session.session_id,
            role="user",
            text=user_message.text,
            object=user_message.object
        )

    @staticmethod
    def render_chat_history_bot_message(bot_message: BotMessage, session: Session):
        return ChatHistoryMessage(
            session_id=session.session_id,
            role="bot",
            text=bot_message.text,
            object=bot_message.object
        )
