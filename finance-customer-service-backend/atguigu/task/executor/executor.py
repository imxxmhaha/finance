"""
FlowExecutor 由两个方法协作，构成两层嵌套循环，外层管 action、内层管 step。
"""
from typing import Any, List

from jinja2 import Template

from atguigu.domain.contexts import CollectedSystemContext
from atguigu.domain.messages import BotMessage
from atguigu.domain.state import DialogueState
from atguigu.task.action.runner import ActionRunner, ActionCall
from atguigu.task.action.base import ActionResult
from atguigu.task.flow.flows import FlowsList, Flow
from atguigu.task.flow.steps import (
    FlowStep,
    ActionFlowStep,
    EndFlowStep,
    CollectedFlowStep,
    StartedFlowStep,
    FlowStepType,
)
from atguigu.task.flow.links import (
    FlowStepLinkUnion,
    FlowStepStaticLink,
    FlowStepConditionalLink,
    FlowStepFallbackLink, FlowStepLink,
)


class FlowExecutor:
    """
    流程执行器
    """

    async def run_task(self, state: DialogueState, flows: FlowsList, action_runner: ActionRunner) -> List[BotMessage]:
        messages: List[BotMessage] = []
        while True:
            action_call: ActionCall = self.advance_until_action(state, flows)
            if action_call.action_name == "action_listen":
                break
            else:
                action_result: ActionResult = await action_runner.run(action_call, state)
                state.set_slots(action_result.slot_updates)
                messages.extend(action_result.messages)
        return messages

    def advance_until_action(self, state: DialogueState, flows: FlowsList) -> ActionCall:
        """
        内层循环：推进 step 直到遇到 ActionFlowStep
        返回需要执行的 ActionCall
        """
        while True:
            # 1. 获取当前流程
            current_active_task = state.current_active_task()
            if current_active_task is None:
                return ActionCall(action_name="action_listen")

            current_flow: Flow | None = flows.get_flow_by_id(current_active_task.flow_id)
            step: FlowStep | None = current_flow.get_step_by_id(current_active_task.step_id)

            # 2. 执行步骤
            step_result: ActionCall | None = self._run_step(step, state, flows)

            # 3. 如果产生了ActionCall，则跳出当前循环返回到外层循环
            if step_result is not None:
                return step_result

    def _run_step(self, step, state, flows) -> ActionCall | None:
        if isinstance(step, StartedFlowStep):
            return self._run_start_step(step, state)
        if isinstance(step, EndFlowStep):
            return self._run_end_step(state)
        if isinstance(step, CollectedFlowStep):
            return self._run_collect_step(step, state, flows)
        if isinstance(step, ActionFlowStep):
            return self._run_action_step(step, state)

    def _run_action_step(self, step, state) -> ActionCall | None:
        self._advance_to_next_step(step, state)
        action_call: ActionCall = self._build_action_call(step, state)
        return action_call

    def _build_action_call(self, step, state) -> ActionCall:
        """构造 ActionCall，支持字符串引用（如 'context.response'）"""
        args = self._resolve_args(step.args, state)
        return ActionCall(action_name=step.action, action_kwargs=args)

    def _resolve_args(self, args, state) -> Any:
        """
        解析 args，统一使用 Jinja2 模板解析
        """
        if not isinstance(args, str):
            return args

        # 构建模板上下文
        current_task = state.current_active_task()
        template_context = {
            "context": current_task if current_task else {},
            "slots": state.active_task.slots if state.active_task else {},
        }

        original_args = args

        # 如果不包含 Jinja2 语法，自动补全 {{ }}
        if '{{' not in args and '{%' not in args:
            args = f"{{{{ {args} }}}}"

        # 统一使用 Jinja2 解析
        try:
            template = Template(args)
            rendered = template.render(template_context).strip()

            if not rendered:
                if '.' in original_args and not any(op in original_args for op in ['{{', '{%', ' ']):
                    return {}
                return rendered

            if rendered.startswith('{') or rendered.startswith('['):
                import ast
                try:
                    return ast.literal_eval(rendered)
                except (ValueError, SyntaxError):
                    return rendered

            return rendered
        except Exception:
            return {}

    def _run_start_step(self, step, state) -> ActionCall | None:
        self._advance_to_next_step(step, state)
        return None

    def _advance_to_next_step(self, step, state):
        """所有 step 推进的公用方法。"""
        next_step_id = self._select_next_step(step, state)
        state.current_active_task().step_id = next_step_id

    def _select_next_step(self, step, state) -> str:
        """从 next 链接中挑出目标 step，条件跳转的核心逻辑就在这里。"""
        links: list[FlowStepLink] = step.next
        for link in links:
            if isinstance(link, FlowStepStaticLink):
                return link.target
            if isinstance(link, FlowStepConditionalLink):
                if self._eval_condition(link.condition, state):
                    return link.target
            if isinstance(link, FlowStepFallbackLink):
                return link.target

    def _eval_condition(self, condition, state) -> bool:
        """执行条件表达式"""
        current_task = state.current_active_task()
        data = {
            "slots": state.active_task.slots if state.active_task else {},
            "context": current_task.model_dump() if current_task and hasattr(current_task, 'model_dump') else {},
        }
        return bool(eval(condition, {}, data))

    def _run_end_step(self, state) -> ActionCall | None:
        """end 步骤标志一个 flow 跑完了"""
        if state.active_system_task:
            state.end_active_system_task()
            return None
        else:
            state.end_active_task()
            return None

    def _run_collect_step(self, step, state, flows) -> ActionCall | None:
        """
        collect 步骤处理"槽位的所有可能状态"：
        1. 刚来时可能本来就有值
        2. 可能从聚焦对象自动补一个
        3. 可能有值但没通过校验
        4. 可能完全没值
        """
        self._try_to_fill_slot_from_focused_object(step, state)
        if state.active_task.slots.get(step.slot_name):
            # ===== 有值 =====
            if step.validation:
                if self._eval_condition(step.validation.condition, state):
                    # 校验通过 → 推进到下一步
                    self._advance_to_next_step(step, state)
                    return None
                else:
                    # 校验失败 → 清空槽位 + 给失败回复
                    state.remove_slot(step.slot_name)
                    if step.validation.failure_response:
                        return ActionCall(action_name="action_response",
                                          action_kwargs=step.validation.failure_response.model_dump())
                    return ActionCall(action_name="action_response",
                                      action_kwargs={"text": "您提供的信息有误，请重新输入。"})
            else:
                # 无校验规则,直接推进
                self._advance_to_next_step(step, state)
                return None
        else:
            # ===== 无值 → 激活系统收集流程 =====
            state.start_active_system_task(CollectedSystemContext(
                flow_id="system_collect_information",
                step_id=flows.get_flow_by_id("system_collect_information").start_step().id,
                slot_name=step.slot_name,
                response=step.response.model_dump() if step.response else {},
            ))
            return None

    def _try_to_fill_slot_from_focused_object(self, step, state):
        if state.focused_object is None:
            return
        if step.slot_name == 'account_number' and state.focused_object.type == "account":
            state.set_slots({step.slot_name: state.focused_object.id})
        if step.slot_name == "card_number" and state.focused_object.type == "bank_card":
            state.set_slots({step.slot_name: state.focused_object.id})
