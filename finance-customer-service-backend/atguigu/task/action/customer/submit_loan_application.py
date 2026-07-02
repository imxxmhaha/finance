from typing import Any

from atguigu.api.logger import logger
from atguigu.domain.messages import BotMessage
from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult
from atguigu.task.action.customer.share import submit_loan_application
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
            resp = await submit_loan_application(
                customer_no=account_number,
                apply_amount=loan_amount,
                loan_purpose=loan_purpose,
                apply_term_months=apply_term_months,
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
