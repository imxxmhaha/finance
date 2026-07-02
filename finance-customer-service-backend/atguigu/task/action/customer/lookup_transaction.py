from typing import Any

from atguigu.api.logger import logger
from atguigu.domain.messages import BotMessage
from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult
from atguigu.task.action.customer.share import fetch_account_transactions
from atguigu.task.action.customer.slot_parser import parse_period


class LookUpTransactionAction(Action):
    name = "action_lookup_transactions"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        """查询交易记录（中台接口: GET /api/v1/accounts/{account_no}/transactions）"""
        account_number = state.active_task.slots.get("account_number")
        transaction_period = state.active_task.slots.get("transaction_period", "")

        # 解析时间段: "最近三个月" -> (start_time, end_time)
        start_time, end_time = await parse_period(transaction_period)
        logger.info(f"交易查询 time_parser: '{transaction_period}' -> start={start_time}, end={end_time}")

        try:
            resp = await fetch_account_transactions(
                account_no=account_number,
                start_time=start_time,
                end_time=end_time,
                page_no=1,
                page_size=10
            )
            # 中台返回: {"code": 0, "data": {"list": [...]}}
            if resp.get("code") != 0:
                return ActionResult(
                    messages=[BotMessage(text=f"抱歉，查询失败：{resp.get('message', '未知错误')}")]
                )

            data = resp.get("data", {})
            transactions = data.get("list", [])
            if not transactions:
                return ActionResult(
                    slot_updates={"transaction_list": "暂无交易记录"}
                )

            # 中台交易字段: transaction_no, transaction_type, transaction_status,
            #               transaction_amount, fee_amount, currency_code,
            #               transaction_at, counterparty_name, merchant_name
            type_map = {
                "wealth_purchase": "理财申购",
                "wealth_redeem": "理财赎回",
                "loan_disbursement": "贷款发放",
                "loan_repayment": "贷款还款",
                "transfer_in": "转入",
                "transfer_out": "转出",
                "deposit": "存款",
                "withdrawal": "取款",
                "fee": "手续费",
                "interest": "利息",
            }
            status_map = {
                "success": "成功",
                "pending": "处理中",
                "failed": "失败",
                "reversed": "已冲正",
            }

            formatted_list = []
            for i, tx in enumerate(transactions[:10], 1):
                tx_time = tx.get("transaction_at", tx.get("created_at", ""))
                tx_type = type_map.get(tx.get("transaction_type", ""), tx.get("transaction_type", ""))
                tx_amount = tx.get("transaction_amount", "0.00")
                tx_currency = tx.get("currency_code", "CNY")
                tx_status = status_map.get(tx.get("transaction_status", ""), tx.get("transaction_status", ""))
                tx_party = tx.get("counterparty_name", "") or tx.get("merchant_name", "")
                formatted_list.append(
                    f"{i}. [{tx_time}] {tx_type} | {tx_amount} {tx_currency} | 状态: {tx_status}"
                    + (f" | {tx_party}" if tx_party else "")
                )

            return ActionResult(
                slot_updates={"transaction_list": "\n".join(formatted_list)}
            )
        except Exception as e:
            return ActionResult(
                messages=[BotMessage(text=f"抱歉，系统暂时无法查询交易记录，请稍后再试。错误信息：{str(e)}")]
            )
