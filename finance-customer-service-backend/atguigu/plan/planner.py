import json
import time
import logging
from typing import Dict, Any
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from atguigu.api.logger import logger
from atguigu.infrastructure.llm import llm
from atguigu.domain.state import DialogueState
from atguigu.plan.turn_plan import TurnPlan
from atguigu.prompts.loader import load_prompt
from atguigu.task.flow.flows import FlowsList
from atguigu.prompts.history_builder import HistoryBuilder
from atguigu.knowledge.intents import KnowledgeIntent


class TurnPlanner:
    """意图分析器：根据自然语言 调用LLM 分析轨道类型"""

    async def predict(self,
                      state: DialogueState,
                      *,
                      flows: FlowsList,
                      intents: Dict[str, KnowledgeIntent]) -> TurnPlan:
        inputs_prompt = self._build_inputs_prompt(state, flows, intents)
        turn_plan = await self._predict_from_inputs_prompt(inputs_prompt)
        return turn_plan

    def _build_inputs_prompt(self,
                             state: DialogueState,
                             flows_list: FlowsList,
                             intents: Dict[str, KnowledgeIntent]) -> Dict[str, Any]:
        user_msg = HistoryBuilder._render_user_message(state.pending_turn.user_message)
        current_conversation = HistoryBuilder.build(state.current_session().turns[-10:])
        active_task_json = json.dumps(state.active_task.model_dump(mode='json'),
                                      ensure_ascii=False) if state.active_task is not None else None
        interrupted_tasks_json = json.dumps([paused_task.model_dump(mode='json') for paused_task in state.paused_tasks],
                                            ensure_ascii=False)
        focused_object_json = json.dumps(state.focused_object.model_dump(mode='json'),
                                         ensure_ascii=False) if state.focused_object is not None else None
        available_flows_json = json.dumps(
            {"flows": [flow.model_dump(mode='json', exclude={'steps'}) for flow in flows_list.flows]},
            ensure_ascii=False,
        )
        knowledge_intents_json = json.dumps(
            [{"id": intent.id, "description": intent.description} for intent in intents.values()], ensure_ascii=False)

        return {
            "user_message": user_msg,
            "current_conversation": current_conversation,
            "active_task_json": active_task_json,
            "interrupted_tasks_json": interrupted_tasks_json,
            "focused_object_json": focused_object_json,
            "available_flows_json": available_flows_json,
            "knowledge_intents_json": knowledge_intents_json
        }

    async def _predict_from_inputs_prompt(self, inputs_prompt: Dict[str, Any]) -> TurnPlan:
        prompt_template_text = load_prompt("turn_plan")
        prompt_template = PromptTemplate.from_template(template=prompt_template_text, template_format="jinja2")
        chain = prompt_template | llm | JsonOutputParser()

        user_msg = inputs_prompt.get("user_message", "")
        logger.info(f"[LLM] >>> 意图识别 | user_message={user_msg[:100]}")
        start = time.time()

        llm_response_dict: Dict[str, Any] = await chain.ainvoke(inputs_prompt)

        elapsed = (time.time() - start) * 1000
        logger.info(f"[LLM] <<< 意图识别完成 | {elapsed:.0f}ms | response={json.dumps(llm_response_dict, ensure_ascii=False)[:200]}")

        return TurnPlan.from_dict(llm_response_dict)
