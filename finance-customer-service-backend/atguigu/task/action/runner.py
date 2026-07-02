import time
from dataclasses import dataclass, field
from typing import Any
from atguigu.api.logger import logger
from atguigu.task.action.registry import ActionRegistry
from atguigu.task.action.base import ActionResult
from atguigu.domain.state import DialogueState


@dataclass
class ActionCall:
    """FlowExecutor返回的"""
    action_name: str
    action_kwargs: dict[str, Any] = field(default_factory=dict)


class ActionRunner:
    def __init__(self, registry: ActionRegistry) -> None:
        self.registry = registry

    async def run(self, action_call: ActionCall, state: DialogueState) -> ActionResult:
        action_name = action_call.action_name
        action = self.registry.get(action_name)

        logger.info(f"[Action] >>> 执行 {action_name} | kwargs={action_call.action_kwargs}")
        start = time.time()

        result = await action.run(state, action_call.action_kwargs)

        elapsed = (time.time() - start) * 1000
        msg_count = len(result.messages)
        slot_count = len(result.slot_updates)
        logger.info(f"[Action] <<< {action_name} 完成 | {elapsed:.0f}ms | messages={msg_count} | slot_updates={slot_count}")

        return result
