# 个人投资助手

一个轻量化的个人投资分析助手系统，帮助用户分析市场、判断板块走势，给出加仓/止盈建议。

## 核心功能

- **市场概览**：实时掌握大盘、指数、板块动态
- **基金分析**：多维度分析基金表现（技术面、估值、资金流向、情绪）
- **板块走势**：分析行业/概念板块轮动趋势
- **智能建议**：基于多维度分析，给出加仓/持有/减仓建议及仓位比例

## 核心特色

### 可信的建议系统

每个建议都有完整的证据链：
- 多维度独立分析（技术、估值、资金、情绪）
- 信号一致性检验（各维度是否达成共识）
- 环境适应性调整（根据市场环境动态调整权重）
- 明确的置信度评估和风险提示

### 多数据源整合

从多个渠道获取数据，确保信息全面准确：
- 天天基金
- 东方财富
- 同花顺
- 其他主流财经数据源

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端** | Python + FastAPI |
| **前端** | Vue 3 + Vite + ECharts |
| **数据库** | SQLite |
| **数据分析** | pandas, pandas-ta |
| **数据源** | 天天基金、东方财富、同花顺 |

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
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 3. 前端（新开终端）
cd frontend
npm install
npm run dev
```

### 访问

- **前端界面**：http://localhost:5173
- **API文档**：http://localhost:8000/docs

## 项目结构

```
personal-invest-assistant/
├── backend/                # 后端服务
│   ├── app/
│   │   ├── api/           # API路由
│   │   ├── models/        # 数据模型
│   │   ├── services/      # 业务逻辑
│   │   │   ├── analyzer/      # 分析引擎
│   │   │   └── data_collector/ # 数据采集
│   │   └── utils/         # 工具函数
│   └── data/              # 数据存储
├── frontend/              # 前端界面
│   └── src/
│       ├── views/         # 页面
│       ├── components/    # 组件
│       └── api/           # API调用
└── docs/                  # 文档
```

## 开发状态

🚧 **设计中** - 尚未开始开发

## 文档

详细设计方案请查看：[设计方案文档](./docs/design.md)

## 风险提示

**本系统仅供学习和参考，不构成投资建议。**

投资有风险，入市需谨慎。系统给出的建议基于历史数据和技术分析，不能预测未来市场走势。用户应根据自身情况独立判断，承担投资风险。

## License

MIT

---

*创建日期：2026-07-02*
