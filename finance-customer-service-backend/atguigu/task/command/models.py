from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class Command:
    command: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Command":
        clz = COMMAND_NAME_TO_CLASS.get(data["command"])
        if clz is not None:
            return clz(**data)
        return Command(command="unknown")


@dataclass
class StartFlowCommand(Command):
    flow: str  # 开启的新的业务流程的流程ID


@dataclass
class SetSlotsCommand(Command):
    slots: Dict[str, Any]  # {"account_number":"ACC001"}


@dataclass
class CancelFlowCommand(Command):
    pass  # 只支持取消当前的业务任务


@dataclass
class ResumeFlowCommand(Command):
    flow: str | None = None  # 恢复指定的业务流程或者当前活跃的业务流程


COMMAND_NAME_TO_CLASS = {
    "start_flow": StartFlowCommand,
    "set_slots": SetSlotsCommand,
    "cancel_flow": CancelFlowCommand,
    "resume_flow": ResumeFlowCommand,
}
