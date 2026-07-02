import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from atguigu.conf.config import settings
from atguigu.domain.state import DialogueState
from atguigu.infrastructure.http_client import get_http_client


@dataclass
class KnowledgeChunk:
    content: str


class KnowledgeProvider(ABC):
    provider_id = ""

    @abstractmethod
    async def retrieve(
            self,
            state: DialogueState,
    ) -> list[KnowledgeChunk]:
        pass


class AccountAPIProvider(KnowledgeProvider):
    """通过中台 API 查询账户信息"""
    provider_id = 'api.account'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        account_number = state.focused_object.id
        resp = await self._get_account_info(account_number)
        if resp.get("code") != 0:
            return [KnowledgeChunk(content=f"查询账户信息失败：{resp.get('message', '未知错误')}")]
        data = resp.get("data", {})
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"账户信息:\n{text}")]

    async def _get_account_info(self, account_number: str) -> dict[str, Any]:
        url = f"{settings.finance_api_base_url}/api/v1/accounts/{account_number}"
        response = await get_http_client().get(url)
        return response.json()


class BankCardAPIProvider(KnowledgeProvider):
    """通过中台 API 查询客户账户列表（代替银行卡查询）"""
    provider_id = 'api.bank_card'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        customer_no = state.focused_object.id
        resp = await self._get_customer_accounts(customer_no)
        if resp.get("code") != 0:
            return [KnowledgeChunk(content=f"查询账户列表失败：{resp.get('message', '未知错误')}")]
        data = resp.get("data", {})
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"客户账户列表:\n{text}")]

    async def _get_customer_accounts(self, customer_no: str) -> dict[str, Any]:
        url = f"{settings.finance_api_base_url}/api/v1/customers/{customer_no}/accounts"
        response = await get_http_client().get(url)
        return response.json()


class FAQProvider(KnowledgeProvider):
    provider_id = 'faq.default'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        return [KnowledgeChunk(content="未检索到相关问题")]


class RAGProvider(KnowledgeProvider):
    provider_id = 'rag.default'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        return [KnowledgeChunk(content="未检索到相关信息")]
