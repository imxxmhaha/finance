"""
金融 API 调用封装
对接中台服务 Finance Data API（http://localhost:8000/docs）
"""
import uuid
from typing import Any, Dict, Optional

from atguigu.conf.config import settings
from atguigu.infrastructure.http_client import get_http_client
from atguigu.api.logger import logger


# ============================================================
# 账户相关
# ============================================================

async def fetch_account(account_no: str) -> Dict[str, Any]:
    """
    查询账户详情（含余额）
    对应接口: GET /api/v1/accounts/{account_no}
    """
    client = get_http_client()
    uri = f'{settings.finance_api_base_url}/api/v1/accounts/{account_no}'
    response = await client.get(uri)
    logger.info(f"invoke {uri} resp: {response.json()}")
    return response.json()


async def fetch_account_transactions(
    account_no: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    transaction_type: Optional[str] = None,
    page_no: int = 1,
    page_size: int = 20
) -> Dict[str, Any]:
    """
    查询账户交易明细
    对应接口: GET /api/v1/accounts/{account_no}/transactions
    """
    client = get_http_client()
    params = {"page_no": page_no, "page_size": page_size}
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time
    if transaction_type:
        params["transaction_type"] = transaction_type
    uri = f'{settings.finance_api_base_url}/api/v1/accounts/{account_no}/transactions'
    response = await client.get(
        uri,
        params=params
    )
    logger.info(f"invoke {uri} resp: {response.json()}")
    return response.json()


async def change_account_status(
    account_no: str,
    target_status: str,
    reason: str
) -> Dict[str, Any]:
    """
    变更账户状态（用于挂失等）
    对应接口: POST /api/v1/accounts/{account_no}/status-changes
    """
    client = get_http_client()
    changes_uri = f'{settings.finance_api_base_url}/api/v1/accounts/{account_no}/status-changes'

    response = await client.post(
        changes_uri,
        json={
            "request_no": str(uuid.uuid4()),
            "target_status": target_status,
            "reason": reason
        }
    )
    logger.info(f"invoke {changes_uri} resp: {response.json()}")
    return response.json()


# ============================================================
# 客户相关
# ============================================================

async def fetch_customer(customer_no: str) -> Dict[str, Any]:
    """
    查询客户档案
    对应接口: GET /api/v1/customers/{customer_no}
    """
    client = get_http_client()
    uri = f'{settings.finance_api_base_url}/api/v1/customers/{customer_no}'
    response = await client.get(
        uri
    )
    logger.info(f"invoke {uri} resp: {response.json()}")
    return response.json()


async def fetch_customer_no_by_account(account_no: str) -> Optional[str]:
    """
    通过账户号反查客户号
    调用 GET /api/v1/accounts/{account_no} 获取 customer_no
    """
    client = get_http_client()
    uri = f'{settings.finance_api_base_url}/api/v1/accounts/{account_no}'
    response = await client.get(uri)
    account_resp = response.json()
    logger.info(f"invoke {uri} resp: {account_resp}")
    if account_resp.get("code") != 0:
        return None
    return account_resp.get("data", {}).get("customer_no")


async def fetch_customer_accounts(
    customer_no: str,
    account_status: Optional[str] = None
) -> Dict[str, Any]:
    """
    查询客户账户列表
    对应接口: GET /api/v1/customers/{customer_no}/accounts
    """
    client = get_http_client()
    params = {}
    if account_status:
        params["account_status"] = account_status
    accounts_uri = f'{settings.finance_api_base_url}/api/v1/customers/{customer_no}/accounts'
    response = await client.get(
        accounts_uri,
        params=params
    )
    logger.info(f"invoke {accounts_uri} resp: {response.json()}")
    return response.json()


# ============================================================
# 贷款相关
# ============================================================

async def submit_loan_application(
    customer_no: str,
    apply_amount: str,
    loan_purpose: str,
    apply_term_months: str,
    limit_no: Optional[str] = None,
    repayment_method: Optional[str] = None
) -> Dict[str, Any]:
    """
    提交贷款申请
    对应接口: POST /api/v1/loan/applications
    """
    client = get_http_client()
    payload = {
        "request_no": str(uuid.uuid4()),
        "customer_no": customer_no,
        "apply_amount": float(apply_amount),
        "apply_term_months": int(apply_term_months),
        "loan_purpose": loan_purpose,
    }
    if limit_no:
        payload["limit_no"] = limit_no
    if repayment_method:
        payload["repayment_method"] = repayment_method
    applications_uri = f'{settings.finance_api_base_url}/api/v1/loan/applications'
    response = await client.post(
        applications_uri,
        json=payload
    )
    logger.info(f"invoke {applications_uri} resp: {response.json()}")
    return response.json()


async def fetch_loan_application(application_no: str) -> Dict[str, Any]:
    """
    查询贷款申请详情
    对应接口: GET /api/v1/loan/applications/{application_no}
    """
    client = get_http_client()
    uri = f'{settings.finance_api_base_url}/api/v1/loan/applications/{application_no}'
    response = await client.get(
        uri
    )
    logger.info(f"invoke {uri} resp: {response.json()}")
    return response.json()


