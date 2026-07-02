from typing import Any

from atguigu.domain.messages import BotMessage
from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult
from atguigu.task.action.customer.share import create_support_ticket


class CreateComplaintTicketAction(Action):
    name = "action_create_complaint_ticket"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        """创建投诉工单（中台接口: POST /api/v1/support/tickets）"""
        complaint_type = state.active_task.slots.get("complaint_type")
        complaint_content = state.active_task.slots.get("complaint_content")

        # 将中文投诉类型映射为中台 ticket_type
        type_map = {
            "服务态度": "COMPLAINT",
            "业务办理": "COMPLAINT",
            "系统问题": "SUGGESTION",
            "费用争议": "COMPLAINT",
            "其他": "OTHER",
        }
        ticket_type = type_map.get(complaint_type, "COMPLAINT")

        try:
            # 从请求上下文获取客户号，无上下文时使用默认值
            from atguigu.api.logger import request_context_var
            try:
                ctx = request_context_var.get()
                customer_no = ctx.get("user_id", "SYS_CS_BOT")
                if customer_no == "-":
                    customer_no = "SYS_CS_BOT"
            except Exception:
                customer_no = "SYS_CS_BOT"

            resp = await create_support_ticket(
                customer_no=customer_no,
                ticket_type=ticket_type,
                ticket_title=f"{complaint_type}反馈",
                ticket_content=complaint_content,
            )
            # 中台返回: {"code": 0, "data": {"ticket_no": "...", "ticket_status": "..."}}
            if resp.get("code") != 0:
                return ActionResult(
                    messages=[BotMessage(text=f"抱歉，提交失败：{resp.get('message', '未知错误')}")]
                )

            data = resp.get("data", {})
            ticket_id = data.get("ticket_no", "")
            status = data.get("ticket_status", data.get("status", "已提交"))
            return ActionResult(
                slot_updates={
                    "ticket_id": ticket_id,
                    "ticket_status": status,
                }
            )
        except Exception as e:
            return ActionResult(
                messages=[BotMessage(text=f"抱歉，系统暂时无法提交投诉工单，请稍后再试。错误信息：{str(e)}")]
            )
