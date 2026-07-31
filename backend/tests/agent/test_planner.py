from app.agent.planner import AgentPlanner


def test_single_fund_question_uses_bounded_data_plan():
    plan = AgentPlanner().plan_question("008163 现在能不能加仓？")

    assert plan.intent == "single_fund"
    assert [step.tool_name for step in plan.steps] == [
        "get_fund_info",
        "get_fund_nav",
        "analyze_technical",
        "get_fund_flow",
        "get_latest_advice",
    ]
    assert plan.steps[2].arguments == {"data": {"$ref": "get_fund_nav.data"}}


def test_question_intents_choose_expected_plans():
    planner = AgentPlanner()

    assert planner.plan_question("我的持仓怎么配置？").intent == "portfolio"
    assert planner.plan_question("市场行情怎么样？").intent == "market"
    assert planner.plan_question("新能源板块趋势如何？").intent == "sector"
    assert planner.plan_question("上次是怎么判断的？").intent == "history"


def test_duplicate_fund_codes_are_deduplicated_for_comparison():
    plan = AgentPlanner().plan_question("008163 和 008163、021033 比较")

    assert plan.intent == "fund_comparison"
    assert plan.fund_codes == ["008163", "021033"]
    assert plan.steps[0].arguments == {"fund_codes": ["008163", "021033"]}


def test_followup_uses_the_single_fund_in_active_context():
    plan = AgentPlanner().plan_question(
        "那只基金现在能不能加仓？",
        {"last_fund_codes": ["008163"]},
    )

    assert plan.intent == "single_fund"
    assert plan.fund_codes == ["008163"]
    assert plan.steps[0].arguments == {"fund_code": "008163"}


def test_followup_does_not_guess_when_context_has_multiple_funds():
    plan = AgentPlanner().plan_question(
        "继续说",
        {"last_fund_codes": ["008163", "005827"]},
    )

    assert plan.intent == "general"
    assert plan.fund_codes == []
