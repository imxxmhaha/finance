# 金融智能客服系统代码生成提示词

## 一、项目背景

基于现有电商客服系统架构，构建面向金融行业的智能客服系统。系统需要支持账户管理、银行卡、存款、贷款、理财、基金、信用卡、支付转账等一站式金融服务。

### 参考架构路径
- 电商客服代码：`D:\ws\py_ws\20260316\project\04\ecommerce-customer\customer-service-backend`
- 流程配置目录：`flow_config/`

### 输出路径
`D:\ws\py_ws\20260316\project\06\finance\finance-customer-service-backend`

---

## 二、系统架构设计

### 2.1 目录结构（保持与电商客服一致）


---

## 三、核心模块实现要求

### 3.1 流程配置文件（flow_config/）

#### 3.1.1 user_flows.yml（用户业务流程）

根据金融需求文档，需要定义以下业务流程：

**槽位定义（slots）：**
```yaml
slots:
  # 账户相关
  account_number:
    type: text
    label: 账户号
    description: 用户的银行账户号

  bank_card_number:
    type: text
    label: 银行卡号
    description: 用户的银行卡号

  # 交易相关
  transaction_date:
    type: text
    label: 交易日期
    description: 查询交易的日期

  transaction_id:
    type: text
    label: 交易流水号
    description: 交易流水号

  # 贷款相关
  loan_type:
    type: text
    label: 贷款类型
    description: 贷款类型（消费贷、经营贷、房贷等）

  loan_amount:
    type: text
    label: 贷款金额
    description: 申请贷款的金额

  loan_term:
    type: text
    label: 贷款期限
    description: 贷款期限（月）

  loan_purpose:
    type: text
    label: 贷款用途
    description: 贷款资金用途

  # 信用卡相关
  credit_card_number:
    type: text
    label: 信用卡号
    description: 需要挂失的信用卡号

  loss_reason:
    type: text
    label: 挂失原因
    description: 信用卡挂失原因

  identity_verification:
    type: text
    label: 身份验证信息
    description: 用于身份验证的信息

  # 投诉相关
  ticket_type:
    type: text
    label: 工单类型
    description: 投诉工单类型

  related_transaction_id:
    type: text
    label: 关联交易号
    description: 投诉关联的交易流水号

  problem_description:
    type: text
    label: 问题描述
    description: 投诉问题的详细描述

  # 查询结果
  account_balance:
    type: text
    label: 账户余额
    description: 账户余额信息

  transaction_list:
    type: text
    label: 交易流水列表
    description: 查询到的交易流水

  application_id:
    type: text
    label: 申请编号
    description: 贷款申请编号

  ticket_id:
    type: text
    label: 工单编号
    description: 投诉工单编号
```

**业务流程定义（flows）：**

