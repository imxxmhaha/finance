from typing import Any

from atguigu.domain.messages import BotMessage
from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult
from atguigu.task.action.customer.share import change_account_status


class SubmitCreditCardLossAction(Action):
    name = "action_submit_credit_card_loss"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        """提交银行卡挂失（中台接口: POST /api/v1/accounts/{account_no}/status-changes）"""
        card_number = state.active_task.slots.get("card_number")
        loss_reason = state.active_task.slots.get("loss_reason")

        try:
            resp = await change_account_status(
                account_no=card_number,
                target_status="FROZEN",
                reason=f"客户申请挂失：{loss_reason}"
            )
            # 中台返回: {"code": 0, "data": {"change_no": "...", "status": "..."}}
            if resp.get("code") != 0:
                return ActionResult(
                    messages=[BotMessage(text=f"抱歉，挂失失败：{resp.get('message', '未知错误')}")]
                )

            data = resp.get("data", {})
            status = data.get("status", "已受理")
            return ActionResult(
                slot_updates={"loss_status": status}
            )
        except Exception as e:
            return ActionResult(
                messages=[BotMessage(text=f"抱歉，系统暂时无法提交挂失申请，请稍后再试。错误信息：{str(e)}")]
            )
