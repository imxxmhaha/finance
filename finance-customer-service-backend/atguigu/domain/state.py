import time
import uuid
from typing import Dict, Any

from pydantic import BaseModel

from atguigu.domain.contexts import TaskContext, SystemContext
from atguigu.domain.messages import UserMessage, BotMessage, FocusedObject


class Turn(BaseModel):
    """
    本轮对话的对象
    """
    turn_id: str
    user_message: UserMessage
    bot_messages: list[BotMessage]


class Session(BaseModel):
    """
    会话信息
    """
    session_id: str  # 会话ID
    started_at: float  # 会话开启的时间
    last_activity_at: float  # 最后一次活动的时间戳，用来判断超时
    closed_at: float | None = None  # session是否关闭了
    turns: list[Turn] = []  # 当前会话的多轮


class DialogueState(BaseModel):
    sender_id: str  # 必须传入
    active_task: TaskContext | None = None  # 当前执行的业务任务
    paused_tasks: list[TaskContext] = []  # 当前暂停的业务任务（多个）
    active_system_task: SystemContext | None = None  # 当前执行的系统流程
    focused_object: FocusedObject | None = None
    sessions: list[Session] = []  # 当前用户的所有会话
    current_session_id: str | None = None  # 当前用户的session的sessionID
    pending_turn: Turn | None = None  # turn会话的暂存区

    # --------------任务相关--------------------------

    def start_active_system_task(self, active_system_task: SystemContext):
        """开启系统流程"""
        self.active_system_task = active_system_task

    def end_active_system_task(self):
        """结束系统流程"""
        self.active_system_task = None

    def start_active_task(self, active_task: TaskContext):
        """开启业务任务"""
        self.active_task = active_task

    def end_active_task(self):
        """结束业务任务"""
        self.active_task = None

    def interrupted_active_task(self):
        """中断活跃任务"""
        self.paused_tasks.append(self.active_task)
        self.active_task = None

    def resumed_active_task(self, flow_id: str | None = None) -> bool:
        """恢复业务任务"""
        if not self.paused_tasks:
            return False

        if flow_id is None:
            task = self.paused_tasks.pop()
            self.active_task = task
            return True

        for i, paused_task in enumerate(self.paused_tasks):
            if paused_task.flow_id == flow_id:
                self.active_task = paused_task
                del self.paused_tasks[i]
                return True

        return False

    def cancel_active_task(self):
        self.active_task = None
        self.active_system_task = None

    # --------------槽位相关--------------------------
    def set_slots(self, slots: Dict[str, Any]):
        """设置槽位"""
        self.active_task.slots.update(slots)

    def remove_slot(self, slot_name: str):
        """移除槽位"""
        self.active_task.slots.pop(slot_name)

    # --------------当前信息--------------------------
    def current_active_task(self):
        """当前正在执行的任务（系统流程、业务任务）"""
        return self.active_system_task or self.active_task

    def current_session(self) -> Session | None:
        """返回当前session"""
        for session in self.sessions:
            if session.session_id == self.current_session_id:
                return session
        return None

    # --------------session相关的--------------------------
    def start_session(self):
        """开启session"""
        now = time.time()
        session = Session(session_id=str(uuid.uuid4()), started_at=now, last_activity_at=now)
        self.sessions.append(session)
        self.current_session_id = session.session_id

    def close_session(self):
        if self.current_session() is not None:
            self.current_session().closed_at = time.time()
            self.current_session_id = None

    def reset_running_state_for_new_session(self):
        """session会话超时（60min超时时间）"""
        self.active_task = None
        self.active_system_task = None
        self.paused_tasks = []
        self.focused_object = None
        self.pending_turn = None

    # --------------turn相关的--------------------------
    def begin_turn(self, message: UserMessage):
        if self.current_session():
            turn = Turn(turn_id=str(uuid.uuid4()), user_message=message, bot_messages=[])
            self.pending_turn = turn

    def commit_turn(self):
        if self.current_session():
            self.current_session().turns.append(self.pending_turn)
            self.pending_turn = None

    # --------------FocusedObject相关的--------------------------
    def set_focused_object(self, focused_object: FocusedObject):
        self.focused_object = focused_object