```yaml
flows:
  # 欢迎引导
  onboarding:
    name: 欢迎引导
    description: 金融客服助手欢迎语
    steps:
      - id: start
        type: start
        next: respond
      - id: respond
        type: action
        action: action_response
        args:
          text: "您好，欢迎使用智能金融客服。我可以帮您查询账户、交易记录，办理贷款、信用卡业务，或提交投诉工单。请问有什么可以帮您？"
        next: end
      - id: end
        type: end
        next: []

  # 账户余额查询
  account_balance_query:
    name: 账户余额查询
    description: 查询银行账户余额、可用余额、冻结金额等信息
    steps:
      - id: start
        type: start
        next: ask_account
      - id: ask_account
        type: collect
        slot_name: bank_card_number
        response:
          text: "请提供您的银行卡号或账户号。"
        next: lookup_balance
      - id: lookup_balance
        type: action
        action: action_lookup_account_balance
        next: show_balance
      - id: show_balance
        type: action
        action: action_response
        args:
          text: "您的账户余额为：{{ slots.account_balance }}"
        next: end
      - id: end
        type: end
        next: []

  # 交易流水查询
  transaction_query:
    name: 交易流水查询
    description: 查询历史交易记录
    steps:
      - id: start
        type: start
        next: ask_account
      - id: ask_account
        type: collect
        slot_name: bank_card_number
        response:
          text: "请提供您的银行卡号。"
        next: ask_date
      - id: ask_date
        type: collect
        slot_name: transaction_date
        response:
          text: "请提供查询日期（如：昨天、2024-01-01）。"
        next: lookup_transaction
      - id: lookup_transaction
        type: action
        action: action_lookup_transaction
        next: show_transaction
      - id: show_transaction
        type: action
        action: action_response
        args:
          text: "查询到以下交易记录：{{ slots.transaction_list }}"
        next: end
      - id: end
        type: end
        next: []

  # 贷款申请
  loan_application:
    name: 贷款申请
    description: 引导客户完成贷款申请流程
    steps:
      - id: start
        type: start
        next: ask_loan_type
      - id: ask_loan_type
        type: collect
        slot_name: loan_type
        response:
          text: "请问您想申请哪种类型的贷款？（消费贷/经营贷/房贷/车贷）"
        next: ask_amount
      - id: ask_amount
        type: collect
        slot_name: loan_amount
        response:
          text: "请问您需要申请多少金额的贷款？"
        next: ask_term
      - id: ask_term
        type: collect
        slot_name: loan_term
        response:
          text: "请问您希望的贷款期限是多少个月？"
        next: ask_purpose
      - id: ask_purpose
        type: collect
        slot_name: loan_purpose
        response:
          text: "请简要说明贷款用途。"
        next: submit_application
      - id: submit_application
        type: action
        action: action_submit_loan_application
        next: show_result
      - id: show_result
        type: action
        action: action_response
        args:
          text: "您的贷款申请已提交成功！申请编号：{{ slots.application_id }}。我们将在3个工作日内完成审核，请留意短信通知。"
        next: end
      - id: end
        type: end
        next: []

  # 信用卡挂失
  credit_card_loss:
    name: 信用卡挂失
    description: 处理信用卡挂失申请
    steps:
      - id: start
        type: start
        next: ask_card_number
      - id: ask_card_number
        type: collect
        slot_name: credit_card_number
        response:
          text: "请提供需要挂失的信用卡号。"
        next: ask_reason
      - id: ask_reason
        type: collect
        slot_name: loss_reason
        response:
          text: "请说明挂失原因（如：卡片丢失、被盗、异常交易等）。"
        next: ask_identity
      - id: ask_identity
        type: collect
        slot_name: identity_verification
        response:
          text: "请提供身份验证信息（如：身份证后4位、预留手机号）。"
        next: submit_loss
      - id: submit_loss
        type: action
        action: action_submit_credit_card_loss
        next: show_result
      - id: show_result
        type: action
        action: action_response
        args:
          text: "您的信用卡挂失申请已受理。挂失后该卡将无法使用，如需补办新卡请前往柜台办理。"
        next: end
      - id: end
        type: end
        next: []

  # 投诉工单
  complaint_ticket:
    name: 投诉工单
    description: 创建投诉工单
    steps:
      - id: start
        type: start
        next: ask_ticket_type
      - id: ask_ticket_type
        type: collect
        slot_name: ticket_type
        response:
          text: "请问您要投诉的类型是什么？（转账问题/服务态度/系统故障/其他）"
        next: ask_transaction_id
      - id: ask_transaction_id
        type: collect
        slot_name: related_transaction_id
        response:
          text: "请提供相关的交易流水号（如有）。"
        next: ask_description
      - id: ask_description
        type: collect
        slot_name: problem_description
        response:
          text: "请详细描述您遇到的问题。"
        next: create_ticket
      - id: create_ticket
        type: action
        action: action_create_complaint_ticket
        next: show_result
      - id: show_result
        type: action
        action: action_response
        args:
          text: "您的投诉工单已创建成功！工单编号：{{ slots.ticket_id }}。我们将在24小时内处理，请耐心等待。"
        next: end
      - id: end
        type: end
        next: []

  # 人工客服
  human_handoff:
    name: 人工客服
    description: 转接人工客服
    steps:
      - id: start
        type: start
        next: respond
      - id: respond
        type: action
        action: action_response
        args:
          text: "好的，正在为您转接人工客服，请稍等..."
        next: end
      - id: end
        type: end
        next: []
```

#### 3.1.2 system_flows.yml（系统流程）

保持与电商客服相同的系统流程结构，修改文案为金融场景：

