# 持仓复盘偏好与历史记录（第四步）

## 用户偏好

`GET /agent/preferences` 返回当前用户已确认的风险偏好、投资期限、关注目标、备注、来源、确认时间和版本。未设置的字段为 `unknown`；`PUT /agent/preferences` 是整份替换，只有用户主动调用才写入，版本递增。`DELETE /agent/preferences` 清空字段和备注，后续运行视为未知；记录只保留空值与版本计数，避免重新设置时版本重用。模型收到的是运行开始时的偏好快照，没有自动写入长期偏好的权限。

风险偏好取 `conservative`、`balanced`、`aggressive` 或 `unknown`；投资期限取 `short`、`medium`、`long` 或 `unknown`。关注目标最多 8 项，每项 1–60 字；备注最多 500 字。

## 独立复盘记录

前端以“问 AI”中的推荐提问“帮我分析当前持仓”为手动入口；等价的明确持仓分析问题进入同一复盘 Skill。历史页位于 `/portfolio-reviews`，对话完成后可直达对应报告。前端不额外设置发起按钮；下述直接发起 API 保留给 API 客户端使用。

`POST /agent/portfolio-review` 先建立 `running` 记录；`review_started` 事件包含复盘 ID。`GET /agent/portfolio-reviews` 和 `GET /agent/portfolio-reviews/{id}` 从数据库读取状态、结构化报告、证据、快照及版本，所有查询以认证用户 ID 限定。报告持久化成功后才发出 `review_ready` 和 `complete`。失败与中断记录保留可见错误；运行期间持续更新心跳，服务启动及读取历史时仅将超过 45 秒没有心跳的运行标为 `interrupted`，用户可重新发起。

记录保存运行与数据时间、持仓/市场/建议快照、上次复盘 ID、偏好版本、Skill / Prompt / 规则版本、结构化结果、证据依赖闭包、质量报告和错误信息。原有 `AgentAnalysis` 仅保留兼容性的运行轨迹。

## “与上次相比”

比较基线仅取同一用户最近一次 `completed`、`ready` 且证据契约完整的独立复盘。失败、中断、降级、普通聊天和单基金建议都不成为基线。首次复盘明确标记 `first_review`。

服务端从两次保存的快照比较基金增删、份额与权重、净值与市场数据、规则建议和质量状态；变化类别、描述、证据 ID 与时间由服务端生成。模型不能仅因措辞不同声明新变化。缺少能够证明变化的证据时降级，说明比较限制。
