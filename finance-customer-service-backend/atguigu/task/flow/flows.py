from __future__ import annotations

from typing import List, Dict

from pydantic import BaseModel

from atguigu.task.flow.steps import FlowStep, StartedFlowStep


class FlowSlot(BaseModel):
    name: str  # 槽位的名字
    type: str = "any"  # 槽位的类型
    label: str = ""  # 槽位的标签
    description: str = ""  # 槽位的描述


class Flow(BaseModel):
    id: str  # 流程的ID
    name: str | None = None  # 流程名字
    description: str = ""
    steps: List[FlowStep] = []  # 步骤
    slots: List[FlowSlot] = []  # 槽位

    def start_step(self) -> StartedFlowStep | None:
        """返回流程的开始步骤"""
        for step in self.steps:
            if isinstance(step, StartedFlowStep):
                return step
        return None

    def get_step_by_id(self, step_id: str) -> FlowStep | None:
        for step in self.steps:
            if step.id == step_id:
                return step
        return None


class FlowsList(BaseModel):
    """
    存放两个yaml文件的流程（业务流程以及系统流程）
    """
    flows: List[Flow] = []
    slots: Dict[str, FlowSlot] = {}

    def get_flow_by_id(self, flow_id: str) -> Flow | None:
        for flow in self.flows:
            if flow.id == flow_id:
                return flow
        return None
