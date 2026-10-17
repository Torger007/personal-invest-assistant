"""Load only explicitly registered Agent skills from this package."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re

import yaml

from app.agent.policy import ToolMode, get_tool_policy
from app.agent.tools.definitions import get_tool_definition


SKILL_DIR = Path(__file__).parent
REGISTERED_SKILLS = {"portfolio_review"}


@dataclass(frozen=True)
class SkillDefinition:
    id: str
    version: str
    instructions: str
    allowed_tools: frozenset[str]
    required_tools: frozenset[str]
    supplement_tools: frozenset[str]
    max_tool_calls: int
    max_supplement_calls: int
    chat_patterns: tuple[str, ...]


@lru_cache(maxsize=8)
def get_skill(skill_id: str) -> SkillDefinition:
    if skill_id not in REGISTERED_SKILLS:
        raise ValueError(f"未注册的 Agent Skill: {skill_id}")
    directory = SKILL_DIR / skill_id
    config = yaml.safe_load((directory / "manifest.yaml").read_text(encoding="utf-8"))
    instructions = (directory / "SKILL.md").read_text(encoding="utf-8").strip()
    if not isinstance(config, dict) or config.get("id") != skill_id or not instructions:
        raise ValueError(f"Skill 配置无效: {skill_id}")
    version = config.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError(f"Skill 版本无效: {skill_id}")
    allowed = frozenset(config.get("allowed_tools") or [])
    required = frozenset(config.get("required_tools") or [])
    supplement = frozenset(config.get("supplement_tools") or [])
    if not allowed or not required <= allowed or not supplement <= allowed:
        raise ValueError(f"Skill 工具集合无效: {skill_id}")
    for tool in allowed:
        policy = get_tool_policy(tool)
        if (policy is None or get_tool_definition(tool) is None
                or not policy.llm_plannable or policy.mode is ToolMode.CONTROLLED_WRITE):
            raise ValueError(f"Skill 包含未经授权的工具: {tool}")
    max_calls = config.get("max_tool_calls")
    max_supplements = config.get("max_supplement_calls")
    chat_patterns = config.get("chat_patterns")
    if (not isinstance(chat_patterns, list) or not chat_patterns
            or any(not isinstance(pattern, str) or len(pattern) > 160 for pattern in chat_patterns)):
        raise ValueError(f"Skill 触发条件无效: {skill_id}")
    for pattern in chat_patterns:
        re.compile(pattern)
    if (not isinstance(max_calls, int) or isinstance(max_calls, bool) or not 1 <= max_calls <= 10
            or not isinstance(max_supplements, int) or isinstance(max_supplements, bool)
            or not 0 <= max_supplements <= 2):
        raise ValueError(f"Skill 预算无效: {skill_id}")
    return SkillDefinition(
        skill_id, version, instructions, allowed, required, supplement,
        max_calls, max_supplements, tuple(chat_patterns),
    )


def match_skill(question: str) -> str | None:
    """Conservative chat routing; explicit API entry selects the skill directly."""
    text = re.sub(r"\s+", "", question)
    for skill_id in sorted(REGISTERED_SKILLS):
        if any(re.search(pattern, text) for pattern in get_skill(skill_id).chat_patterns):
            return skill_id
    return None