async def fetch_loan_products(
    loan_type: Optional[str] = None,
    currency_code: Optional[str] = None
) -> Dict[str, Any]:
    """
    查询贷款产品
    对应接口: GET /api/v1/loan/products
    """
    client = get_http_client()
    params = {}
    if loan_type:
        params["loan_type"] = loan_type
    if currency_code:
        params["currency_code"] = currency_code

    products_uri = f'{settings.finance_api_base_url}/api/v1/loan/products'
    response = await client.get(
        products_uri,
        params=params
    )
    logger.info(f"invoke {products_uri} resp: {response.json()}")
    return response.json()


async def fetch_credit_limits(customer_no: str) -> Dict[str, Any]:
    """
    查询客户授信额度列表
    对应接口: GET /api/v1/customers/{customer_no}/credit-limits
    """
    client = get_http_client()
    uri = f'{settings.finance_api_base_url}/api/v1/customers/{customer_no}/credit-limits'
    response = await client.get(uri)
    logger.info(f"invoke {uri} resp: {response.json()}")
    return response.json()


async def fetch_loan_product_detail(product_code: str) -> Dict[str, Any]:
    """
    查询贷款产品详情（含还款方式等）
    对应接口: GET /api/v1/loan/products/{product_code}
    """
    client = get_http_client()
    uri = f'{settings.finance_api_base_url}/api/v1/loan/products/{product_code}'
    response = await client.get(uri)
    logger.info(f"invoke {uri} resp: {response.json()}")
    return response.json()


# ============================================================
# 客服工单
# ============================================================

async def create_support_ticket(
    customer_no: str,
    ticket_type: str,
    ticket_title: str,
    ticket_content: str,
    related_type: str = "none",
    related_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    创建客服工单（投诉/建议）
    对应接口: POST /api/v1/support/tickets
    中台 related_type: none, account_transaction, wealth_order,
        loan_contract, loan_application, repayment_bill,
        collection_case, support_ticket, risk_event, fee_reduction
    """
    client = get_http_client()
    payload = {
        "request_no": str(uuid.uuid4()),
        "customer_no": customer_no,
        "ticket_type": ticket_type,
        "ticket_title": ticket_title,
        "ticket_content": ticket_content,
        "related_type": related_type,
    }
    # related_type="none" 时 related_id 必须为 null；非 none 时必须是有效整数
    if related_type != "none" and related_id is not None:
        payload["related_id"] = related_id
    tickets_uri = f'{settings.finance_api_base_url}/api/v1/support/tickets'
    response = await client.post(
        tickets_uri,
        json=payload
    )
    logger.info(f"invoke {tickets_uri}, payload:{payload} resp: {response.json()}")
    return response.json()


async def fetch_support_ticket(ticket_no: str) -> Dict[str, Any]:
    """
    查询客服工单详情
    对应接口: GET /api/v1/support/tickets/{ticket_no}
    """
    client = get_http_client()
    uri = f'{settings.finance_api_base_url}/api/v1/support/tickets/{ticket_no}'
    response = await client.get(
        uri
    )
    logger.info(f"invoke {uri} resp: {response.json()}")
    return response.json()


async def submit_ticket_feedback(
    ticket_no: str,
    confirm_status: str,
    satisfaction_score: int,
    feedback_content: str
) -> Dict[str, Any]:
    """
    提交工单反馈
    对应接口: POST /api/v1/support/tickets/{ticket_no}/feedback
    """
    client = get_http_client()
    feedback_uri = f'{settings.finance_api_base_url}/api/v1/support/tickets/{ticket_no}/feedback'
    response = await client.post(
        feedback_uri,
        json={
            "request_no": str(uuid.uuid4()),
            "confirm_status": confirm_status,
            "satisfaction_score": satisfaction_score,
            "feedback_content": feedback_content
        }
    )
    logger.info(f"invoke {feedback_uri} resp: {response.json()}")
    return response.json()


# ============================================================
# 还款相关
# ============================================================

async def fetch_repayment_bills(
    customer_no: Optional[str] = None,
    contract_no: Optional[str] = None,
    bill_status: Optional[str] = None,
    page_no: int = 1,
    page_size: int = 20
) -> Dict[str, Any]:
    """
    查询还款账单
    对应接口: GET /api/v1/repayment/bills
    """
    client = get_http_client()
    params = {"page_no": page_no, "page_size": page_size}
    if customer_no:
        params["customer_no"] = customer_no
    if contract_no:
        params["contract_no"] = contract_no
    if bill_status:
        params["bill_status"] = bill_status

    bills_uri = f'{settings.finance_api_base_url}/api/v1/repayment/bills'
    response = await client.get(
        bills_uri,
        params=params
    )
    logger.info(f"invoke {bills_uri} resp: {response.json()}")
    return response.json()


# ============================================================
# 基础数据
# ============================================================

async def fetch_branches(
    branch_status: Optional[str] = None,
    province: Optional[str] = None,
    city: Optional[str] = None
) -> Dict[str, Any]:
    """
    查询可用机构树
    对应接口: GET /api/v1/branches
    """
    client = get_http_client()
    params = {}
    if branch_status:
        params["branch_status"] = branch_status
    if province:
        params["province"] = province
    if city:
        params["city"] = city

    branches_uri = f'{settings.finance_api_base_url}/api/v1/branches'
    response = await client.get(
        branches_uri,
        params=params
    )
    logger.info(f"invoke {branches_uri} resp: {response.json()}")
    return response.json()
