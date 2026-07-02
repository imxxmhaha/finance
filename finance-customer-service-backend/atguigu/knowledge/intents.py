from dataclasses import dataclass, field


@dataclass
class KnowledgeIntent:
    id: str
    description: str
    provider_ids: list[str] = field(default_factory=list)
    requires_object: str | None = None


KNOWLEDGE_INTENTS: dict[str, KnowledgeIntent] = {
    "account_info": KnowledgeIntent(
        id="account_info",
        description="账户信息咨询",
        provider_ids=["api.account"],
        requires_object="account",
    ),
    "bank_card_info": KnowledgeIntent(
        id="bank_card_info",
        description="银行卡信息咨询",
        provider_ids=["api.bank_card"],
        requires_object="bank_card",
    ),
    "loan_policy": KnowledgeIntent(
        id="loan_policy",
        description="贷款政策咨询",
        provider_ids=["faq.default", "rag.default"],
    ),
    "credit_card_policy": KnowledgeIntent(
        id="credit_card_policy",
        description="信用卡政策咨询",
        provider_ids=["faq.default", "rag.default"],
    ),
    "interest_rate": KnowledgeIntent(
        id="interest_rate",
        description="利率信息咨询",
        provider_ids=["faq.default", "rag.default"],
    ),
    "service_fee": KnowledgeIntent(
        id="service_fee",
        description="手续费咨询",
        provider_ids=["faq.default", "rag.default"],
    ),
    "general_finance_info": KnowledgeIntent(
        id="general_finance_info",
        description="金融通用信息咨询",
        provider_ids=["faq.default", "rag.default"],
    ),
}