```yaml
flows:
  system_task_started:
    description: Flow for acknowledging that a new task has started
    name: task started acknowledgement
    steps:
      - id: start
        type: start
        next: acknowledge
      - id: acknowledge
        type: action
        action: action_response
        args:
          mode: static
          text: "好的，我们先处理{{ context.started_flow_name }}。"
        next: end
      - id: end
        type: end
        next: []

  system_task_resumed:
    description: Flow for acknowledging that a paused task has been resumed
    name: task resumed acknowledgement
    steps:
      - id: start
        type: start
        next: acknowledge
      - id: acknowledge
        type: action
        action: action_response
        args:
          mode: static
          text: "好的，我们继续刚才的{{ context.resumed_flow_name }}。"
        next: end
      - id: end
        type: end
        next: []

  system_collect_information:
    description: Flow for asking the user for a slot value during a collect step
    name: collect information
    steps:
      - id: start
        type: start
        next: ask
      - id: ask
        type: action
        action: action_response
        args: context.response
        next: listen
      - id: listen
        type: action
        action: action_listen
        next: end
      - id: end
        type: end
        next: []

  system_task_interrupted:
    description: Flow for acknowledging that the current task has been interrupted
    name: task interrupted acknowledgement
    steps:
      - id: start
        type: start
        next: acknowledge
      - id: acknowledge
        type: action
        action: action_response
        args:
          mode: static
          text: "好的，我们先把{{ context.interrupted_flow_name }}放一放，先处理{{ context.started_flow_name }}。"
        next: end
      - id: end
        type: end
        next: []

  system_task_canceled:
    description: Flow for acknowledging that the current task was canceled
    name: task canceled acknowledgement
    steps:
      - id: start
        type: start
        next: acknowledge
      - id: acknowledge
        type: action
        action: action_response
        args:
          mode: static
          text: "好的，{{ context.canceled_flow_name }}先帮你取消。"
        next: end
      - id: end
        type: end
        next: []

  system_cannot_handle:
    description: Flow for handling requests the assistant cannot support
    name: cannot handle request
    steps:
      - id: start
        type: start
        next:
          - if: "context.get('reason') == 'clarification_rejected'"
            then: clarification_rejected
          - if: "context.get('reason') == 'not_supported'"
            then: not_supported
          - if: "context.get('reason') == 'no_relevant_answer'"
            then: no_relevant_answer
          - else: ask_rephrase
      - id: clarification_rejected
        type: action
        action: action_response
        args:
          mode: rephrase
          text: "看来我刚才理解偏了。您可以重新描述一下您的需求，比如查询账户、办理贷款或提交投诉？"
          prompt: |
            你是一个中文金融客服助手，语气专业、友好、简洁。
            请基于下面的建议回复，生成一句更自然的中文回复，保持原意，不要扩写。
            对话上下文：
            {history}
            用户最后一句：
            用户：{user_message}
            建议回复：{current_response}
            改写后的回复：
        next: end
      - id: not_supported
        type: action
        action: action_response
        args:
          mode: rephrase
          text: "我理解您的意思，不过这个业务目前还没有接入线上办理。"
          prompt: |
            你是一个中文金融客服助手，语气专业、友好、简洁。
            请基于下面的建议回复，生成一句更自然的中文回复，保持原意，不要扩写。
            对话上下文：
            {history}
            用户最后一句：
            用户：{user_message}
            建议回复：{current_response}
            改写后的回复：
        next: end
      - id: no_relevant_answer
        type: action
        action: action_response
        args:
          mode: rephrase
          text: "我暂时没有查到相关信息。您可以换个说法，或者提供更具体的账户或交易信息。"
          prompt: |
            你是一个中文金融客服助手，语气专业、友好、简洁。
            请基于下面的建议回复，生成一句更自然的中文回复，保持原意，不要扩写。
            对话上下文：
            {history}
            用户最后一句：
            用户：{user_message}
            建议回复：{current_response}
            改写后的回复：
        next: end
      - id: ask_rephrase
        type: action
        action: action_response
        args:
          mode: rephrase
          text: "抱歉，我没有完全理解您的需求。您可以具体说明一下想办理什么业务吗？比如查询账户、申请贷款或挂失信用卡。"
          prompt: |
            你是一个中文金融客服助手，语气专业、友好、简洁。
            请基于下面的建议回复，生成一句更自然的中文回复，保持原意，不要扩写。
            对话上下文：
            {history}
            用户最后一句：
            用户：{user_message}
            建议回复：{current_response}
            改写后的回复：
        next: end
      - id: end
        type: end
        next: []
```

