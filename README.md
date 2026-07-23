# 个人投资助手

一个轻量化的个人投资分析助手系统，帮助用户分析市场、判断板块走势，给出加仓/止盈建议。

## 核心功能

- **市场概览**：实时掌握大盘指数（上证、深证、创业板）点位与涨跌幅，跟踪北向资金、主力资金流向
- **基金分析**：多维度分析基金表现（技术面、估值、资金流向、情绪）
- **板块走势**：分析行业/概念板块轮动趋势，支持查看板块 K 线图
- **智能建议**：基于多维度分析，给出加仓/持有/减仓建议及仓位比例，附完整证据链与置信度
- **AI 问答**：支持自然语言查询基金信息、市场分析，对接 OpenAI/Anthropic

## 核心特色

### 可信的建议系统

每个建议都有完整的证据链：
- 多维度独立分析（技术、估值、资金、情绪）
- 信号一致性检验（各维度是否达成共识）
- 环境适应性调整（根据市场环境动态调整权重）
- 明确的置信度评估和风险提示

### 多数据源整合

通过 [AKShare](https://github.com/akfamily/akshare) 统一接入多个财经数据渠道，确保信息全面准确：
- 指数行情（上证、深证、创业板、沪深300、中证500）
- 资金流向（北向资金、主力资金）
- 基金净值与基本信息
- 板块数据（概念/行业板块涨跌排行）
- 更多数据持续接入中

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端** | Python 3.9+ · FastAPI · SQLAlchemy (async) |
| **前端** | Vue 3 · Vite · Element Plus · ECharts |
| **数据库** | SQLite（aiosqlite 异步驱动） |
| **数据采集** | AKShare（同步，asyncio.to_thread 包装） |
| **定时任务** | APScheduler（每日 16:30 自动更新） |
| **技术分析** | ta（Technical Analysis library） |

## 快速开始

### 环境要求

- Python 3.9+
- Node.js 16+

### 安装步骤

```bash
# 1. 克隆项目
git clone <your-repo-url>
cd personal-invest-assistant

# 2. 后端
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001

# 3. 前端（新开终端）
cd frontend
npm install
npm run dev
```

首次启动后，可在前端「市场概览」页面点击「手动采集数据」按钮，或等待每日 16:30 自动采集。

### 访问

- **前端界面**：http://localhost:5173
- **API 文档**：http://localhost:8001/docs

## 项目结构

```
personal-invest-assistant/
├── backend/                          # 后端服务
│   ├── app/
│   │   ├── api/                      # API 路由
│   │   │   ├── market.py             #   市场概览、指数、资金流向、板块
│   │   │   ├── funds.py              #   基金列表与详情
│   │   │   ├── advice.py             #   投资建议
│   │   │   ├── agent.py              #   AI 问答接口
│   │   │   └── tasks.py              #   手动/自动数据更新任务
│   │   ├── models/                   # 数据模型（SQLAlchemy ORM）
│   │   ├── agent/                    # AI Agent 模块
│   │   │   ├── core.py               #   Agent 核心（工具调用循环）
│   │   │   ├── providers/            #   LLM 提供商适配器
│   │   │   └── tools/                #   Agent 工具定义
│   │   ├── services/
│   │   │   ├── analyzer/             # 分析引擎
│   │   │   │   ├── technical.py      #   技术分析（均线、动量、量价）
│   │   │   │   ├── valuation.py      #   估值分析
│   │   │   │   ├── fund_flow.py      #   资金流向分析
│   │   │   │   ├── sentiment.py      #   市场情绪分析
│   │   │   │   ├── sector.py         #   板块分析
│   │   │   │   ├── advisor.py        #   综合建议生成器
│   │   │   │   └── result.py         #   统一分析结果结构
│   │   │   ├── data_collector/       # 数据采集
│   │   │   │   ├── akshare_source.py #   AKShare 数据源
│   │   │   │   ├── storage.py        #   数据库存储层
│   │   │   │   └── scheduler.py      #   定时任务调度器
│   │   │   └── advice_service.py     # 建议服务
│   │   └── utils/
│   │       └── db.py                 # 异步数据库初始化
│   ├── data/                         # SQLite 数据库文件
│   └── requirements.txt
├── frontend/                         # 前端界面
│   └── src/
│       ├── views/
│       │   ├── MarketOverview.vue    # 市场概览（指数卡片 + 资金流向）
│       │   ├── FundList.vue          # 基金列表
│       │   ├── FundDetail.vue        # 基金详情（净值走势、收益计算）
│       │   ├── SectorAnalysis.vue    # 板块走势（涨跌排行 + K线图）
│       │   ├── AdviceReport.vue      # 投资建议报告
│       │   └── AgentSettings.vue     # AI 设置
│       ├── api/index.js              # Axios API 封装
│       └── router/index.js           # 路由配置
├── scripts/
│   ├── init_db.py                    # 数据库初始化脚本
│   └── fetch_sample_data.py          # 手动数据采集脚本
└── docs/                             # 设计文档
```

## 开发状态

✅ **核心功能已完成** — 系统已可用，持续优化中。

| 模块 | 状态 | 说明 |
|------|------|------|
| 指数行情采集（AKShare） | ✅ 已完成 | 上证、深证、创业板、沪深300、中证500 |
| 资金流向采集 | ✅ 已完成 | 北向资金、主力资金流向 |
| 市场概览页面 | ✅ 已完成 | 指数卡片 + 资金流向图表 |
| 定时调度器（每日 16:30） | ✅ 已完成 | APScheduler 自动采集 |
| 手动数据刷新 API | ✅ 已完成 | 支持指数、基金、板块数据刷新 |
| 前端基础框架与路由 | ✅ 已完成 | Vue 3 + Element Plus + 暗黑主题 |
| 技术分析引擎 | ✅ 已完成 | 均线、动量、量价分析 |
| 估值分析引擎 | ✅ 已完成 | PE/PB 分位数分析 |
| 资金流向分析 | ✅ 已完成 | 北向/主力资金趋势分析 |
| 情绪分析引擎 | ✅ 已完成 | 市场恐慌/贪婪指数 |
| 基金净值采集 | ✅ 已完成 | 支持 90 天历史净值 |
| 基金列表与详情 | ✅ 已完成 | 净值走势、收益计算、基本信息 |
| 板块数据采集 | ✅ 已完成 | 概念/行业板块涨跌排行 |
| 板块走势页面 | ✅ 已完成 | 资金流向趋势、板块 K 线图 |
| 综合建议生成 | ✅ 已完成 | 多维度评分 + 信号一致性检验 |
| AI 问答助手 | ✅ 已完成 | Agent 工具调用 + OpenAI/Anthropic 支持 |

### 🚧 待优化项

- [ ] 板块历史数据持久化存储
- [ ] 用户设置持久化（AI Provider 配置）
- [ ] 更多技术指标（MACD、RSI、布林带）
- [ ] 投资组合跟踪功能

## 文档

详细设计方案请查看：[设计方案文档](./docs/design.md)

## 风险提示

**本系统仅供学习和参考，不构成投资建议。**

投资有风险，入市需谨慎。系统给出的建议基于历史数据和技术分析，不能预测未来市场走势。用户应根据自身情况独立判断，承担投资风险。

## License

MIT

---

*创建日期：2026-07-02 · 最后更新：2026-07-23*
