# 智能金融客服系统 - 架构设计文档

## 1. 业务架构图

```mermaid
graph TB
    subgraph "用户层"
        User[用户/客户]
    end

    subgraph "前端交互层"
        WebApp[Web应用<br/>Vue 3 + Vite]
        ChatUI[智能对话界面]
        SidebarPanel[业务对象面板]
    end

    subgraph "业务服务层"
        ChatService[对话服务]

        subgraph "核心业务模块"
            AccountQuery[账户余额查询]
            WealthConsult[理财产品咨询]
            LoanApply[贷款申请]
            CreditCardLoss[信用卡挂失]
            ComplaintTicket[投诉工单]
        end

        subgraph "智能引擎"
            DialogueEngine[对话引擎]
            IntentRecognition[意图识别]
            TaskPlanner[任务规划]
            ActionExecutor[动作执行器]
        end
    end

    subgraph "数据与外部服务层"
        DB[(数据库)]
        FinanceMiddle[金融中台]
        LLMService[大语言模型服务]

        subgraph "金融中台接口"
            AccountAPI[账户服务API]
            WealthAPI[理财服务API]
            LoanAPI[贷款服务API]
            SupportAPI[客服工单API]
        end
    end

    User --> WebApp
    WebApp --> ChatUI
    WebApp --> SidebarPanel

    ChatUI --> ChatService
    SidebarPanel --> FinanceMiddle

    ChatService --> DialogueEngine
    DialogueEngine --> IntentRecognition
    IntentRecognition --> TaskPlanner
    TaskPlanner --> ActionExecutor

    ActionExecutor --> AccountQuery
    ActionExecutor --> WealthConsult
    ActionExecutor --> LoanApply
    ActionExecutor --> CreditCardLoss
    ActionExecutor --> ComplaintTicket

    AccountQuery --> AccountAPI
    WealthConsult --> WealthAPI
    LoanApply --> LoanAPI
    ComplaintTicket --> SupportAPI
    CreditCardLoss --> SupportAPI

    FinanceMiddle --> AccountAPI
    FinanceMiddle --> WealthAPI
    FinanceMiddle --> LoanAPI
    FinanceMiddle --> SupportAPI

    DialogueEngine --> LLMService
    ChatService --> DB
```

## 2. 技术架构图

```mermaid
graph TB
    subgraph "客户端 Client"
        Browser[浏览器]
        VueApp[Vue 3 SPA]
        Vite[Vite 构建工具]
    end

    subgraph "API 网关层 Gateway"
        Nginx[Nginx 反向代理]
        CORS[CORS 跨域处理]
    end

    subgraph "应用服务层 Application"
        FastAPI[FastAPI 框架]
        Uvicorn[Uvicorn ASGI服务器]

        subgraph "API 路由"
            ChatRouter[聊天路由 /api/chat]
            HistoryRouter[历史记录路由]
            FinanceRouter[金融数据路由]
        end

        subgraph "中间件"
            AuthMiddleware[认证中间件]
            LogMiddleware[日志中间件]
            RequestContext[请求上下文]
        end
    end

    subgraph "业务逻辑层 Business Logic"
        subgraph "对话管理"
            DialogueService[对话服务]
            DialogueState[对话状态管理]
            MessageHandler[消息处理器]
        end

        subgraph "任务执行引擎"
            TaskHandler[任务处理器]
            FlowLoader[流程加载器]
            StepExecutor[步骤执行器]
            ActionRunner[动作运行器]
        end

        subgraph "知识与意图"
            KnowledgeBase[知识库]
            IntentClassifier[意图分类器]
            ClarifyHandler[澄清处理器]
            ChitChatHandler[闲聊处理器]
        end
    end

    subgraph "基础设施层 Infrastructure"
        subgraph "数据存储"
            MySQL[(MySQL 数据库)]
            aiomysql[aiomysql 异步驱动]
        end

        subgraph "外部服务"
            LLM[大语言模型 API]
            HttpClient[HTTP 客户端]
        end

        subgraph "配置管理"
            Config[配置中心]
            EnvFile[.env 环境变量]
        end
    end

    subgraph "金融中台 Finance Middle Platform"
        AccountService[账户服务]
        WealthService[理财服务]
        LoanService[贷款服务]
        SupportService[客服工单服务]
    end

    Browser --> VueApp
    VueApp --> Nginx

    Nginx --> FastAPI
    FastAPI --> Uvicorn

    FastAPI --> ChatRouter
    FastAPI --> HistoryRouter
    FastAPI --> FinanceRouter

    ChatRouter --> AuthMiddleware
    AuthMiddleware --> DialogueService

    DialogueService --> DialogueState
    DialogueService --> MessageHandler

    MessageHandler --> TaskHandler
    TaskHandler --> FlowLoader
    FlowLoader --> StepExecutor
    StepExecutor --> ActionRunner

    DialogueService --> KnowledgeBase
    KnowledgeBase --> IntentClassifier
    IntentClassifier --> ClarifyHandler
    IntentClassifier --> ChitChatHandler

    DialogueService --> LLM
    DialogueService --> aiomysql
    aiomysql --> MySQL

    ActionRunner --> HttpClient
    HttpClient --> AccountService
    HttpClient --> WealthService
    HttpClient --> LoanService
    HttpClient --> SupportService

    FastAPI --> Config
    Config --> EnvFile
```