---

### 3.2 业务 Action 实现（atguigu/task/action/customer/）

#### 3.2.1 share.py（金融 API 调用封装）

```python
from urllib.parse import quote
from atguigu.conf.config import settings
from atguigu.infrastructure.http_client import get_http_client

http_client = get_http_client()

def _base_url() -> str:
    return settings.finance_api_base_url.rstrip("/")

def _extract_data(result: dict | None) -> dict | None:
    data = result.get("data") if isinstance(result, dict) else None
    return data if isinstance(data, dict) else None

# 账户查询
async def fetch_account(account_id: str) -> dict | None:
    try:
        r = await http_client.get(f"{_base_url()}/accounts/{quote(account_id)}")
        return _extract_data(r.json())
    except Exception:
        return None

# 银行卡查询
async def fetch_bank_card(card_number: str) -> dict | None:
    try:
        r = await http_client.get(f"{_base_url()}/bank-cards/{quote(card_number)}")
        return _extract_data(r.json())
    except Exception:
        return None

# 交易流水查询
async def fetch_transactions(card_number: str, date: str) -> dict | None:
    try:
        r = await http_client.get(
            f"{_base_url()}/transactions",
            params={"card_number": card_number, "date": date}
        )
        return _extract_data(r.json())
    except Exception:
        return None

# 贷款申请提交
async def submit_loan_application(payload: dict) -> dict | None:
    try:
        r = await http_client.post(f"{_base_url()}/loan-applications", json=payload)
        return _extract_data(r.json())
    except Exception:
        return None

# 信用卡挂失
async def submit_credit_card_loss(card_number: str, reason: str, identity: str) -> dict | None:
    try:
        r = await http_client.post(
            f"{_base_url()}/credit-cards/{quote(card_number)}/loss",
            json={"reason": reason, "identity_verification": identity}
        )
        return _extract_data(r.json())
    except Exception:
        return None

# 创建投诉工单
async def create_ticket(payload: dict) -> dict | None:
    try:
        r = await http_client.post(f"{_base_url()}/tickets", json=payload)
        return _extract_data(r.json())
    except Exception:
        return None
```

#### 3.2.2 lookup_account_balance.py

```python
from typing import Any
from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult
from atguigu.task.action.customer.share import fetch_bank_card

class LookUpAccountBalanceAction(Action):
    name = "action_lookup_account_balance"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        """查询账户余额"""
        bank_card_number = state.active_task.slots.get("bank_card_number")
        payload = await fetch_bank_card(bank_card_number)

        if payload is None:
            return ActionResult(slot_updates={
                "account_balance": "查询失败，请稍后再试"
            })

        balance = payload.get("balance", 0)
        available = payload.get("available_balance", 0)
        frozen = payload.get("frozen_amount", 0)

        balance_info = f"总余额 ¥{balance}，可用余额 ¥{available}，冻结金额 ¥{frozen}"
        return ActionResult(slot_updates={
            "account_balance": balance_info
        })
```

#### 3.2.3 lookup_transaction.py

```python
from typing import Any
from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult
from atguigu.task.action.customer.share import fetch_transactions

class LookUpTransactionAction(Action):
    name = "action_lookup_transaction"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        """查询交易流水"""
        bank_card_number = state.active_task.slots.get("bank_card_number")
        transaction_date = state.active_task.slots.get("transaction_date")

        payload = await fetch_transactions(bank_card_number, transaction_date)

        if payload is None:
            return ActionResult(slot_updates={
                "transaction_list": "查询失败，请稍后再试"
            })

        transactions = payload.get("transactions", [])
        if not transactions:
            return ActionResult(slot_updates={
                "transaction_list": "该时间段内没有交易记录"
            })

        # 格式化交易列表
        lines = []
        for tx in transactions[:5]:  # 最多显示5条
            amount = tx.get("amount", 0)
            tx_type = "收入" if amount > 0 else "支出"
            desc = tx.get("description", "")
            time = tx.get("time", "")
            lines.append(f"{time} {tx_type} ¥{abs(amount)} {desc}")

        result = "\n".join(lines)
        if len(transactions) > 5:
            result += f"\n...共 {len(transactions)} 笔交易"

        return ActionResult(slot_updates={
            "transaction_list": result
        })
```

