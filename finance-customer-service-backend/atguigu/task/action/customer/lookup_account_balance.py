from typing import Any

from atguigu.domain.messages import BotMessage
from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult
from atguigu.task.action.customer.share import fetch_account


class LookUpAccountBalanceAction(Action):
    name = "action_lookup_account_balance"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        """查询账户余额（中台接口: GET /api/v1/accounts/{account_no}）"""
        account_number = state.active_task.slots.get("account_number")

        try:
            resp = await fetch_account(account_number)
            # 中台返回: {"code": 0, "data": {"account_status": "normal", "balance_amount": "2125.00", ...}}
            if resp.get("code") != 0:
                return ActionResult(
                    messages=[BotMessage(text=f"抱歉，查询失败：{resp.get('message', '未知错误')}")]
                )

            data = resp.get("data", {})
            balance = data.get("balance_amount", "0.00")
            frozen = data.get("frozen_amount", "0.00")
            account_status = data.get("account_status", "")
            product = data.get("account_product", {})
            product_name = product.get("product_name", "")
            account_type = product.get("account_type", "")

            return ActionResult(
                slot_updates={
                    "account_balance": balance,
                    "account_type": product_name or account_type,
                }
            )
        except Exception as e:
            return ActionResult(
                messages=[BotMessage(text=f"抱歉，系统暂时无法查询账户余额，请稍后再试。错误信息：{str(e)}")]
            )
