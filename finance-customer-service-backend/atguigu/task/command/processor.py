from typing import List

from atguigu.domain.contexts import TaskContext, StartedSystemContext, InterruptedSystemContext, ResumedSystemContext, \
    CanceledSystemContext
from atguigu.domain.state import DialogueState
from atguigu.task.command.models import Command, StartFlowCommand, SetSlotsCommand, ResumeFlowCommand, CancelFlowCommand
from atguigu.task.flow.flows import FlowsList


class CommandProcessor:
    """
    命令处理器
    """

    def run(self, state: DialogueState, commands: List[Command], flow_list: FlowsList) -> None:
        for command in commands:
            self._apply(state, command=command, flow_list=flow_list)

    def _apply(self, state: DialogueState, *, command: Command, flow_list: FlowsList):

        if isinstance(command, StartFlowCommand):
            self._handle_start_flow(state, command, flow_list)
        elif isinstance(command, SetSlotsCommand):
            self._handle_set_slots(state, command)
        elif isinstance(command, ResumeFlowCommand):
            self._handle_resume_flow(state, flow_list, command)
        elif isinstance(command, CancelFlowCommand):
            self.handle_cancel_flow(state, flow_list)
        else:
            pass

    def _handle_set_slots(self, state: DialogueState, command: SetSlotsCommand):
        if state.active_task is not None:
            state.set_slots(command.slots)

    def _handle_start_flow(self,
                           state: DialogueState,
                           command: StartFlowCommand,
                           flow_list: FlowsList):
        """
        开启业务任务
        """
        # 0. 清除当前系统流程
        state.end_active_system_task()
        # 0.1 不允许直接启动system_ 开头的内部流程
        if command.flow.startswith("system_"):
            raise ValueError(f"不能开启系统流程流程ID: {command.flow}")
        # 0.2 判断流程是否存在, 且有起点
        target_flow = flow_list.get_flow_by_id(command.flow)
        if target_flow is None:
            raise ValueError(f"开启的流程ID: {command.flow} 对应的流程不存在")
        start_step = target_flow.start_step()
        if start_step is None:
            raise ValueError(f"流程ID: {command.flow} 的起点不存在")

        # 1. 当前活跃任务
        active_task = state.active_task
        # ===== 情况一:当前有活跃任务 =====
        if active_task is not None:
            # a) 当前活跃任务就是需要开启的流程
            if active_task.flow_id == command.flow:
                return  # 不用重复开

            # b) 代码走到这里, 说明当前正在执行的业务任务不是要开启的业务任务
            # b.1) 中断别人: 将当前任务压进暂停栈中, 将活跃业务流程置空
            interrupted_flow_id = active_task.flow_id
            interrupted_flow_name = self._readable_flow_name(active_task.flow_id, flow_list)
            state.interrupted_active_task()

            # b.2) 尝试从暂停栈中恢复 目标任务
            resumed_flag = state.resumed_active_task(command.flow)
            if not resumed_flag:
                started_flow_id = command.flow
                started_flow_name = self._readable_flow_name(command.flow, flow_list)
                # ②要开的流程不在暂停栈 → 新建
                state.start_active_task(TaskContext(flow_id=command.flow, step_id=start_step.id))
            else:
                # ③要开的流程在暂停栈 → 已被 resume_task 恢复
                started_flow_id = command.flow
                started_flow_name = self._readable_flow_name(command.flow, flow_list)

            # b.3) 引出中断系统流程
            self._activate_interrupted_system_task(
                state, flow_list,
                interrupted_flow_id=interrupted_flow_id,
                interrupted_flow_name=interrupted_flow_name,
                started_flow_id=started_flow_id,
                started_flow_name=started_flow_name,
            )
            return

        # ===== 情况二:当前没有活跃任务 =====
        # 试着从暂停栈中恢复同名任务
        resumed = state.resumed_active_task(command.flow)
        if resumed:
            # 能恢复, 引出恢复系统流程
            self._activate_resumed_system_flow(
                state, flow_list,
                resumed_flow_id=command.flow,
                resumed_flow_name=self._readable_flow_name(command.flow, flow_list),
            )
            return

        # 暂停栈没有目标任务, 需要新开，引出开启系统流程的开场白
        state.start_active_task(TaskContext(flow_id=command.flow, step_id=start_step.id))
        self._activate_start_system_task(
            state, flow_list,
            started_flow_id=command.flow,
            started_flow_name=self._readable_flow_name(command.flow, flow_list),
        )

    @staticmethod
    def _readable_flow_name(flow_id: str, flow_list: FlowsList) -> str:
        flow = flow_list.get_flow_by_id(flow_id)
        return flow.name if flow.name else flow.id

    @staticmethod
    def _activate_start_system_task(state: DialogueState,
                                    flow_list: FlowsList,
                                    *,
                                    started_flow_id: str,
                                    started_flow_name: str):
        flow = flow_list.get_flow_by_id("system_task_started")
        state.start_active_system_task(StartedSystemContext(
            flow_id=flow.id,
            step_id=flow.start_step().id,
            started_flow_id=started_flow_id,
            started_flow_name=started_flow_name
        ))

    @staticmethod
    def _activate_interrupted_system_task(state: DialogueState,
                                          flow_list: FlowsList,
                                          *,
                                          interrupted_flow_id: str,
                                          interrupted_flow_name: str,
                                          started_flow_id: str,
                                          started_flow_name: str):
        flow = flow_list.get_flow_by_id("system_task_interrupted")
        state.start_active_system_task(InterruptedSystemContext(
            flow_id=flow.id,
            step_id=flow.start_step().id,
            interrupted_flow_id=interrupted_flow_id,
            interrupted_flow_name=interrupted_flow_name,
            started_flow_id=started_flow_id,
            started_flow_name=started_flow_name
        ))

    def _activate_resumed_system_flow(self,
                                      state: DialogueState,
                                      flow_list: FlowsList,
                                      resumed_flow_id: str,
                                      resumed_flow_name: str):
        flow = flow_list.get_flow_by_id("system_task_resumed")
        state.start_active_system_task(ResumedSystemContext(
            flow_id=flow.id,
            step_id=flow.start_step().id,
            resumed_flow_id=resumed_flow_id,
            resumed_flow_name=resumed_flow_name
        ))

    def _activate_cancel_system_flow(self,
                                     state: DialogueState,
                                     flow_list: FlowsList,
                                     *,
                                     cancel_flow_id: str,
                                     cancel_flow_name: str):
        flow = flow_list.get_flow_by_id("system_task_canceled")
        state.start_active_system_task(CanceledSystemContext(
            flow_id=flow.id,
            step_id=flow.start_step().id,
            canceled_flow_id=cancel_flow_id,
            canceled_flow_name=cancel_flow_name
        ))

    def handle_cancel_flow(self,
                           state: DialogueState,
                           flow_list: FlowsList):
        """取消当前业务流程、进入取消系统流程"""
        task = state.active_task
        flow = flow_list.get_flow_by_id(task.flow_id)
        self._activate_cancel_system_flow(state,
                                          flow_list,
                                          cancel_flow_id=flow.id,
                                          cancel_flow_name=self._readable_flow_name(flow.id, flow_list)
                                          )
        state.end_active_task()

    def _handle_resume_flow(self,
                            state: DialogueState,
                            flow_list: FlowsList,
                            command: ResumeFlowCommand):

        # ===== 第一步:确定要恢复哪个流程 =====
        if command.flow is not None:
            target_flow = flow_list.get_flow_by_id(command.flow)
            if target_flow is None:
                raise ValueError(f"Unknown flow '{command.flow}'.")
            target_flow_id = target_flow.id
            target_flow_name = target_flow.name
        else:
            if not state.paused_tasks:
                return
            top_paused = state.paused_tasks[-1]
            target_flow_id = top_paused.flow_id
            target_flow_name = self._readable_flow_name(target_flow_id, flow_list)

        # ===== 第二步:按"当前有没有活跃任务"恢复 =====
        active_task = state.active_task

        if active_task is not None:
            if active_task.flow_id == target_flow_id:
                return

            state.interrupted_active_task()
            interrupted_flow_id = active_task.flow_id
            interrupted_flow_name = self._readable_flow_name(active_task.flow_id, flow_list)

            if not state.resumed_active_task(flow_id=target_flow_id):
                state.resumed_active_task()
                return

            self._activate_interrupted_system_task(
                state, flow_list,
                interrupted_flow_id=interrupted_flow_id,
                interrupted_flow_name=interrupted_flow_name,
                started_flow_id=target_flow_id,
                started_flow_name=target_flow_name,
            )
        else:
            if not state.resumed_active_task(command.flow):
                return

            resumed = state.active_task
            self._activate_resumed_system_flow(
                state, flow_list,
                resumed_flow_id=resumed.flow_id,
                resumed_flow_name=self._readable_flow_name(resumed.flow_id, flow_list),
            )
