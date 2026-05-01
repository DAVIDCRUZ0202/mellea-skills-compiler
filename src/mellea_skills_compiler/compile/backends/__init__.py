"""Backend implementations for mellea-skills compilation.

This package contains concrete implementations of the CompilationBackend protocol,
each wrapping a different compilation engine (Claude Code, IBM Bob, local LLMs, etc.).

Available backends:
- claude_code: Uses Anthropic's Claude Code CLI for compilation
"""

from mellea_skills_compiler.compile.backend import register_backend
from mellea_skills_compiler.compile.backends.claude_code import ClaudeCodeBackend

# Register the Claude Code backend
register_backend("claude", ClaudeCodeBackend)

__all__ = ["ClaudeCodeBackend"]
