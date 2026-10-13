# 个人投资助手

一个面向个人基金持仓和 A 股市场分析的全栈 Web 应用。系统采集公开市场数据，展示真实持仓、市场与板块信息，生成规则型分析建议，并提供基于受控工具调用的 AI 问答。

> 状态：**可演示、可容器化部署的 MVP**（截至 2026-10-13）。持仓维护、数据采集、建议生成和 Agent 问答的主要流程已实现；生产稳定性、自动化测试和可观测性仍需补齐。

## 当前进度

| 领域 | 进度 | 已实现内容 |
| --- | --- | --- |
| 市场数据与采集 | 已实现 | 基于 AKShare 采集指数、资金流、活跃用户持仓基金的净值和概念/行业板块；支持管理员手动刷新与周一至周五 16:30（Asia/Shanghai）定时刷新。 |
| 持仓与市场界面 | 已实现 | 用户按平台新增、校准、删除基金持仓；查看持仓估值、收益走势、市场概览和板块走势。 |
| 投资建议 | 已实现 | 技术面、估值、资金流、情绪等维度分析；展示单基金建议、当前组合概览及建议历史。 |
| AI 助手 | 已实现 | OpenAI/Anthropic Provider、受约束规划与工具校验、质量检查、有限重规划、SSE 进度和历史会话。 |
| 用户与权限 | 已实现 | 登录页、服务端会话、HttpOnly Cookie、CSRF 校验、登录限流；数据和会话按用户隔离，刷新任务限管理员调用。 |
| 部署 | 已实现 | Docker Compose 编排 PostgreSQL、数据库迁移、FastAPI 和 Nginx；仅对外暴露前端端口。 |
| 前端构建 | 已验证 | `npm run build` 于 2026-10-10 成功完成，仍有大包警告。 |
| 后端自动化测试 | 已通过 | 已有数据存储、Agent 规划、SSE 和任务管理测试；2026-10-13 在锁定依赖环境中执行结果为 54 通过。Agent 离线评测为 20/20。 |

## 已知缺口与下一步

1. 为登录、鉴权、数据采集、建议生成和容器启动补充集成测试，并接入 CI。
2. 为持仓变更补充审计记录和组合级规则；当前用户没有真实持仓时，组合为空。
3. 将进程内的手动刷新状态改为持久化任务队列，并增加采集失败告警、日志聚合、指标和备份策略。
4. 扩充技术指标与数据质量校验，并处理 AKShare/上游公开数据源的可用性、限流和反爬变化。
5. 优化前端产物拆包。当前生产构建通过，但存在超过 500 kB 的 chunk 警告。

## 功能概览

- **市场概览**：主要指数、北向/主力资金流、行业与概念板块数据。
- **真实持仓**：按平台管理基金、份额、市值、收益与成本；校准后查看基于已保存净值的收益走势。
- **板块走势**：板块涨跌排行、资金趋势及历史 K 线展示。
- **投资建议**：综合评分、信号一致性、置信度、风险提示和历史对比。
- **AI 问答**：默认启用受约束 Agent，在服务端工具白名单和预算内查询市场、基金、当前用户持仓及建议；单基金最终动作与目标仓位由规则产物提供。
- **账号安全**：服务端会话配合 HttpOnly Cookie 与 CSRF Token；初始管理员由环境变量引导创建。

### 持仓与净值采集规则