## 3. 核心业务流程图

```mermaid
sequenceDiagram
    participant U as 用户
    participant F as 前端
    participant A as API网关
    participant D as 对话引擎
    participant L as LLM服务
    participant T as 任务执行器
    participant M as 金融中台

    U->>F: 发送消息
    F->>A: POST /api/chat
    A->>D: 处理消息

    D->>L: 意图识别
    L-->>D: 返回意图分类

    alt 需要执行任务
        D->>T: 触发任务流程
        T->>M: 调用金融API
        M-->>T: 返回业务数据
        T-->>D: 返回执行结果
    else 闲聊/澄清
        D->>L: 生成回复
        L-->>D: 返回回复内容
    end

    D-->>A: 返回响应
    A-->>F: JSON响应
    F-->>U: 显示结果
```

## 4. 业务功能模块说明

### 4.1 核心业务功能

| 功能模块 | 说明 | 对应Action类 |
|---------|------|-------------|
| 账户余额查询 | 查询客户银行账户余额信息 | `LookUpAccountBalanceAction` |
| 交易记录查询 | 查询账户交易流水记录 | `LookUpTransactionAction` |
| 理财产品咨询 | 查询和推荐理财产品 | 通过金融中台API |
| 贷款申请 | 提交贷款申请流程 | `SubmitLoanApplicationAction` |
| 信用卡挂失 | 信用卡紧急挂失处理 | `SubmitCreditCardLossAction` |
| 投诉工单 | 创建客户服务投诉工单 | `CreateComplaintTicketAction` |

### 4.2 智能对话能力

- **意图识别**: 基于LLM的自然语言理解
- **任务规划**: 自动规划多步骤业务流程
- **槽位提取**: 从对话中提取业务参数
- **上下文管理**: 维护多轮对话状态
- **知识库**: 金融产品知识问答

## 5. 技术栈汇总

| 层级 | 技术选型 |
|------|---------|
| 前端框架 | Vue 3 + Composition API |
| 构建工具 | Vite |
| 后端框架 | FastAPI (Python) |
| ASGI服务器 | Uvicorn |
| 数据库 | MySQL |
| 数据库驱动 | aiomysql (异步) |
| AI服务 | 大语言模型 (LLM) |
| HTTP客户端 | httpx/aiohttp |

## 6. 部署架构

```
┌─────────────────────────────────────────────────────────┐
│                    生产环境部署                           │
├─────────────────────────────────────────────────────────┤
│  前端: Nginx 静态资源服务                                │
│  后端: Uvicorn + FastAPI (多worker)                      │
│  数据库: MySQL 主从集群                                  │
│  缓存: Redis (可选)                                      │
│  AI服务: LLM API 云端调用                               │
└─────────────────────────────────────────────────────────┘
```