#### 3.2.4 submit_loan_application.py

```python
from typing import Any
from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult
from atguigu.task.action.customer.share import submit_loan_application

class SubmitLoanApplicationAction(Action):
    name = "action_submit_loan_application"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        """提交贷款申请"""
        payload = {
            "loan_type": state.active_task.slots.get("loan_type"),
            "amount": state.active_task.slots.get("loan_amount"),
            "term_months": state.active_task.slots.get("loan_term"),
            "purpose": state.active_task.slots.get("loan_purpose"),
            "customer_id": state.sender_id
        }

        result = await submit_loan_application(payload)

        if result is None:
            return ActionResult(slot_updates={
                "application_id": "申请提交失败，请稍后再试"
            })

        return ActionResult(slot_updates={
            "application_id": result.get("application_id", "未知")
        })
```

#### 3.2.5 submit_credit_card_loss.py

```python
from typing import Any
from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult
from atguigu.task.action.customer.share import submit_credit_card_loss

class SubmitCreditCardLossAction(Action):
    name = "action_submit_credit_card_loss"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        """提交信用卡挂失"""
        card_number = state.active_task.slots.get("credit_card_number")
        reason = state.active_task.slots.get("loss_reason")
        identity = state.active_task.slots.get("identity_verification")

        result = await submit_credit_card_loss(card_number, reason, identity)

        if result is None:
            return ActionResult(messages=[
                {"text": "挂失申请提交失败，请稍后再试或拨打客服热线。"}
            ])

        return ActionResult(messages=[
            {"text": "信用卡挂失申请已受理成功。"}
        ])
```

#### 3.2.6 create_complaint_ticket.py

```python
from typing import Any
from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult
from atguigu.task.action.customer.share import create_ticket

class CreateComplaintTicketAction(Action):
    name = "action_create_complaint_ticket"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        """创建投诉工单"""
        payload = {
            "ticket_type": state.active_task.slots.get("ticket_type"),
            "related_transaction_id": state.active_task.slots.get("related_transaction_id"),
            "problem_description": state.active_task.slots.get("problem_description"),
            "customer_id": state.sender_id
        }

        result = await create_ticket(payload)

        if result is None:
            return ActionResult(slot_updates={
                "ticket_id": "工单创建失败，请稍后再试"
            })

        return ActionResult(slot_updates={
            "ticket_id": result.get("ticket_id", "未知")
        })
```

---

### 3.3 领域上下文模型（atguigu/domain/contexts.py）

```python
from typing import Dict, Any
from pydantic import BaseModel


class TaskContext(BaseModel):
    """业务任务上下文"""
    flow_id: str
    step_id: str | None = None
    slots: Dict[str, Any] = {}


class SystemContext(BaseModel):
    """系统流程上下文"""
    flow_id: str
    step_id: str | None = None


class StartedSystemContext(SystemContext):
    started_flow_id: str = ""
    started_flow_name: str = ""


class InterruptedSystemContext(SystemContext):
    interrupted_flow_id: str = ""
    interrupted_flow_name: str = ""
    started_flow_id: str = ""
    started_flow_name: str = ""


class ResumedSystemContext(SystemContext):
    resumed_flow_id: str = ""
    resumed_flow_name: str = ""


class CanceledSystemContext(SystemContext):
    canceled_flow_id: str = ""
    canceled_flow_name: str = ""


class CollectedSystemContext(SystemContext):
    slot_name: str = ""
    response: Dict[str, Any] = {}
```

---

### 3.4 配置文件（atguigu/conf/config.py）

