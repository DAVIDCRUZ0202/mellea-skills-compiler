"""Audit trail hook — records every pipeline event to a JSONL log.

Captures generation calls, Guardian verdicts, component lifecycle events,
and validation outcomes.  Designed to compose with GuardianAuditPlugin
(priority 40) — this hook runs at priority 100 so Guardian verdicts are
available in user_metadata by the time we log.

Usage:
    from audit_trail_hook import AuditTrailPlugin
    plugin = AuditTrailPlugin(log_path="audit.jsonl")
    register(plugin)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mellea.plugins import HookType, Plugin, PluginMode, hook

from mellea_skills_compiler.toolkit.logging import configure_logger


log = configure_logger("mellea_skills_compiler.audit")


class AuditTrailPlugin(Plugin, name="mellea_skills_compiler-audit-trail", priority=100):
    """Append-only JSONL audit trail for GraniteClawHub PoC.

    Each entry contains:
      - timestamp, hook_type, session_id, request_id
      - event-specific data (prompt preview, output preview, verdicts, etc.)
      - optional policy_id for traceability to organisational policy

    The priority (100) ensures this runs after all transform/sequential hooks,
    so user_metadata is fully populated (e.g. Guardian verdicts at pri 40).
    """

    def __init__(
        self,
        log_path: str | Path = "audit_trail.jsonl",
        policy_id: str = "",
        guardian_ref: Any = None,
    ):
        self.log_path = Path(log_path)
        self.policy_id = policy_id
        self._guardian_ref = guardian_ref
        self._entries: list[dict] = []

    def _write(self, entry: dict) -> None:
        entry["timestamp"] = datetime.now(UTC).isoformat()
        if self.policy_id:
            entry["policy_id"] = self.policy_id
        self._entries.append(entry)
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    # ── Generation hooks ────────────────────────────────────────────

    @hook(HookType.GENERATION_PRE_CALL, mode=PluginMode.AUDIT)
    async def log_pre_call(self, payload: Any, ctx: Any) -> None:
        """Log the prompt being sent to the LLM."""
        prompt = payload.prompt if hasattr(payload, "prompt") else ""
        action_preview = str(getattr(payload, "action", ""))[:200]
        self._write(
            {
                "hook": "generation_pre_call",
                "session_id": getattr(payload, "session_id", ""),
                "request_id": getattr(payload, "request_id", ""),
                "action_preview": action_preview.replace("\n", " "),
                "model_options": dict(getattr(payload, "model_options", {})),
            }
        )

    @hook(HookType.GENERATION_POST_CALL, mode=PluginMode.AUDIT)
    async def log_post_call(self, payload: Any, ctx: Any) -> None:
        """Log LLM output and any Guardian verdicts."""
        mot = payload.model_output
        output_text = getattr(mot, "value", "") or "" if mot else ""
        latency = getattr(payload, "latency_ms", 0)

        # Try user_metadata first, then fall back to the Guardian plugin ref
        verdicts = payload.user_metadata.get("guardian_verdicts", [])
        if not verdicts and self._guardian_ref is not None:
            # Read the most recent verdicts from the Guardian plugin directly
            recent = self._guardian_ref.all_verdicts[-len(self._guardian_ref.risks) :]
            verdicts = [
                {
                    "risk": v.risk,
                    "label": v.label,
                    "raw": v.raw_output,
                    "ts": v.timestamp,
                }
                for v in recent
            ]

        any_risk = any(v.get("label") == "Yes" for v in verdicts)

        self._write(
            {
                "hook": "generation_post_call",
                "session_id": getattr(payload, "session_id", ""),
                "request_id": getattr(payload, "request_id", ""),
                "output_preview": output_text[:300].replace("\n", " "),
                "latency_ms": latency,
                "guardian_verdicts": verdicts,
                "risk_detected": any_risk,
            }
        )

        if any_risk:
            flagged = [v["risk"] for v in verdicts if v.get("label") == "Yes"]
            log.warning("[audit] RISK DETECTED — flagged risks: %s", ", ".join(flagged))

    # ── Component hooks ─────────────────────────────────────────────

    @hook(HookType.COMPONENT_PRE_EXECUTE, mode=PluginMode.AUDIT)
    async def log_component_start(self, payload: Any, ctx: Any) -> None:
        self._write(
            {
                "hook": "component_pre_execute",
                "session_id": getattr(payload, "session_id", ""),
                "component_type": getattr(payload, "component_type", ""),
            }
        )

    @hook(HookType.COMPONENT_POST_SUCCESS, mode=PluginMode.AUDIT)
    async def log_component_success(self, payload: Any, ctx: Any) -> None:
        self._write(
            {
                "hook": "component_post_success",
                "session_id": getattr(payload, "session_id", ""),
                "component_type": getattr(payload, "component_type", ""),
                "latency_ms": getattr(payload, "latency_ms", 0),
            }
        )

    @hook(HookType.COMPONENT_POST_ERROR, mode=PluginMode.AUDIT)
    async def log_component_error(self, payload: Any, ctx: Any) -> None:
        self._write(
            {
                "hook": "component_post_error",
                "session_id": getattr(payload, "session_id", ""),
                "component_type": getattr(payload, "component_type", ""),
                "error": str(getattr(payload, "error", "")),
            }
        )

    # ── Validation hooks ────────────────────────────────────────────

    @hook(HookType.VALIDATION_POST_CHECK, mode=PluginMode.AUDIT)
    async def log_validation(self, payload: Any, ctx: Any) -> None:
        self._write(
            {
                "hook": "validation_post_check",
                "session_id": getattr(payload, "session_id", ""),
                "passed": getattr(payload, "passed", None),
                "reason": getattr(payload, "reason", ""),
            }
        )

    # ── Tool hooks (Pattern 3: LLM-directed tool calls) ──────────

    @hook(HookType.TOOL_PRE_INVOKE, mode=PluginMode.AUDIT)
    async def log_tool_pre(self, payload: Any, ctx: Any) -> None:
        """Log tool call before execution."""
        tool_call = payload.model_tool_call
        self._write(
            {
                "hook": "tool_pre_invoke",
                "session_id": getattr(payload, "session_id", ""),
                "tool_name": getattr(tool_call, "name", "unknown"),
                "tool_args": str(getattr(tool_call, "args", {}))[:300],
                "governance": "pattern3_llm_directed",
            }
        )

    @hook(HookType.TOOL_POST_INVOKE, mode=PluginMode.AUDIT)
    async def log_tool_post(self, payload: Any, ctx: Any) -> None:
        """Log tool result after execution."""
        tool_call = payload.model_tool_call
        tool_name = getattr(tool_call, "name", "unknown")
        tool_output = str(payload.tool_output or "")

        # Check for Guardian verdicts on tool output
        verdicts = []
        if self._guardian_ref is not None:
            # Look for tool-prefixed verdicts added by Guardian
            recent = [
                v for v in self._guardian_ref.all_verdicts if v.risk.startswith("tool:")
            ]
            verdicts = [
                {
                    "risk": v.risk,
                    "label": v.label,
                    "raw": v.raw_output,
                    "ts": v.timestamp,
                }
                for v in recent[-len(getattr(self._guardian_ref, "risks", [])) :]
            ]

        any_risk = any(v.get("label") == "Yes" for v in verdicts)

        self._write(
            {
                "hook": "tool_post_invoke",
                "session_id": getattr(payload, "session_id", ""),
                "tool_name": tool_name,
                "tool_args": str(getattr(tool_call, "args", {}))[:300],
                "output_preview": tool_output[:300],
                "execution_time_ms": payload.execution_time_ms,
                "success": payload.success,
                "error": str(payload.error) if payload.error else "",
                "guardian_verdicts": verdicts,
                "risk_detected": any_risk,
                "governance": "pattern3_llm_directed",
            }
        )

        if any_risk:
            flagged = [v["risk"] for v in verdicts if v.get("label") == "Yes"]
            log.warning("[audit] TOOL RISK — %s: %s", tool_name, ", ".join(flagged))

    # ── Summary ─────────────────────────────────────────────────────

    def summary(self) -> dict:
        """Return a summary of the audit trail for display."""
        total = len(self._entries)
        generations = [e for e in self._entries if e["hook"] == "generation_post_call"]
        tool_calls = [e for e in self._entries if e["hook"] == "tool_post_invoke"]
        gen_risks = [e for e in generations if e.get("risk_detected")]
        tool_risks = [e for e in tool_calls if e.get("risk_detected")]
        return {
            "total_events": total,
            "generations": len(generations),
            "tool_calls": len(tool_calls),
            "generation_risks_flagged": len(gen_risks),
            "tool_risks_flagged": len(tool_risks),
            "log_file": str(self.log_path),
        }
