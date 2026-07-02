from typing import Any

from atguigu.api.logger import logger
from atguigu.domain.messages import BotMessage
from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult
from atguigu.task.action.customer.share import (
    fetch_credit_limits,
    fetch_customer_no_by_account,
    fetch_loan_product_detail,
    submit_loan_application,
)
from atguigu.task.action.customer.slot_parser import parse_amount, parse_term


class SubmitLoanApplicationAction(Action):
    name = "action_submit_loan_application"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        """提交贷款申请（中台接口: POST /api/v1/loan/applications）"""
        account_number = state.active_task.slots.get("account_number")
        loan_amount_raw = state.active_task.slots.get("loan_amount")
        loan_purpose = state.active_task.slots.get("loan_purpose")
        loan_term_raw = state.active_task.slots.get("loan_term")

        # 解析金额: "一亿" -> 100000000, "50万" -> 500000
        parsed_amount = await parse_amount(str(loan_amount_raw))
        if parsed_amount is None:
            return ActionResult(
                messages=[BotMessage(text=f"抱歉，无法识别金额「{loan_amount_raw}」，请重新输入（如：10万、500000）。")]
            )
        loan_amount = str(parsed_amount)
        logger.info(f"贷款申请 金额解析: '{loan_amount_raw}' -> {loan_amount}")

        # 解析期限: "3年" -> 36, "半年" -> 6
        parsed_term = await parse_term(str(loan_term_raw))
        if parsed_term is None:
            return ActionResult(
                messages=[BotMessage(text=f"抱歉，无法识别贷款期限「{loan_term_raw}」，请重新输入（如：1年、36个月）。")]
            )
        apply_term_months = str(parsed_term)
        logger.info(f"贷款申请 期限解析: '{loan_term_raw}' -> {apply_term_months}个月")

        try:
            # ---- 0. 通过账户号反查客户号 ----
            customer_no = await fetch_customer_no_by_account(account_number)
            if not customer_no:
                return ActionResult(
                    messages=[BotMessage(text=f"抱歉，无法识别账户号「{account_number}」，请确认账户号是否正确。")]
                )
            logger.info(f"贷款申请 账户号={account_number} -> 客户号={customer_no}")

            # ---- 1. 查询客户授信额度 ----
            credit_resp = await fetch_credit_limits(customer_no)
            if credit_resp.get("code") != 0:
                return ActionResult(
                    messages=[BotMessage(text=f"抱歉，查询授信额度失败：{credit_resp.get('message', '未知错误')}")]
                )
            credit_list = credit_resp.get("data", {}).get("list", [])
            if not credit_list:
                return ActionResult(
                    messages=[BotMessage(text="抱歉，您当前没有可用的授信额度，请先申请授信。")]
                )

            # 取第一个有效额度
            credit = credit_list[0]
            limit_no = credit.get("limit_no")
            available = float(credit.get("available_limit_amount", 0))
            product_code = credit.get("product_code")

            # ---- 2. 额度不足时友好提示 ----
            if parsed_amount > available:
                return ActionResult(
                    messages=[BotMessage(
                        text=f"抱歉，您的申请额度不足。当前可用授信额度为 {available:,.2f} 元，"
                             f"您申请的金额为 {parsed_amount:,.2f} 元，"
                             f"差额 {parsed_amount - available:,.2f} 元。"
                             f"请调整申请金额后重试。"
                    )]
                )

            # ---- 3. 查询产品详情，获取还款方式 ----
            product_resp = await fetch_loan_product_detail(product_code)
            if product_resp.get("code") != 0:
                return ActionResult(
                    messages=[BotMessage(text=f"抱歉，查询产品信息失败：{product_resp.get('message', '未知错误')}")]
                )
            product_detail = product_resp.get("data", {}).get("product_detail", {})
            repayment_method = product_detail.get("repayment_method", "equal_principal_interest")
            logger.info(f"贷款申请 产品={product_code}, 还款方式={repayment_method}")

            # ---- 4. 提交贷款申请 ----
            resp = await submit_loan_application(
                customer_no=customer_no,
                apply_amount=loan_amount,
                loan_purpose=loan_purpose,
                apply_term_months=apply_term_months,
                limit_no=limit_no,
                repayment_method=repayment_method,
            )
            # 中台返回: {"code": 0, "data": {"application_no": "...", "application_status": "..."}}
            if resp.get("code") != 0:
                return ActionResult(
                    messages=[BotMessage(text=f"抱歉，提交失败：{resp.get('message', '未知错误')}")]
                )

            data = resp.get("data", {})
            application_no = data.get("application_no", "")
            status = data.get("application_status", data.get("status", "审核中"))
            return ActionResult(
                slot_updates={
                    "loan_status": status,
                    "loan_application_no": application_no,
                }
            )
        except Exception as e:
            return ActionResult(
                messages=[BotMessage(text=f"抱歉，系统暂时无法提交贷款申请，请稍后再试。错误信息：{str(e)}")]
            )