```python
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_project_root() -> Path:
    current = Path(__file__).resolve().parent
    for parent in current.parents:
        if (parent / '.env').exists():
            return parent
    return current.parents[1]


ENV_FILE = find_project_root() / '.env'


class Settings(BaseSettings):
    # LLM
    llm_api_key: str
    llm_model: str
    llm_base_url: str

    # 数据库
    database_url: str

    # 金融业务 API
    finance_api_base_url: str

    # 服务器
    app_host: str
    app_port: int

    model_config = SettingsConfigDict(env_file=ENV_FILE)


settings = Settings()
```

---

---

### 3.6 Prompt 模板（atguigu/prompts/jinja2/）

#### turn_plan.jinja2
```jinja2
你是一个专业的金融客服助手。请根据用户的消息和当前对话状态，决定下一步的行动。

当前对话历史：
{{ history }}

用户最新消息：
{{ user_message }}

当前任务状态：
{{ current_state }}

可用的业务流程：
{{ available_flows }}

请分析用户意图，决定：
1. 是否需要启动新的业务流程
2. 是否需要继续当前流程
3. 是否需要切换到其他流程
4. 是否需要澄清用户意图

输出格式：
{
  "intent": "意图类型",
  "flow_id": "流程ID（如有）",
  "confidence": 0.95,
  "reasoning": "推理说明"
}
```

#### chitchat_respond.jinja2
```jinja2
你是一个专业的金融客服助手。当用户的问题与金融业务无关时，请友好地回应并引导用户回到业务场景。

对话历史：
{{ history }}

用户消息：
{{ user_message }}

请生成一个自然、友好的回复，并适当引导用户咨询金融相关问题。
```

#### clarify_respond.jinja2
```jinja2
你是一个专业的金融客服助手。当用户意图不明确时，请主动澄清用户需求。

对话历史：
{{ history }}

用户消息：
{{ user_message }}

可能的意图：
{{ possible_intents }}

请生成一个澄清回复，帮助用户明确他们的需求。
```

#### knowledge_respond.jinja2
```jinja2
你是一个专业的金融客服助手。请根据知识库内容回答用户的问题。

对话历史：
{{ history }}

用户消息：
{{ user_message }}

相关知识：
{{ knowledge_content }}

请基于知识库内容生成专业、准确的回复。
```

---

### 3.7 API 接口（atguigu/api/server.py）

```python
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from atguigu.infrastructure.http_client import init_http_pool, close_http_pool, get_http_client
from atguigu.infrastructure.database import init_db_pool, close_db_pool, get_db_session


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    init_http_pool(
        max_connections=50,
        max_keepalive_connections=20,
        connect_timeout=5.0,
        read_timeout=10.0,
        write_timeout=10.0,
        pool_timeout=5.0
    )
    print("[OK] HTTP connection pool initialized")

    init_db_pool(
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
        echo=False
    )
    print("[OK] Database connection pool initialized")

    yield

    await close_http_pool()
    print("[OK] HTTP connection pool closed")

    await close_db_pool()
    print("[OK] Database connection pool closed")


def create_app() -> FastAPI:
    app = FastAPI(
        description="金融智能客服系统 API",
        lifespan=lifespan
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_router(app)
    return app


def register_router(app: FastAPI):
    @app.get("/get-account/{card_number}")
    async def fetch_account(card_number: str):
        """查询账户信息"""
        client = get_http_client()
        response = await client.get(f'http://localhost:18082/api/v1/bank-cards/{card_number}')
        return response.json()

    @app.get("/get-transactions/{card_number}")
    async def fetch_transactions(card_number: str, date: str = None):
        """查询交易流水"""
        client = get_http_client()
        params = {"date": date} if date else {}
        response = await client.get(
            f'http://localhost:18082/api/v1/transactions',
            params={"card_number": card_number, **params}
        )
        return response.json()

    @app.post("/submit-loan")
    async def submit_loan(payload: dict):
        """提交贷款申请"""
        client = get_http_client()
        response = await client.post(
            'http://localhost:18082/api/v1/loan-applications',
            json=payload
        )
        return response.json()

    @app.post("/credit-card-loss/{card_number}")
    async def credit_card_loss(card_number: str, payload: dict):
        """信用卡挂失"""
        client = get_http_client()
        response = await client.post(
            f'http://localhost:18082/api/v1/credit-cards/{card_number}/loss',
            json=payload
        )
        return response.json()

    @app.post("/create-ticket")
    async def create_ticket(payload: dict):
        """创建投诉工单"""
        client = get_http_client()
        response = await client.post(
            'http://localhost:18082/api/v1/tickets',
            json=payload
        )
        return response.json()

    @app.get("/db-test")
    async def db_test():
        """测试数据库连接"""
        from sqlalchemy import text
        try:
            async with get_db_session() as session:
                result = await session.execute(text("SELECT 1"))
                return {"status": "ok", "result": result.scalar()}
        except Exception as e:
            return {"status": "error", "message": str(e)}


if __name__ == '__main__':
    uvicorn.run(app=create_app(), port=8000, host="0.0.0.0")
```