- `user_fund_positions` 是组合、建议和 Agent 查询的唯一持仓来源；没有录入持仓的用户会得到空组合，不会自动获得预置基金。
- 每日净值采集汇总所有活跃用户的真实持仓基金代码；同一基金被多个用户或平台持有时只采集一次。
- 每日净值采集按周一至周五运行，尚未接入交易所节假日历。基金净值和收益展示取决于公开数据源的实际更新时间。

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
│   │   ├── agent/                # Provider、受约束规划、工具执行、质量门与流式服务
│   │   ├── models/               # 市场、建议、会话、用户与持仓 ORM 模型
│   │   ├── services/             # 分析器、建议生成、数据采集与调度
│   │   └── auth.py               # 会话与权限控制
│   ├── alembic/                  # 数据库迁移
│   ├── evals/                    # Agent 离线 fixture 与评测运行器
│   ├── tests/                    # 存储层、持仓与 Agent 测试
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/views/                # 登录、市场、基金、板块、建议、AI 设置页面
│   ├── src/api/                  # HTTP 与 SSE 客户端封装
│   ├── Dockerfile
│   └── nginx.conf
├── docs/                        # 部署说明、改进方案与评测报告
├── docker-compose.yml
└── .env.production.example
```

## 本地开发

### 前置条件

- Python 3.11+ 与 [uv](https://docs.astral.sh/uv/)
- Node.js 22+（前端镜像使用 Node 22；本地应使用兼容版本）
- PostgreSQL 16+
- 可用的 OpenAI 或 Anthropic API Key（仅 AI 问答需要）

### 1. 启动后端

在 `backend/.env` 中配置本地 PostgreSQL 连接、JWT 密钥和初始管理员。例如：

```dotenv
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/invest_assistant
JWT_SECRET=replace-with-a-unique-secret-of-at-least-32-characters
BOOTSTRAP_ADMIN_USERNAME=admin
BOOTSTRAP_ADMIN_PASSWORD=change-this-to-a-strong-password
SESSION_SECURE=false
CORS_ORIGINS=http://localhost:3001,http://127.0.0.1:3001
RUN_MIGRATIONS_ON_STARTUP=false
```

然后安装依赖、执行迁移并启动：

```powershell
cd backend
uv sync --extra test
uv run alembic upgrade head
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001
```

`JWT_SECRET` 至少 32 个字符，初始管理员密码至少 12 个字符。市场和持仓页面不需要 LLM Key；使用 AI 助手前需在 `backend/.env` 配置 `LLM_PROVIDER`、对应的 API Key 和模型。

### 2. 启动前端

另开终端，在项目根目录执行：

```powershell
cd frontend
npm ci
npm run dev
```

- 前端：<http://localhost:3001>
- API 文档：<http://localhost:8001/docs>

首次登录使用上一步通过 `BOOTSTRAP_ADMIN_USERNAME` 和 `BOOTSTRAP_ADMIN_PASSWORD` 创建的管理员账号。

### 从旧版升级数据库

迁移 `c0d1e2f3a4b5` 会删除旧的 `user_portfolio_items` 表及其中记录，不会将预设权重转换成真实持仓。升级前如需保留旧记录，请先自行导出；升级后，只有旧配置、没有 `user_fund_positions` 记录的用户需要在“基金持仓”页面重新录入。已有真实持仓不受这次删表影响。

本地执行 `uv run alembic upgrade head` 时会应用该迁移。Docker Compose 的 `migrate` 服务会在后端启动前自动应用迁移。

## Docker 部署

生产或演示环境推荐使用 Docker Compose：

```powershell
Copy-Item .env.production.example .env.production
# 编辑 .env.production，设置数据库密码、JWT_SECRET、管理员密码、访问域名和所用 LLM Key
docker compose --env-file .env.production up -d --build
docker compose --env-file .env.production ps
```

默认访问地址为 <http://localhost:8080>。仅在本机用 HTTP 测试登录时将 `SESSION_SECURE` 设为 `false`；生产环境应通过 HTTPS 访问并保留 `SESSION_SECURE=true`。详细配置、运维命令和数据卷注意事项见 [Docker 部署文档](docs/docker-deployment.md)。

## 验证

```powershell
# 前端生产构建
cd frontend
npm run build

# 后端测试（先用 uv 安装与锁文件一致的依赖）
cd ../backend
uv sync --extra test
uv run pytest -q
uv run python -m evals.runner
```

截至 2026-10-13，前端最近一次构建成功，但仍有超过 500 kB 的产物警告。后端测试在锁定依赖环境中的结果为 **54 passed**；Agent 离线评测为 **20/20**。离线评测默认以 2026-09-14 为基准日，各用例也可单独指定 `evaluation_date`；[评测报告](docs/agent-eval-report.md)分别记录评测基准日和生成日期。后端测试应使用 `uv` 的锁定依赖环境执行，避免全局 Python 中 pandas/NumPy ABI 不匹配导致的收集失败。

## 风险提示

本项目仅用于学习和信息辅助，不构成投资建议。市场数据可能延迟、缺失或受第三方数据源限制；任何投资决策均应由用户独立判断并自行承担风险。

## License

MIT

---

创建日期：2026-07-02 · 本次状态更新：2026-10-13
