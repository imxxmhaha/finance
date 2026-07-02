from typing import Dict, Any
from pydantic import BaseModel


class TaskContext(BaseModel):
    """
    业务任务的上下文
    """
    flow_id: str  # 业务流程的流程ID
    step_id: str | None = None  # 业务流程下步骤ID
    slots: Dict[str, Any] = {}  # 业务任务执行过程中收集到的数据（槽位数据）


class SystemContext(BaseModel):
    """
    系统流程上下文
    """
    flow_id: str  # 系统流程的流程ID(system_task_started)
    step_id: str | None = None  # 系统流程的步骤ID(start)


class StartedSystemContext(SystemContext):
    started_flow_id: str = ""  # 开启具体某一个业务流程的流程ID
    started_flow_name: str = ""  # 开启具体的某一个业务流程的名字


class InterruptedSystemContext(SystemContext):
    interrupted_flow_id: str = ""  # 中断老业务流程的ID
    interrupted_flow_name: str = ""  # 中断老业务流程的名字
    started_flow_id: str = ""  # 开始新业务流程ID
    started_flow_name: str = ""  # 开始新业务流程名字


class ResumedSystemContext(SystemContext):
    resumed_flow_id: str = ""  # 恢复业务流程的ID(中断的业务流程)
    resumed_flow_name: str = ""  # 恢复业务流程的名字(中断的业务流程)


class CanceledSystemContext(SystemContext):
    canceled_flow_id: str = ""
    canceled_flow_name: str = ""


class CollectedSystemContext(SystemContext):
    slot_name: str = ""  # 收集的槽位名
    response: Dict[str, Any] = {}  # {"text":"请告诉我你的账户号"}
