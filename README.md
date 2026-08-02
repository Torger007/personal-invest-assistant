# 个人投资助手

一个面向 A 股基金分析的全栈 Web 应用。系统采集公开市场数据，提供市场、基金与板块分析，生成结构化投资建议，并通过 AI 助手支持基于工具调用的问答。

> 状态：**可演示、可容器化部署的 MVP**（截至 2026-08-02）。核心闭环已经完成；生产稳定性、自动化测试和可观测性仍需补齐。

## 当前进度

| 领域 | 进度 | 已实现内容 |
| --- | --- | --- |
| 市场数据与采集 | 已完成 | 基于 AKShare 采集指数、资金流、基金净值和概念/行业板块；支持手动刷新与工作日 16:30 定时刷新。 |
| 市场与基金界面 | 已完成 | 市场概览、基金列表、基金详情（净值走势和收益计算）、板块走势及 K 线图。 |
| 投资建议 | 已完成 | 技术面、估值、资金流、情绪和板块等多维分析；支持单基金、组合建议、建议历史与对比。 |
| AI 助手 | 已完成 | OpenAI/Anthropic Provider 适配、标准工具调用、问题规划、SSE 流式输出、执行进度和历史会话。 |
| 用户与权限 | 已完成 | 登录页、服务端会话、HttpOnly Cookie、CSRF 校验、登录限流；数据和会话按用户隔离，刷新任务限管理员调用。 |
| 部署 | 已完成 | Docker Compose 编排 PostgreSQL、数据库迁移、FastAPI 和 Nginx；仅对外暴露前端端口。 |
| 前端构建 | 已验证 | `npm run build` 于 2026-08-02 成功完成。 |
| 后端自动化测试 | 部分通过 | 已有数据存储、Agent 规划、SSE 和任务管理测试；2026-08-02 在锁定依赖环境中执行结果为 13 通过、3 失败。 |

## 已知缺口与下一步

1. 修复鉴权改造后失效的 3 个 Agent/SSE 测试夹具：直接调用路由时未传入用户，且以 `__new__` 构造 `AgentCore` 的测试未设置 `user_id`。
2. 为登录、鉴权、数据采集、建议生成和容器启动补充集成测试，并接入 CI。
3. 提供持仓的新增、编辑、删除界面和 API。目前只会为首次登录用户写入预置持仓，尚未提供自助管理功能。
4. 将进程内的手动刷新状态改为持久化任务队列，并增加采集失败告警、日志聚合、指标和备份策略。
5. 扩充技术指标与数据质量校验，并处理 AKShare/上游公开数据源的可用性、限流和反爬变化。
6. 优化前端产物拆包。当前生产构建通过，但存在超过 500 kB 的 chunk 警告。

## 功能概览

- **市场概览**：主要指数、北向/主力资金流、行业与概念板块数据。
- **基金分析**：基金列表、历史净值、收益计算、技术与估值等多维分析。
- **板块走势**：板块涨跌排行、资金趋势及历史 K 线展示。
- **投资建议**：综合评分、信号一致性、置信度、风险提示和历史对比。
- **AI 问答**：通过预定义工具查询市场、基金、持仓和建议；支持 OpenAI 与 Anthropic 兼容配置。
- **账号安全**：服务端会话配合 HttpOnly Cookie 与 CSRF Token；初始管理员由环境变量引导创建。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 后端 | Python 3.11、FastAPI、SQLAlchemy Async、Alembic |
| 数据库 | PostgreSQL 16（Docker Compose） |
| 前端 | Vue 3、Vite、Element Plus、ECharts、Axios |
| 数据采集 | AKShare、pandas、curl_cffi |
| 分析与调度 | ta、APScheduler |
| AI | OpenAI / Anthropic SDK、YAML Prompt、SSE |
| 部署 | Docker Compose、Nginx、Uvicorn |

## 项目结构

```text
personal-invest-assistant/
├── backend/
│   ├── app/
│   │   ├── api/                  # 认证、市场、基金、建议、Agent、任务接口
│   │   ├── agent/                # Provider、规划器、工具注册与执行、流式服务
│   │   ├── models/               # 市场、建议、会话、用户与持仓 ORM 模型
│   │   ├── services/             # 分析器、建议生成、数据采集与调度
│   │   └── auth.py               # 会话与权限控制
│   ├── alembic/                  # 数据库迁移
│   ├── tests/                    # 存储层与 Agent 单元测试
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/views/                # 登录、市场、基金、板块、建议、AI 设置页面
│   ├── src/api/                  # HTTP 与 SSE 客户端封装
│   ├── Dockerfile
│   └── nginx.conf
├── docs/
│   └── docker-deployment.md      # Docker 部署细节
├── docker-compose.yml
└── .env.production.example
```

## 本地开发

### 前置条件

- Python 3.11+
- Node.js 22+（前端镜像使用 Node 22；本地应使用兼容版本）
- PostgreSQL 16+
- 可用的 OpenAI 或 Anthropic API Key（仅 AI 问答需要）

### 1. 启动后端

在 `backend/.env` 中配置本地 PostgreSQL 连接；同时设置初始管理员和本地 Cookie 选项，例如：

```dotenv
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/invest_assistant
BOOTSTRAP_ADMIN_USERNAME=admin
BOOTSTRAP_ADMIN_PASSWORD=change-this-to-a-strong-password
SESSION_SECURE=false
CORS_ORIGINS=http://localhost:3001,http://127.0.0.1:3001
```

然后安装依赖、执行迁移并启动：

```powershell
cd backend
uv sync --extra test
uv run alembic upgrade head
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001
```

> 仅需浏览市场/基金数据时可不配置 LLM Key；进入 AI 助手前需在 `backend/.env` 配置对应 Provider 的 Key 和模型。

### 2. 启动前端

```powershell
cd frontend
npm ci
npm run dev
```

- 前端：<http://localhost:3001>
- API 文档：<http://localhost:8001/docs>

首次登录使用上一步通过 `BOOTSTRAP_ADMIN_USERNAME` 和 `BOOTSTRAP_ADMIN_PASSWORD` 创建的管理员账号。

## Docker 部署

生产或演示环境推荐使用 Docker Compose：

```powershell
Copy-Item .env.production.example .env.production
# 编辑 .env.production，替换数据库密码、管理员密码、CORS 域名和 LLM Key
docker compose --env-file .env.production up -d --build
docker compose --env-file .env.production ps
```

默认访问地址为 <http://localhost:8080>。生产环境应使用 HTTPS 反向代理并保留 `SESSION_SECURE=true`。详细配置、运维命令和数据卷注意事项见 [Docker 部署文档](docs/docker-deployment.md)。

## 验证

```powershell
# 前端生产构建
cd frontend
npm run build

# 后端测试（先用 uv 安装与锁文件一致的依赖）
cd ../backend
uv sync --extra test
uv run pytest -q
```

当前仓库已确认前端构建成功。后端测试在锁定依赖环境中的结果为 **13 passed、3 failed**；失败均为鉴权改造后需要更新的 Agent/SSE 测试夹具。后端测试应使用 `uv` 的锁定依赖环境执行，避免全局 Python 中 pandas/NumPy ABI 不匹配导致的收集失败。

## 风险提示

本项目仅用于学习和信息辅助，不构成投资建议。市场数据可能延迟、缺失或受第三方数据源限制；任何投资决策均应由用户独立判断并自行承担风险。

## License

MIT

---

创建日期：2026-07-02 · 本次状态更新：2026-08-02
