# 金融客服系统 AI 应用评估指南

## 快速开始

### 1. 安装依赖

```bash
pip install requests matplotlib
```

### 2. 启动服务

确保以下服务已启动：
- 客服服务 (端口 7000)
- 中台服务 (端口 8000)
- MySQL 数据库

### 3. 运行评估

```bash
# 运行完整评估
python evaluate.py

# 或指定服务地址
python evaluate.py --url http://your-server:7000
```

## 评估内容

### 1. 意图识别测试

测试系统对用户意图的识别能力：

| 类别 | 测试用例 | 期望意图 |
|------|---------|---------|
| 贷款 | "我想贷款"、"贷款申请"、"借钱" | loan_application |
| 账户 | "查询账户余额"、"余额查询" | account_balance |
| 理财 | "理财产品推荐"、"有什么理财" | wealth_recommendation |
| 交易 | "查询交易记录"、"最近交易" | transaction_query |
| 信用卡 | "信用卡挂失"、"卡片丢失" | card_loss |

### 2. 业务流程测试

测试完整的业务流程：

- **贷款申请流程**: 启动 → 提供账户号 → 提供金额 → 提供用途 → 提供期限 → 提交
- **账户查询流程**: 启动查询 → 返回结果

### 3. 响应时间测试

测试系统响应性能：

- 平均响应时间
- P95 响应时间
- P99 响应时间
- 响应时间分布

### 4. 异常场景测试

测试系统对异常输入的处理：

- 空输入
- 无意义输入
- 格式错误
- 范围错误

## 评估报告

运行评估后，会在 `evaluation_reports/` 目录生成以下文件：

### 1. 文本报告 (`evaluation_report.txt`)

包含：
- 总体评估结果
- 各项指标详情
- 失败用例分析

### 2. JSON 报告 (`evaluation_report.json`)

结构化数据，可用于：
- 数据分析
- 趋势对比
- 自动化处理

### 3. 可视化图表

#### 评估仪表盘 (`evaluation_dashboard.png`)
- 意图识别准确率
- 各业务类别准确率
- 响应时间分布
- 测试结果饼图

#### 详细结果图 (`detailed_results.png`)
- 每个测试用例的通过/失败状态

#### 雷达图 (`radar_chart.png`)
- 系统综合能力评估
- 包含：意图识别、业务流程、响应速度、稳定性、覆盖率

## 评估指标说明

### 意图识别准确率

```
准确率 = 正确识别的意图数 / 总意图数 × 100%
```

**目标**: ≥ 80%

### 业务流程完成率

```
完成率 = 成功完成的流程数 / 总流程数 × 100%
```

**目标**: ≥ 90%

### 响应时间

| 指标 | 说明 | 目标 |
|------|------|------|
| 平均响应时间 | 所有请求的平均耗时 | < 3s |
| P95 响应时间 | 95% 请求的耗时上限 | < 5s |
| P99 响应时间 | 99% 请求的耗时上限 | < 10s |

## 持续监控

### 定期评估

建议每周运行一次评估，跟踪系统性能趋势：

```bash
# 添加到 crontab
0 2 * * 1 cd /path/to/project && python evaluate.py
```

### A/B 测试

对比不同模型/策略的效果：

```bash
# 测试模型 A
python evaluate.py --model qwen-plus --output reports/model_a

# 测试模型 B
python evaluate.py --model qwen-turbo --output reports/model_b
```

## 自定义测试用例

在 `evaluate.py` 中修改测试用例：

```python
INTENT_TEST_CASES = [
    {"input": "你的输入", "expected_intent": "期望意图", "category": "类别"},
    # 添加更多用例...
]
```

## 常见问题

### Q: 评估脚本连接失败

A: 检查服务是否启动，端口是否正确

### Q: 图表中文显示乱码

A: 安装中文字体：
```bash
# Windows
# 字体已内置，通常无需额外安装

# Linux
apt-get install fonts-wqy-zenhei
```

### Q: 评估结果不准确

A: 检查测试用例是否符合实际业务场景，适当调整期望值
