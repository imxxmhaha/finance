import time
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from atguigu.api.logger import logger
from atguigu.infrastructure.llm import llm
from atguigu.domain.messages import UserMessage, BotMessage
from atguigu.domain.state import Turn
from atguigu.prompts.history_builder import HistoryBuilder
from atguigu.prompts.loader import load_prompt
from atguigu.knowledge.providers import KnowledgeChunk


class KnowledgeResponder:

    async def respond(self,
                      user_message: UserMessage,
                      recent_turns: list[Turn],
                      chunks: list[KnowledgeChunk]
                      ) -> list[BotMessage]:
        user_message = HistoryBuilder._render_user_message(user_message)
        history = HistoryBuilder.build(recent_turns)
        knowledge_content = "\n\n".join([chunk.content for chunk in chunks])

        prompt_text = load_prompt("knowledge_respond")
        prompt = PromptTemplate.from_template(prompt_text, template_format="jinja2")
        chain = prompt | llm | StrOutputParser()

        logger.info(f"[LLM] >>> 知识回复 | user_message={user_message[:100]} | chunks={len(chunks)}")
        start = time.time()

        response = await chain.ainvoke({
            "user_message": user_message,
            "history": history,
            "knowledge_content": knowledge_content,
        })

        elapsed = (time.time() - start) * 1000
        logger.info(f"[LLM] <<< 知识回复完成 | {elapsed:.0f}ms | response={response[:100]}")

        return [BotMessage(text=response)]
