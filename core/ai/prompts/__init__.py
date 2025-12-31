"""
Prompt management system for CrossBridge AI.

Provides versioned, auditable prompt templates with Jinja2 rendering.
"""

from core.ai.prompts.registry import (
    PromptRegistry,
    PromptRenderer,
    get_prompt,
    get_registry,
    render_prompt,
)

__all__ = [
    "PromptRegistry",
    "PromptRenderer",
    "get_prompt",
    "get_registry",
    "render_prompt",
]
