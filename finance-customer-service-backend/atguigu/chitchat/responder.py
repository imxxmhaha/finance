import time
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from atguigu.api.logger import logger
from atguigu.domain.messages import UserMessage, BotMessage
from atguigu.domain.state import Turn
from atguigu.prompts.history_builder import HistoryBuilder
from atguigu.prompts.loader import load_prompt
from atguigu.infrastructure.llm import llm


class ChitChatResponder:

    async def respond(self,
                      user_message: UserMessage,
                      recent_turns: list[Turn]):
        user_message_str = HistoryBuilder._render_user_message(user_message)
        history = HistoryBuilder.build(recent_turns)

        prompt_text = load_prompt("chitchat_respond")
        prompt = PromptTemplate.from_template(prompt_text, template_format="jinja2")
        chain = prompt | llm | StrOutputParser()

        logger.info(f"[LLM] >>> 闲聊回复 | user_message={user_message_str[:100]}")
        start = time.time()

        response = await chain.ainvoke({
            "user_message": user_message_str,
            "history": history,
        })

        elapsed = (time.time() - start) * 1000
        logger.info(f"[LLM] <<< 闲聊回复完成 | {elapsed:.0f}ms | response={response[:100]}")

        return [BotMessage(text=response)]
