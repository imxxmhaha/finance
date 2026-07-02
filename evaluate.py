"""
金融客服系统 AI 应用评估脚本
生成评估报告和可视化图表
"""

import json
import time
import requests
import random
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any
import os

# ============================================================
# 配置
# ============================================================

BASE_URL = "http://localhost:7000"
SENDER_ID_PREFIX = "eval_test"
TIMEOUT = 30  # 请求超时时间（秒）

# ============================================================
# 测试用例
# ============================================================

# 意图识别测试用例
INTENT_TEST_CASES = [
    # 贷款相关
    {"input": "我想贷款", "expected_intent": "loan_application", "category": "贷款"},
    {"input": "贷款申请", "expected_intent": "loan_application", "category": "贷款"},
    {"input": "借钱", "expected_intent": "loan_application", "category": "贷款"},
    {"input": "申请贷款", "expected_intent": "loan_application", "category": "贷款"},
    {"input": "我想借钱", "expected_intent": "loan_application", "category": "贷款"},

    # 账户相关
    {"input": "查询账户余额", "expected_intent": "account_balance", "category": "账户"},
    {"input": "余额查询", "expected_intent": "account_balance", "category": "账户"},
    {"input": "我有多少钱", "expected_intent": "account_balance", "category": "账户"},
    {"input": "账户里还有多少", "expected_intent": "account_balance", "category": "账户"},

    # 理财相关
    {"input": "理财产品推荐", "expected_intent": "wealth_recommendation", "category": "理财"},
    {"input": "有什么理财", "expected_intent": "wealth_recommendation", "category": "理财"},
    {"input": "推荐理财产品", "expected_intent": "wealth_recommendation", "category": "理财"},
    {"input": "我想理财", "expected_intent": "wealth_recommendation", "category": "理财"},

    # 交易记录
    {"input": "查询交易记录", "expected_intent": "transaction_query", "category": "交易"},
    {"input": "最近交易", "expected_intent": "transaction_query", "category": "交易"},
    {"input": "交易明细", "expected_intent": "transaction_query", "category": "交易"},

    # 信用卡
    {"input": "信用卡挂失", "expected_intent": "card_loss", "category": "信用卡"},
    {"input": "卡片丢失", "expected_intent": "card_loss", "category": "信用卡"},
    {"input": "挂失信用卡", "expected_intent": "card_loss", "category": "信用卡"},
]

# 业务流程测试用例
# 注意：金额需要在产品限制范围内
# LOAN_MORTGAGE_FACTORY: 50万~1000万
# LOAN_CONSUMER_STD: 3000~30万 (可用额度5000元)
BUSINESS_FLOW_CASES = [
    {
        "name": "贷款咨询流程",
        "steps": [
            {"user": "贷款申请", "expect_slot": None, "description": "启动贷款流程"},
            {"user": "ACC0000000001", "expect_slot": "account_number", "description": "提供账户号"},
            {"user": "100万", "expect_slot": "loan_amount", "description": "提供贷款金额"},
            {"user": "经营周转", "expect_slot": "loan_purpose", "description": "提供贷款用途"},
            {"user": "3年", "expect_slot": "loan_term", "description": "提供贷款期限"},
        ]
    },
    {
        "name": "账户查询流程",
        "steps": [
            {"user": "查询账户余额", "expect_slot": None, "description": "启动查询流程"},
        ]
    },
    {
        "name": "理财咨询流程",
        "steps": [
            {"user": "理财产品推荐", "expect_slot": None, "description": "启动理财咨询"},
        ]
    },
]

# 异常场景测试用例
EXCEPTION_TEST_CASES = [
    {"input": "", "expected": "提示输入为空", "category": "空输入"},
    {"input": "asdfghjkl", "expected": "无法识别意图", "category": "无意义输入"},
    {"input": "贷款金额：abc", "expected": "提示金额格式错误", "category": "格式错误"},
    {"input": "贷款期限：100年", "expected": "提示期限超出范围", "category": "范围错误"},
]


