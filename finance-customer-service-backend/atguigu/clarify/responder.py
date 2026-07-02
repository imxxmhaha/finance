import json
import time

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from atguigu.api.logger import logger
from atguigu.domain.state import DialogueState
from atguigu.plan.turn_plan import ClarifyReason
from atguigu.prompts.history_builder import HistoryBuilder
from atguigu.prompts.loader import load_prompt
from atguigu.infrastructure.llm import llm
from atguigu.domain.messages import BotMessage


class ClarifyResponder:

    async def respond(self, state: DialogueState, reason: ClarifyReason) -> list[BotMessage]:
        clarify_message = self.build_clarify_message(reason=reason, state=state)
        user_message = state.pending_turn.user_message
        user_message_str = HistoryBuilder._render_user_message(user_message)
        history_str = HistoryBuilder.build(state.current_session().turns[-10:])
        focused_object_str = json.dumps(state.focused_object.model_dump(mode='json'),
                                        ensure_ascii=False) if state.focused_object is not None else None

        prompt_text = load_prompt("clarify_respond")
        prompt_template = PromptTemplate.from_template(template=prompt_text, template_format="jinja2")
        chain = prompt_template | llm | StrOutputParser()

        logger.info(f"[LLM] >>> 意图澄清 | reason={reason.value} | clarify_message={clarify_message[:80]}")
        start = time.time()

        rewritten = await chain.ainvoke({
            "user_message": user_message_str,
            "history": history_str,
            "focused_object": focused_object_str,
            "clarify_message": clarify_message,
            "reason": reason.value
        })

        elapsed = (time.time() - start) * 1000
        logger.info(f"[LLM] <<< 意图澄清完成 | {elapsed:.0f}ms | response={rewritten[:100]}")

        return [BotMessage(text=rewritten)]

    def build_clarify_message(
            self,
            reason: ClarifyReason,
            state: DialogueState,
    ) -> str:
        if reason is ClarifyReason.MULTIPLE_TRACKS:
            return "您这次同时提到了多个方向。我们先处理一个，您想先办理业务还是先咨询信息呢？"
        if reason is ClarifyReason.MISSING_FOCUSED_OBJECT:
            return "请先发送您想咨询的对象，我再继续帮您看。"
        if reason is ClarifyReason.MISSING_KNOWLEDGE_INTENT:
            return "您是想了解账户信息、贷款政策，还是信用卡相关问题呢？"
        if reason is ClarifyReason.MISSING_TRACK:
            return "您是想先办理业务，还是先咨询信息呢？"
        if reason is ClarifyReason.MISSING_TASK_COMMANDS:
            return "您这次是想办理什么业务呢？比如查余额、查交易记录，或者申请贷款。"
        if reason is ClarifyReason.OBJECT_REQUIRES_INTENT:
            focused_object = state.focused_object
            if focused_object is not None and focused_object.type == "account":
                return "我已经收到这个账户了。您想查余额、查交易记录，还是申请贷款呢？"
            if focused_object is not None and focused_object.type == "bank_card":
                return "我已经收到这张银行卡了。您想查余额、办理挂失，还是其他业务呢？"
        return "我还需要再确认一下您的意思，您可以换个更具体的说法告诉我。"
