from typing import Any

from atguigu.api.logger import logger
from atguigu.domain.messages import BotMessage
from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult
from atguigu.task.action.customer.share import (
    fetch_credit_limits,
    fetch_customer_no_by_account,
    fetch_loan_product_detail,
)


class FetchLoanProductInfoAction(Action):
    name = "action_fetch_loan_product_info"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        """获取贷款产品信息（期限范围等），存入 slots 供后续步骤使用"""
        account_number = action_kwargs.get("account_number")

        if not account_number:
            return ActionResult(
                messages=[BotMessage(text="抱歉，未提供账户号，无法查询产品信息。")],
                is_success=False,
            )

        try:
            # 1. 通过账户号反查客户号
            customer_no = await fetch_customer_no_by_account(account_number)
            if not customer_no:
                return ActionResult(
                    messages=[BotMessage(text=f"抱歉，无法识别账户号「{account_number}」，请确认账户号是否正确。")],
                    is_success=False,
                )
            logger.info(f"贷款产品信息查询 账户号={account_number} -> 客户号={customer_no}")

            # 2. 查询客户授信额度
            credit_resp = await fetch_credit_limits(customer_no)
            if credit_resp.get("code") != 0:
                return ActionResult(
                    messages=[BotMessage(text=f"抱歉，查询授信额度失败：{credit_resp.get('message', '未知错误')}")],
                    is_success=False,
                )
            credit_list = credit_resp.get("data", {}).get("list", [])
            if not credit_list:
                return ActionResult(
                    messages=[BotMessage(text="抱歉，您当前没有可用的授信额度，请先申请授信。")],
                    is_success=False,
                )

            # 取第一个有效额度的产品编号
            product_code = credit_list[0].get("product_code")
            logger.info(f"贷款产品信息查询 产品编号={product_code}")

            # 3. 查询产品详情
            product_resp = await fetch_loan_product_detail(product_code)
            if product_resp.get("code") != 0:
                return ActionResult(
                    messages=[BotMessage(text=f"抱歉，查询产品信息失败：{product_resp.get('message', '未知错误')}")],
                    is_success=False,
                )
            product_detail = product_resp.get("data", {}).get("product_detail", {})

            # 4. 提取期限范围和金额范围
            term_range = product_detail.get("term_range", {})
            term_min = term_range.get("min")
            term_max = term_range.get("max")

            amount_range = product_detail.get("amount_range", {})
            amount_min = amount_range.get("min")
            amount_max = amount_range.get("max")

            # 生成可读的期限描述
            def format_term(months):
                if months is None:
                    return "无限制"
                if months < 12:
                    return f"{months}个月"
                years = months // 12
                remain_months = months % 12
                if remain_months == 0:
                    return f"{years}年"
                return f"{years}年{remain_months}个月"

            # 生成可选期限示例
            def generate_term_examples(min_m, max_m):
                examples = []
                common_terms = [1, 3, 6, 12, 18, 24, 36, 48, 60, 120, 240, 360]
                for t in common_terms:
                    if min_m <= t <= max_m:
                        examples.append(format_term(t))
                    if len(examples) >= 6:
                        break
                return examples

            term_examples = generate_term_examples(term_min or 1, term_max or 360)
            term_examples_text = "、".join(term_examples) if term_examples else ""
            term_range_text = f"{format_term(term_min)}~{format_term(term_max)}" if term_min is not None or term_max is not None else ""

            logger.info(f"贷款产品信息查询完成 期限范围=[{term_min}, {term_max}] 示例={term_examples_text}")

            return ActionResult(
                slot_updates={
                    "customer_no": customer_no,
                    "product_code": product_code,
                    "term_min": str(term_min) if term_min is not None else "",
                    "term_max": str(term_max) if term_max is not None else "",
                    "term_range_text": term_range_text,
                    "term_examples_text": term_examples_text,
                }
            )

        except Exception as e:
            logger.error(f"贷款产品信息查询异常: {e}")
            return ActionResult(
                messages=[BotMessage(text=f"抱歉，系统暂时无法查询产品信息，请稍后再试。错误信息：{str(e)}")],
                is_success=False,
            )
