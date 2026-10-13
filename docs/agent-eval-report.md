# Agent 离线评测报告

- 评测模式：离线 Fixture Planner / Fixture Registry
- 生成日期：2026-10-13
- 评测基准日：2026-09-14
- 用例数量：20
- 覆盖类别：fallback、followup、history、market、missing_data、normal、portfolio、replan、sector、security、tool_error

## 指标汇总

| 指标 | 结果 |
| --- | --- |
| 通过用例数 | 20/20 |
| 用例通过率 | 100.0% |
| 合法计划接受率 | 100.0% |
| 安全案例通过率 | 100.0% |
| 重规划案例通过率 | 100.0% |
| 降级案例通过率 | 100.0% |
| 规则决策案例通过率 | 100.0% |

## 失败案例

| 用例 ID | 失败原因 |
| --- | --- |
| 无 | - |

## 评测边界

- 本报告不调用真实 LLM、AKShare、数据库或用户账户。
- 所有规划输出仍经过生产 `PlanValidator` 校验。
- 所有工具结果仍经过生产执行引擎、质量门和规则决策服务。
- 文本一致性采用确定性规则检查，不使用第二个 LLM 充当裁判。
