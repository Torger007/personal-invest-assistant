"""Prompt loading utilities for the investment agent."""
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


PROMPT_DIR = Path(__file__).parent / "prompts"


class PromptTemplateError(ValueError):
    """Raised when a prompt template is missing or malformed."""


@lru_cache(maxsize=16)
def load_prompt_config(name: str) -> dict[str, Any]:
    """Load a YAML prompt config from the prompt directory."""
    path = PROMPT_DIR / f"{name}.yaml"
    if not path.exists():
        raise PromptTemplateError(f"Prompt config not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise PromptTemplateError(f"Prompt config must be a mapping: {path}")

    return data


def get_agent_system_prompt() -> str:
    """Return the shared system prompt for the investment agent."""
    config = load_prompt_config("agent")
    system_prompt = config.get("system")
    if not isinstance(system_prompt, str) or not system_prompt.strip():
        raise PromptTemplateError("Missing non-empty agent.system prompt")
    return system_prompt.strip()


def render_agent_prompt(template_name: str, **variables: Any) -> str:
    """Render a named task prompt from prompts/agent.yaml."""
    config = load_prompt_config("agent")
    template_config = config.get("tasks", {}).get(template_name)
    if not isinstance(template_config, dict):
        raise PromptTemplateError(f"Missing agent task prompt: {template_name}")

    template = template_config.get("template")
    if not isinstance(template, str) or not template.strip():
        raise PromptTemplateError(f"Missing template body for agent task: {template_name}")

    try:
        return template.format(**variables).strip()
    except KeyError as e:
        raise PromptTemplateError(
            f"Missing variable {e!s} for agent task prompt: {template_name}"
        ) from e
