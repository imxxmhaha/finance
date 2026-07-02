from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass, field
from atguigu.domain.state import DialogueState
from atguigu.domain.messages import BotMessage


@dataclass
class ActionResult:
    messages: list[BotMessage] = field(default_factory=list)         # action执行完后的结果消息
    slot_updates: dict[str, Any] = field(default_factory=dict)       # 业务任务流程要的所有槽位信息
    is_success: bool = True                                            # 业务是否成功，失败时停止流程推进


class Action(ABC):
    name: str  # action的名字

    @abstractmethod
    async def run(
            self,
            state: DialogueState,
            action_kwargs: dict[str, Any],
    ) -> ActionResult:
        pass
