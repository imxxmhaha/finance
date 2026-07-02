from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Discriminator


class FlowStepLink(BaseModel):
    """模版边（基类）"""
    target: str  # 下一条步骤（节点）的ID


class FlowStepStaticLink(FlowStepLink):
    """对应的是next:"ask_account_number" """
    link_type: Literal["static"] = "static"


class FlowStepConditionalLink(FlowStepLink):
    """对应的是next:"[{"if":"xxxxxx","then":"step_id"}]" """
    link_type: Literal["conditional"] = "conditional"
    condition: str  # 接收if 中的xxxxx


class FlowStepFallbackLink(FlowStepLink):
    """对应的是next:"[{"else":"step_id"}]" """
    link_type: Literal["fallback"] = "fallback"


# 带 Discriminator 的联合类型，让 Pydantic 正确序列化子类字段
FlowStepLinkUnion = Annotated[
    Union[FlowStepStaticLink, FlowStepConditionalLink, FlowStepFallbackLink],
    Discriminator("link_type"),
]


def build_links(link_data: str | list[dict]) -> list[FlowStepLinkUnion]:
    """
    将 YAML 中的 next 字段转为 FlowStepLink 列表
    next 可以是字符串（静态跳转）或列表（条件跳转）
    """
    if isinstance(link_data, str):
        return [FlowStepStaticLink(target=link_data)]

    links = []
    for link_dict in link_data:
        if "if" in link_dict:
            links.append(FlowStepConditionalLink(condition=link_dict['if'], target=link_dict['then']))
        else:
            links.append(FlowStepFallbackLink(target=link_dict['else']))
    return links
