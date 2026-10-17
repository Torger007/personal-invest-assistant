# 持仓复盘 Skill 运行契约（第三步）

## 位置与入口

所有业务 Skill 统一放在 `backend/app/agent/skills/`。当前仅注册 `portfolio_review`。注册器显式读取版本化 `manifest.yaml` 与 `SKILL.md`，并在加载时核对工具权限和预算；提示文件本身不能授予工具权限。

- `POST /agent/portfolio-review` 手动发起，复用现有任务状态与 SSE 事件端点。
- 聊天中明确要求“持仓复盘”“组合复盘”“持仓与上次相比”等诉求时，路由到同一 Skill；普通持仓分析沿用通用问答。
- Skill 始终使用受约束的规划与执行链。工具从认证上下文获取 `user_id`，模型不能指定其他用户。

## 执行边界

允许工具与必需工具由 `manifest.yaml` 声明，经服务端工具策略二次校验。初始计划使用 `get_portfolio`、`get_market_overview`、`get_latest_advice`、`compare_funds`；单基金净值与板块趋势仅在需要时读取。受控写入工具不在 Skill 白名单中。

同一计划可用不同步骤 ID 多次调用只读工具。整次运行最多 10 次工具调用，质量门触发的补查最多 2 次；按工具定义的次数上限也跨计划累计。规划器只看到剩余预算，超限计划不会执行。

复盘质量门以沪市交易日历判断净值与市场数据的预期日期，并区分净值公布窗口。持仓使用校准值、数据缺失或过期、交易日历不可用时输出降级状态。缺失数据可以有限补查，不能靠新的文字解释消除质量门判定。

## 报告契约

模型通过 `submit_portfolio_review` 提交 `PortfolioReviewResult`。服务端负责填入本次运行与各数据的时间，核对本次及历史证据 ID、比较状态和操作边界；无效输出转为不含臆测关注项的降级报告。`review_ready` 与 `complete` 事件携带结构化报告，执行轨迹记录 Skill 版本与引用的最小证据快照。

手动运行的进度仍使用现有任务流；报告在展示前写入独立 `PortfolioReview` 记录。普通聊天摘要与 `AgentAnalysis` 不作为“上次判断”的权威来源。偏好和历史记录的读写语义见 `portfolio-review-memory.md`。