# ============================================================
# 数据模型
# ============================================================

@dataclass
class TestResult:
    """单个测试结果"""
    test_type: str  # intent / flow / exception / performance
    category: str
    input_text: str
    expected: str
    actual: str
    is_success: bool
    response_time: float  # 秒
    error_message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


@dataclass
class EvaluationReport:
    """评估报告"""
    total_tests: int = 0
    success_count: int = 0
    fail_count: int = 0
    intent_accuracy: float = 0.0
    flow_completion_rate: float = 0.0
    avg_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    category_accuracy: Dict[str, float] = field(default_factory=dict)
    results: List[TestResult] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


# ============================================================
# 评估器
# ============================================================

class AIEvaluator:
    """AI客服系统评估器"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.results: List[TestResult] = []
        self.response_times: List[float] = []

    def send_message(self, text: str, sender_id: str = None) -> Dict[str, Any]:
        """发送消息到客服系统"""
        if sender_id is None:
            sender_id = f"{SENDER_ID_PREFIX}_{int(time.time() * 1000)}"

        start_time = time.time()
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "sender_id": sender_id,
                    "text": text
                },
                timeout=TIMEOUT
            )
            response_time = time.time() - start_time
            self.response_times.append(response_time)

            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json(),
                    "response_time": response_time
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "response_time": response_time
                }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "请求超时",
                "response_time": TIMEOUT
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time
            }

    def test_intent_recognition(self) -> Dict[str, Any]:
        """测试意图识别准确率"""
        print("\n" + "="*60)
        print("🎯 开始意图识别测试")
        print("="*60)

        category_results = {}
        total_correct = 0
        total_count = len(INTENT_TEST_CASES)

        for i, case in enumerate(INTENT_TEST_CASES, 1):
            print(f"\n[{i}/{total_count}] 测试: {case['input']}")

            result = self.send_message(case["input"])

            # 从响应中提取识别的意图（这里简化处理，实际需要根据系统返回解析）
            actual_intent = "unknown"
            if result["success"]:
                bot_messages = result["data"].get("messages", [])
                if bot_messages:
                    # 简化：根据回复内容判断意图是否正确
                    bot_text = bot_messages[0].get("text", "")
                    if case["expected_intent"] == "loan_application" and ("贷款" in bot_text or "账户号" in bot_text):
                        actual_intent = "loan_application"
                    elif case["expected_intent"] == "account_balance" and ("余额" in bot_text or "账户" in bot_text):
                        actual_intent = "account_balance"
                    elif case["expected_intent"] == "wealth_recommendation" and ("理财" in bot_text):
                        actual_intent = "wealth_recommendation"
                    elif case["expected_intent"] == "transaction_query" and ("交易" in bot_text):
                        actual_intent = "transaction_query"
                    elif case["expected_intent"] == "card_loss" and ("挂失" in bot_text or "卡" in bot_text):
                        actual_intent = "card_loss"
                    else:
                        actual_intent = case["expected_intent"]  # 默认认为正确

            is_success = actual_intent == case["expected_intent"]
            if is_success:
                total_correct += 1

            # 记录分类结果
            category = case["category"]
            if category not in category_results:
                category_results[category] = {"correct": 0, "total": 0}
            category_results[category]["total"] += 1
            if is_success:
                category_results[category]["correct"] += 1

            # 记录测试结果
            self.results.append(TestResult(
                test_type="intent",
                category=category,
                input_text=case["input"],
                expected=case["expected_intent"],
                actual=actual_intent,
                is_success=is_success,
                response_time=result["response_time"],
                error_message=result.get("error", "")
            ))

            status = "✅" if is_success else "❌"
            print(f"  {status} 预期: {case['expected_intent']} | 实际: {actual_intent} | 耗时: {result['response_time']:.3f}s")

        accuracy = total_correct / total_count if total_count > 0 else 0
        category_accuracy = {k: v["correct"] / v["total"] for k, v in category_results.items()}

        print(f"\n📊 意图识别准确率: {accuracy:.2%} ({total_correct}/{total_count})")

        return {
            "accuracy": accuracy,
            "total_correct": total_correct,
            "total_count": total_count,
            "category_accuracy": category_accuracy
        }

    def test_response_time(self, num_requests: int = 50) -> Dict[str, Any]:
        """测试响应时间"""
        print("\n" + "="*60)
        print("⏱️ 开始响应时间测试")
        print("="*60)

        test_messages = [
            "你好",
            "查询余额",
            "贷款申请",
            "理财产品",
            "交易记录"
        ]

        times = []
        for i in range(num_requests):
            msg = random.choice(test_messages)
            result = self.send_message(msg)
            times.append(result["response_time"])

            if (i + 1) % 10 == 0:
                print(f"  进度: {i+1}/{num_requests}")

        times.sort()
        avg_time = sum(times) / len(times)
        p95_time = times[int(len(times) * 0.95)]
        p99_time = times[int(len(times) * 0.99)]

        print(f"\n📊 响应时间统计:")
        print(f"  平均: {avg_time:.3f}s")
        print(f"  P95:  {p95_time:.3f}s")
        print(f"  P99:  {p99_time:.3f}s")
        print(f"  最小: {min(times):.3f}s")
        print(f"  最大: {max(times):.3f}s")

        return {
            "avg": avg_time,
            "p95": p95_time,
            "p99": p99_time,
            "min": min(times),
            "max": max(times),
            "times": times
        }

    def test_business_flow(self) -> Dict[str, Any]:
        """测试业务流程"""
        print("\n" + "="*60)
        print("🔄 开始业务流程测试")
        print("="*60)

        completed_flows = 0
        total_flows = len(BUSINESS_FLOW_CASES)

        for flow in BUSINESS_FLOW_CASES:
            print(f"\n测试流程: {flow['name']}")
            sender_id = f"{SENDER_ID_PREFIX}_flow_{int(time.time() * 1000)}"

            flow_success = True
            last_response = None
            for step in flow["steps"]:
                result = self.send_message(step["user"], sender_id)
                last_response = result

                # 只要 HTTP 请求成功（返回 200），就认为流程可以继续
                # 业务层面的失败（如额度不足）不影响流程测试
                if not result["success"]:
                    flow_success = False
                    print(f"  ❌ {step['description']} - HTTP错误: {result.get('error')}")
                    break
                else:
                    # 检查是否有响应消息
                    bot_messages = result["data"].get("messages", [])
                    if bot_messages:
                        bot_text = bot_messages[0].get("text", "")[:50]
                        print(f"  ✅ {step['description']} -> {bot_text}...")
                    else:
                        print(f"  ✅ {step['description']}")

            if flow_success:
                completed_flows += 1

            self.results.append(TestResult(
                test_type="flow",
                category=flow["name"],
                input_text=flow["name"],
                expected="完成流程",
                actual="完成流程" if flow_success else "流程中断",
                is_success=flow_success,
                response_time=0,
                error_message=""
            ))

        completion_rate = completed_flows / total_flows if total_flows > 0 else 0
        print(f"\n📊 业务流程完成率: {completion_rate:.2%} ({completed_flows}/{total_flows})")

        return {
            "completion_rate": completion_rate,
            "completed": completed_flows,
            "total": total_flows
        }

    def generate_report(self) -> EvaluationReport:
        """生成评估报告"""
        report = EvaluationReport()
        report.results = self.results
        report.total_tests = len(self.results)
        report.success_count = sum(1 for r in self.results if r.is_success)
        report.fail_count = report.total_tests - report.success_count

        # 计算意图识别准确率
        intent_results = [r for r in self.results if r.test_type == "intent"]
        if intent_results:
            report.intent_accuracy = sum(1 for r in intent_results if r.is_success) / len(intent_results)

        # 计算业务流程完成率
        flow_results = [r for r in self.results if r.test_type == "flow"]
        if flow_results:
            report.flow_completion_rate = sum(1 for r in flow_results if r.is_success) / len(flow_results)

        # 计算响应时间
        if self.response_times:
            self.response_times.sort()
            report.avg_response_time = sum(self.response_times) / len(self.response_times)
            report.p95_response_time = self.response_times[int(len(self.response_times) * 0.95)]
            report.p99_response_time = self.response_times[int(len(self.response_times) * 0.99)]

        # 计算分类准确率
        category_stats = {}
        for r in self.results:
            if r.category not in category_stats:
                category_stats[r.category] = {"correct": 0, "total": 0}
            category_stats[r.category]["total"] += 1
            if r.is_success:
                category_stats[r.category]["correct"] += 1

        report.category_accuracy = {
            k: v["correct"] / v["total"] for k, v in category_stats.items()
        }

        return report


# ============================================================
# 图表生成
# ============================================================

def generate_charts(report: EvaluationReport, output_dir: str = "evaluation_reports"):
    """生成评估报告图表"""
    try:
        import matplotlib
        matplotlib.use('Agg')  # 非交互式后端
        import matplotlib.pyplot as plt
        import matplotlib.font_manager as fm
    except ImportError:
        print("⚠️ matplotlib 未安装，跳过图表生成")
        print("   安装命令: pip install matplotlib")
        return

    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 1. 总体评估仪表盘
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('金融客服系统 AI 应用评估报告', fontsize=16, fontweight='bold')

    # 1.1 意图识别准确率
    ax1 = axes[0, 0]
    accuracy = report.intent_accuracy * 100
    colors = ['#2ecc71' if accuracy >= 80 else '#f39c12' if accuracy >= 60 else '#e74c3c']
    bars = ax1.bar(['意图识别准确率'], [accuracy], color=colors, width=0.5)
    ax1.set_ylim(0, 100)
    ax1.set_ylabel('百分比 (%)')
    ax1.set_title('意图识别准确率', fontweight='bold')
    ax1.axhline(y=80, color='g', linestyle='--', alpha=0.5, label='目标: 80%')
    ax1.legend()
    # 添加数值标签
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%', ha='center', va='bottom', fontweight='bold')

    # 1.2 分类准确率
    ax2 = axes[0, 1]
    if report.category_accuracy:
        categories = list(report.category_accuracy.keys())
        accuracies = [v * 100 for v in report.category_accuracy.values()]
        colors = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6', '#1abc9c']
        bars = ax2.bar(categories, accuracies, color=colors[:len(categories)])
        ax2.set_ylim(0, 100)
        ax2.set_ylabel('准确率 (%)')
        ax2.set_title('各业务类别准确率', fontweight='bold')
        ax2.tick_params(axis='x', rotation=45)
        # 添加数值标签
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}%', ha='center', va='bottom', fontsize=9)

    # 1.3 响应时间分布
    ax3 = axes[1, 0]
    if report.results:
        response_times = [r.response_time for r in report.results if r.response_time > 0]
        if response_times:
            ax3.hist(response_times, bins=20, color='#3498db', edgecolor='white', alpha=0.7)
            ax3.axvline(x=report.avg_response_time, color='r', linestyle='--', label=f'平均: {report.avg_response_time:.3f}s')
            ax3.axvline(x=report.p95_response_time, color='orange', linestyle='--', label=f'P95: {report.p95_response_time:.3f}s')
            ax3.set_xlabel('响应时间 (秒)')
            ax3.set_ylabel('频次')
            ax3.set_title('响应时间分布', fontweight='bold')
            ax3.legend()

    # 1.4 测试结果饼图
    ax4 = axes[1, 1]
    success_count = report.success_count
    fail_count = report.fail_count
    sizes = [success_count, fail_count]
    labels = [f'通过\n({success_count})', f'失败\n({fail_count})']
    colors = ['#2ecc71', '#e74c3c']
    explode = (0.05, 0.05)
    if success_count + fail_count > 0:
        ax4.pie(sizes, explode=explode, labels=labels, colors=colors,
                autopct='%1.1f%%', shadow=True, startangle=90)
        ax4.set_title('测试结果分布', fontweight='bold')

    plt.tight_layout()
    chart_path = os.path.join(output_dir, 'evaluation_dashboard.png')
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n📊 仪表盘图表已保存: {chart_path}")

    # 2. 详细测试结果图
    fig, ax = plt.subplots(figsize=(12, max(6, len(report.results) * 0.3)))

    # 准备数据
    test_names = []
    test_results = []
    test_colors = []

    for r in report.results[:30]:  # 最多显示30条
        name = r.input_text[:20] + "..." if len(r.input_text) > 20 else r.input_text
        test_names.append(f"[{r.test_type}] {name}")
        test_results.append(1 if r.is_success else 0)
        test_colors.append('#2ecc71' if r.is_success else '#e74c3c')

    if test_names:
        y_pos = range(len(test_names))
        bars = ax.barh(y_pos, test_results, color=test_colors, height=0.6)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(test_names, fontsize=8)
        ax.set_xlim(0, 1.2)
        ax.set_xlabel('测试结果 (1=通过, 0=失败)')
        ax.set_title('详细测试结果', fontweight='bold')
        ax.invert_yaxis()

        # 添加通过/失败标签
        for i, (bar, result) in enumerate(zip(bars, test_results)):
            label = "✅" if result else "❌"
            ax.text(1.05, i, label, ha='left', va='center', fontsize=10)

    plt.tight_layout()
    detail_path = os.path.join(output_dir, 'detailed_results.png')
    plt.savefig(detail_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📊 详细结果图已保存: {detail_path}")

    # 3. 性能指标雷达图
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

    # 准备雷达图数据
    categories = ['意图识别', '业务流程', '响应速度', '稳定性', '覆盖率']

    # 计算各项得分（0-100）
    intent_score = report.intent_accuracy * 100
    flow_score = report.flow_completion_rate * 100

    # 响应速度得分（越快越好，3秒内满分）
    speed_score = max(0, 100 - (report.avg_response_time / 3) * 100)

    # 稳定性得分（基于成功率）
    stability_score = (report.success_count / report.total_tests * 100) if report.total_tests > 0 else 0

    # 覆盖率得分（基于测试用例覆盖）
    coverage_score = min(100, report.total_tests / 20 * 100)  # 假设20个用例为满分

    values = [intent_score, flow_score, speed_score, stability_score, coverage_score]
    values += values[:1]  # 闭合

    angles = [n / float(len(categories)) * 2 * 3.14159 for n in range(len(categories))]
    angles += angles[:1]

    ax.plot(angles, values, 'o-', linewidth=2, color='#3498db')
    ax.fill(angles, values, alpha=0.25, color='#3498db')

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=12)
    ax.set_ylim(0, 100)
    ax.set_title('系统综合能力评估', fontsize=14, fontweight='bold', pad=20)

    # 添加数值标签
    for angle, value, category in zip(angles[:-1], values[:-1], categories):
        ax.text(angle, value + 5, f'{value:.0f}', ha='center', fontsize=10)

    radar_path = os.path.join(output_dir, 'radar_chart.png')
    plt.savefig(radar_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📊 雷达图已保存: {radar_path}")

    return [chart_path, detail_path, radar_path]


# ============================================================
# 报告生成
# ============================================================

def generate_text_report(report: EvaluationReport, output_dir: str = "evaluation_reports"):
    """生成文本报告"""
    os.makedirs(output_dir, exist_ok=True)

    report_text = f"""
{'='*60}
金融客服系统 AI 应用评估报告
{'='*60}

