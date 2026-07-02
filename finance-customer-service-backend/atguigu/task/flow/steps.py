"""
步骤（节点）设计
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Any, List

from pydantic import BaseModel, Field

from atguigu.task.flow.links import FlowStepLinkUnion, build_links


class FlowStepType(Enum):
    """
    流程的步骤类型
    """
    START = "start"
    ACTION = "action"
    END = "end"
    COLLECT = "collect"


class ResponseDefinition(BaseModel):
    """
    响应的模式:静态模式(static) 改写模式(rephrase) | prompt
    """
    text: str  # 必填字段
    model: str = "static"  # 响应模式
    prompt: str | None = None


class SlotValidation(BaseModel):
    condition: str  # 条件(必填)
    failure_response: ResponseDefinition | None = None


class FlowStep(BaseModel):
    """
    流程步骤模版
    """
    id: str  # 步骤ID
    type: FlowStepType  # 步骤类型
    next: List[FlowStepLinkUnion] = []  # 下一步
    description: str = ""  # 步骤描述

    @classmethod
    def from_dict(cls, step_data: Dict[str, Any]) -> FlowStep:
        # 多态转发
        step_type = step_data['type']
        clz = TYPE_TO_FLOW_STEP[step_type]
        return clz.from_dict(step_data)

    @staticmethod
    def base_load_fields(base_data: Dict[str, Any]) -> Dict[str, Any]:
        """加载各个步骤的基础字段"""
        return {
            "id": base_data['id'],
            "type": FlowStepType(base_data['type']),
            "description": base_data.get('description', ''),
            "next": build_links(base_data['next'])
        }


class StartedFlowStep(FlowStep):

    @classmethod
    def from_dict(cls, step_data: Dict[str, Any]) -> StartedFlowStep:
        return cls(**FlowStep.base_load_fields(step_data))


class ActionFlowStep(FlowStep):
    action: str = ""  # 行动的名字
    args: Dict[str, Any] | str = {}  # 支持字典或字符串引用

    @classmethod
    def from_dict(cls, step_data: Dict[str, Any]) -> ActionFlowStep:
        raw_args = step_data.get('args', {})
        args = raw_args if isinstance(raw_args, (dict, str)) else {}
        return cls(
            **FlowStep.base_load_fields(step_data),
            action=step_data['action'],
            args=args,
        )


class EndFlowStep(FlowStep):

    @classmethod
    def from_dict(cls, step_data: Dict[str, Any]) -> EndFlowStep:
        return cls(**FlowStep.base_load_fields(step_data))


class CollectedFlowStep(FlowStep):
    slot_name: str = ""  # 必填字段
    response: ResponseDefinition | None = None  # 必填字段（填写的槽位）
    validation: SlotValidation | None = Field(default=None, alias="validate")  # 扩展槽位校验的能力

    model_config = {"populate_by_name": True}

    @classmethod
    def from_dict(cls, step_data: Dict[str, Any]) -> CollectedFlowStep:
        resp_data = step_data.get('response')
        response = ResponseDefinition(**resp_data) if resp_data else None

        val_data = step_data.get('validate')
        validate = None
        if val_data:
            failure_resp_data = val_data.get('failure_response')
            failure_resp = ResponseDefinition(**failure_resp_data) if failure_resp_data else None
            validate = SlotValidation(condition=val_data['condition'], failure_response=failure_resp)

        return cls(
            **FlowStep.base_load_fields(step_data),
            slot_name=step_data['slot_name'],
            response=response,
            validation=validate,
        )


# 类的类型 实例类型
TYPE_TO_FLOW_STEP: Dict[str, type[FlowStep]] = {
    "start": StartedFlowStep,
    "action": ActionFlowStep,
    "end": EndFlowStep,
    "collect": CollectedFlowStep
}