---

## 四、Action 注册配置

在 `atguigu/task/action/customer/__init__.py` 中注册所有金融业务 Action：

```python
from atguigu.task.action.customer.lookup_account_balance import LookUpAccountBalanceAction
from atguigu.task.action.customer.lookup_transaction import LookUpTransactionAction
from atguigu.task.action.customer.submit_loan_application import SubmitLoanApplicationAction
from atguigu.task.action.customer.submit_credit_card_loss import SubmitCreditCardLossAction
from atguigu.task.action.customer.create_complaint_ticket import CreateComplaintTicketAction

__all__ = [
    "LookUpAccountBalanceAction",
    "LookUpTransactionAction",
    "SubmitLoanApplicationAction",
    "SubmitCreditCardLossAction",
    "CreateComplaintTicketAction",
]
```

---

## 五、金融业务数据模型（finance-data）

### 5.1 客户（Customer）
```json
{
  "customer_id": "C001",
  "name": "张三",
  "id_card": "110101199001011234",
  "phone": "13800138000",
  "email": "zhangsan@example.com"
}
```

### 5.2 银行账户（Account）
```json
{
  "account_id": "ACC001",
  "customer_id": "C001",
  "account_type": "savings",
  "balance": 50000.00,
  "available_balance": 45000.00,
  "frozen_amount": 5000.00,
  "currency": "CNY",
  "status": "active"
}
```

### 5.3 银行卡（Bank Card）
```json
{
  "card_number": "6222021234567890123",
  "account_id": "ACC001",
  "card_type": "debit",
  "status": "active"
}
```

### 5.4 信用卡（Credit Card）
```json
{
  "card_number": "4000123456789012",
  "customer_id": "C001",
  "credit_limit": 50000.00,
  "used_amount": 10000.00,
  "available_credit": 40000.00,
  "status": "active"
}
```

### 5.5 贷款产品（Loan Product）
```json
{
  "product_id": "LOAN001",
  "name": "消费贷款",
  "interest_rate": 4.35,
  "max_amount": 200000,
  "max_term_months": 60,
  "repayment_method": "equal_installment"
}
```

### 5.6 贷款申请（Loan Application）
```json
{
  "application_id": "LA20240101001",
  "customer_id": "C001",
  "product_id": "LOAN001",
  "amount": 100000,
  "term_months": 24,
  "purpose": "装修",
  "status": "pending",
  "created_at": "2024-01-01T10:00:00Z"
}
```

### 5.7 交易流水（Transaction）
```json
{
  "transaction_id": "TXN20240101001",
  "account_id": "ACC001",
  "amount": -500.00,
  "type": "consumption",
  "description": "超市消费",
  "time": "2024-01-01T14:30:00Z",
  "balance_after": 49500.00
}
```

### 5.8 投诉工单（Ticket）
```json
{
  "ticket_id": "TK20240101001",
  "customer_id": "C001",
  "ticket_type": "transfer_issue",
  "related_transaction_id": "TXN20240101001",
  "problem_description": "转账未到账",
  "status": "open",
  "created_at": "2024-01-01T16:00:00Z"
}
```

---

## 六、生成指令

请根据以上提示词，在指定路径生成完整的金融智能客服系统代码：

生成的代码需要：
- 保持与电商客服相同的架构模式
- 代码结构与电商客服相同
- 不要漏掉相关内容
- 使用相同的流程引擎和 Action 机制
- 支持多轮对话和槽位收集
- 支持流程切换、恢复和取消
- 金融业务文案专业、准确
- 项目使用uv环境建设