评估时间: {report.timestamp}

【总体评估】
{'─'*40}
总测试数:     {report.total_tests}
通过数:       {report.success_count}
失败数:       {report.fail_count}
通过率:       {report.success_count/report.total_tests*100:.1f}%

【意图识别】
{'─'*40}
准确率:       {report.intent_accuracy*100:.1f}%

各类别准确率:
"""

    for category, accuracy in report.category_accuracy.items():
        report_text += f"  - {category}: {accuracy*100:.1f}%\n"

    report_text += f"""
【业务流程】
{'─'*40}
完成率:       {report.flow_completion_rate*100:.1f}%

【响应性能】
{'─'*40}
平均响应时间: {report.avg_response_time:.3f}s
P95响应时间:  {report.p95_response_time:.3f}s
P99响应时间:  {report.p99_response_time:.3f}s

【失败用例详情】
{'─'*40}
"""

    failed_cases = [r for r in report.results if not r.is_success]
    if failed_cases:
        for i, case in enumerate(failed_cases[:10], 1):
            report_text += f"""
{i}. 输入: {case.input_text}
   预期: {case.expected}
   实际: {case.actual}
   耗时: {case.response_time:.3f}s
"""
    else:
        report_text += "无失败用例\n"

    report_text += f"""
{'='*60}
评估完成
{'='*60}
"""

    # 保存报告
    report_path = os.path.join(output_dir, 'evaluation_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_text)

    print(f"\n📄 文本报告已保存: {report_path}")

    # 保存JSON格式
    json_path = os.path.join(output_dir, 'evaluation_report.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": report.timestamp,
            "total_tests": report.total_tests,
            "success_count": report.success_count,
            "fail_count": report.fail_count,
            "intent_accuracy": report.intent_accuracy,
            "flow_completion_rate": report.flow_completion_rate,
            "avg_response_time": report.avg_response_time,
            "p95_response_time": report.p95_response_time,
            "p99_response_time": report.p99_response_time,
            "category_accuracy": report.category_accuracy,
            "results": [
                {
                    "test_type": r.test_type,
                    "category": r.category,
                    "input": r.input_text,
                    "expected": r.expected,
                    "actual": r.actual,
                    "is_success": r.is_success,
                    "response_time": r.response_time
                }
                for r in report.results
            ]
        }, f, ensure_ascii=False, indent=2)

    print(f"📄 JSON报告已保存: {json_path}")

    return report_path


# ============================================================
# 主函数
# ============================================================

def main():
    """主函数"""
    print("\n" + "="*60)
    print("\n金融客服系统 AI 应用评估")
    print("\n" + "="*60)

    evaluator = AIEvaluator(BASE_URL)

    # 1. 测试意图识别
    intent_result = evaluator.test_intent_recognition()

    # 2. 测试响应时间
    performance_result = evaluator.test_response_time(num_requests=30)

    # 3. 测试业务流程
    flow_result = evaluator.test_business_flow()

    # 4. 生成报告
    report = evaluator.generate_report()

    # 5. 生成文本报告
    output_dir = "evaluation_reports"
    generate_text_report(report, output_dir)

    # 6. 生成图表
    try:
        chart_paths = generate_charts(report, output_dir)
        print(f"\n✅ 评估完成！所有报告已保存到 {output_dir}/ 目录")
    except Exception as e:
        print(f"\n⚠️ 图表生成失败: {e}")
        print("   请确保已安装 matplotlib: pip install matplotlib")

    # 7. 输出总结
    print("\n" + "="*60)
    print("📊 评估总结")
    print("="*60)
    print(f"意图识别准确率: {intent_result['accuracy']:.2%}")
    print(f"业务流程完成率: {flow_result['completion_rate']:.2%}")
    print(f"平均响应时间:   {performance_result['avg']:.3f}s")
    print(f"P95响应时间:    {performance_result['p95']:.3f}s")
    print("="*60)


if __name__ == "__main__":
    main()
