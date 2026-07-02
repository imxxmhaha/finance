import time
from typing import Dict, Any
from atguigu.api.logger import logger
from atguigu.domain.state import DialogueState, Session
from atguigu.domain.messages import UserMessage, ProcessResult, BotMessage, MessageType
from atguigu.plan.planner import TurnPlanner
from atguigu.task.command.models import Command
from atguigu.task.handler import TaskHandler
from atguigu.knowledge.handler import KnowLedgeHandler
from atguigu.chitchat.handler import ChitChatHandler
from atguigu.task.flow.flows import FlowsList
from atguigu.plan.turn_validator import TurnPlanValidator
from atguigu.clarify.responder import ClarifyResponder
from atguigu.knowledge.intents import KnowledgeIntent
from atguigu.plan.turn_plan import ClarifyReason
from atguigu.task.command.models import SetSlotsCommand
from atguigu.task.flow.steps import CollectedFlowStep


class DialogueEngine:
    """调度中心（只协调各个组件、身上的各个组件真正干活）"""

    def __init__(self,
                 turn_planner: TurnPlanner,
                 turn_validator: TurnPlanValidator,
                 clarify_responder: ClarifyResponder,
                 task_handler: TaskHandler,
                 knowledge_handler: KnowLedgeHandler,
                 chit_chat_handler: ChitChatHandler
                 ):
        self.turn_planner = turn_planner
        self.turn_validator = turn_validator
        self.clarify_responder = clarify_responder
        self.task_handler = task_handler
        self.knowledge_handler = knowledge_handler
        self.chit_chat_handler = chit_chat_handler

    async def handle_dialogue(self, state: DialogueState,
                              user_message: UserMessage) -> ProcessResult:
        logger.info(f"[Engine] >>> 收到用户消息 | sender={user_message.sender_id} | type={user_message.type.value} | text={user_message.text}")

        # 1. 开启Session
        self._prepare_session(state)

        # 2. 开启turn
        self._begin_turn(state, user_message)

        # 3. 判断消息类型
        if user_message.type is MessageType.TEXT:
            logger.info(f"[Engine] 处理文本消息，进入意图识别")
            msgs = await self._handle_text_msg(
                state,
                self.turn_planner,
                self.task_handler.flows,
                self.knowledge_handler.knowledge_intents)
        else:
            logger.info(f"[Engine] 处理对象消息 | object_type={user_message.object.type} | object_id={user_message.object.id}")
            state.set_focused_object(user_message.object)
            msgs = await self._handle_obj_msg(user_message, state, self.task_handler.flows)

        # 4. 更新turn中的BotMessage
        state.pending_turn.bot_messages.extend(msgs)

        # 5. 提交
        state.commit_turn()

        # 6. 返回
        logger.info(f"[Engine] <<< 回复完成 | 共{len(msgs)}条消息")
        return ProcessResult(
            sender_id=user_message.sender_id,
            message_id=user_message.message_id,
            messages=msgs
        )

    def _prepare_session(self, state: DialogueState) -> None:
        current_session: Session = state.current_session()
        if current_session is None:
            state.start_session()
            logger.info(f"[Engine] 新建会话 | session_id={state.current_session_id}")
            return

        now = time.time()
        if now - current_session.last_activity_at > 60 * 60:
            state.close_session()
            state.reset_running_state_for_new_session()
            state.start_session()
            logger.info(f"[Engine] 会话超时，重建会话 | new_session_id={state.current_session_id}")
        else:
            current_session.last_activity_at = now

    def _begin_turn(self, state: DialogueState, user_message: UserMessage):
        state.begin_turn(user_message)

    async def _handle_text_msg(self, state: DialogueState,
                               turn_planner: TurnPlanner,
                               flows: FlowsList,
                               knowledge_intents: Dict[str, KnowledgeIntent]
                               ) -> list[BotMessage]:
        """处理文本类型消息"""
        # 1. 意图识别
        logger.info(f"[Engine] --- 意图识别开始 ---")
        turn_plan = await turn_planner.predict(state, flows=flows, intents=knowledge_intents)
        logger.info(f"[Engine] 意图识别结果 | task={turn_plan.task is not None} | knowledge={turn_plan.knowledge is not None} | chitchat={turn_plan.chitchat is not None}")

        # 2. 校验
        validated = self.turn_validator.validate(state, turn_plan, flow_list=flows, intents=knowledge_intents)

        if not validated.valid:
            logger.info(f"[Engine] 意图校验不通过 | reason={validated.reason.value}")
            return await self.clarify_responder.respond(state, validated.reason)

        # 3. 分轨处理
        if turn_plan.task is not None:
            cmd_names = [c.command for c in turn_plan.task.commands]
            logger.info(f"[Engine] 进入业务任务轨道 | commands={cmd_names}")
            return await self.task_handler.handle(state, commands=turn_plan.task.commands)
        elif turn_plan.knowledge is not None:
            logger.info(f"[Engine] 进入知识咨询轨道 | intents={turn_plan.knowledge.intents}")
            return await self.knowledge_handler.handle(state, turn_plan.knowledge.intents)
        else:
            logger.info(f"[Engine] 进入闲聊轨道")
            return await self.chit_chat_handler.handle(state)

    async def _handle_obj_msg(self, user_message: UserMessage,
                              state: DialogueState,
                              flows: FlowsList) -> list[BotMessage]:

        commands = self._resolve_object_command(user_message, state, flows)
        if commands:
            return await self.task_handler.handle(state=state, commands=commands)

        if state.active_task is not None:
            return await self.task_handler.handle(state=state, commands=[])

        return await self.clarify_responder.respond(state, reason=ClarifyReason.OBJECT_REQUIRES_INTENT)

    def _resolve_object_command(self, user_message: UserMessage,
                                state: DialogueState,
                                flows: FlowsList) -> list[Command]:

        user_obj = user_message.object
        if user_obj is None:
            return []

        object_type = user_obj.type

        if object_type == "account":
            if self._flow_has_unfilled_collect_slot(state, flows, "account_number"):
                return [SetSlotsCommand(command="set_slots", slots={"account_number": user_obj.id})]
            return []

        if object_type == "bank_card":
            if self._flow_has_unfilled_collect_slot(state, flows, "card_number"):
                return [SetSlotsCommand(command="set_slots", slots={"card_number": user_obj.id})]
            return []

        return []

    def _flow_has_unfilled_collect_slot(self, state: DialogueState,
                                        flows: FlowsList, slot_name: str) -> bool:

        active_task = state.active_task
        if active_task is None:
            return False

        flow_id = active_task.flow_id
        flow = flows.get_flow_by_id(flow_id)
        if flow is None:
            return False

        if active_task.slots.get(slot_name):
            return False

        for step in flow.steps:
            if isinstance(step, CollectedFlowStep) and step.slot_name == slot_name:
                return True

        return False
