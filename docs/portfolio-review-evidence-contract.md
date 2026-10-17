# 持仓复盘证据契约（第二步）

关键工具输出由 `backend/app/agent/tools/output_contracts.py` 的 Pydantic 模型校验和投影；统一外壳由 `ToolResultEnvelope` 定义。规划器的输入白名单保持在 `tools/definitions.py`，输出校验在服务端执行。校验失败返回 `invalid_tool_output`，不会把不合格数字传给总结模型。

## 时间与来源

- `as_of` 是事实所代表的日期。组合估值与市场概览顶层取可验证事实中最早的日期；建议及比较工具顶层取最早的建议日期，供建议时效检查使用。每条 `evidence` 仍保留自己的实际日期。
- 外壳 `fetched_at` 是本次工具读取时间，`retrieval_tool` 是读取工具。证据的 `source` 是原始来源，`source_fetched_at` 是可证明的原始抓取时间；未知时保留 `unknown` / `null`，不能用读取时间补造。
- `source_ref` 指向持仓、净值、指数、资金流或建议记录。派生权重通过 `depends_on_evidence_ids` 引用构成总市值的逐笔估值，保存引用时会连同依赖一并复制。
- `unit`、`calculation_basis`、`status` 和 `quality_flags` 随事实保存。校准值、未知来源、缺少建议和截断均有显式标记。

## 关键工具边界

| 工具 | 输出上限 | 证据粒度 |
| --- | ---: | --- |
| `get_portfolio` | 50 只基金、100 笔估值 | 逐笔估值与组合权重 |
| `get_market_overview` | 3 个指数及 1 条资金流 | 指数最新与前收记录、资金流记录 |
| `get_latest_advice` | 20 条建议或 20 只基金 | 规则建议记录及组合权重依赖 |
| `compare_funds` | 20 只基金、100 笔组合估值 | 建议与权重比较，关联原始记录 |
| `get_fund_nav` | 最多 365 条净值；最近 10 条进入候选证据 | 基金代码、净值日期和来源 |

超限结果标为 `partial`，保留原始 `count` 并添加 `output_truncated`，不能把显示的子集当成完整组合。模型输入只包含投影字段，原始建议长文本和未声明字段不进入关键工具输出。

## 保存与引用

现有受约束运行会把有界候选证据写入 `AgentAnalysis.tool_calls.evidence_candidates`，不保存完整工具原始数据。`select_evidence_snapshot(results, evidence_ids)` 在生成结构化复盘后只选择实际引用的事实和其依赖，未知 ID 或循环依赖会报错。第四步的 `PortfolioReview` 持久化接入该选择函数，使报告保留可回看的最小证据快照。
