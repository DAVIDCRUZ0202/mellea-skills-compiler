from itertools import chain

from mellea_skills_compiler.enums import CoverageLevel
from mellea_skills_compiler.models import (
    ComplianceSummary,
    GovernanceAction,
    PolicyManifest,
    RequirementClassification,
)


def classify_governance_requirements(
    manifest: PolicyManifest,
    nexus,
) -> ComplianceSummary:
    """Classify each governance requirement as AUTOMATED, PARTIAL, or MANUAL
    based on pipeline controls from pipeline_control_mappings.yaml.

    Args:
        manifest (PolicyManifest): _description_
        nexus (_type_): _description_

    Returns:
        ComplianceSummary: _description_
    """

    def _classify_single(
        action: GovernanceAction,
        nexus,
    ) -> list[RequirementClassification]:
        """Classify a single governance action via YAML lookup."""
        classifications = []
        if not action.categorized_as:
            return [
                RequirementClassification(
                    action=action,
                    coverage=CoverageLevel.MANUAL,
                    matched_controls=[],
                )
            ]

        for cat in action.categorized_as:
            entry = nexus.get_by_id(class_name="RiskControlGroup", identifier=cat)
            if entry is None:
                # Unmapped action → MANUAL (conservative default)
                classifications.append(
                    RequirementClassification(
                        action=action,
                        coverage=CoverageLevel.MANUAL,
                        matched_controls=[],
                    )
                )
            else:
                if entry.broader and len(entry.broader) > 0:
                    for b in entry.broader:
                        top_group = nexus.get_by_id(
                            class_name="RiskControlGroup", identifier=b
                        )

                        c_level = CoverageLevel.MANUAL

                        if top_group.name == "Implemented":
                            c_level = CoverageLevel.AUTOMATED

                        classifications.append(
                            RequirementClassification(
                                action=action,
                                coverage=c_level,
                                matched_controls=cat,
                            )
                        )

        return classifications

    all_actions = manifest.governance_actions
    if all_actions:
        classifications = list(
            chain.from_iterable(_classify_single(a, nexus) for a in all_actions)
        )
    else:
        classifications = []
    return ComplianceSummary(classifications=classifications)


def classify_skill_sensitivity(tools: list[str], body: str) -> dict:
    """Classify skill sensitivity from tool list and body keywords.

    # ── Tool sensitivity classification ───────────────────────────────
    #
    # Simple lookup: tool name → sensitivity tier + operation types.
    # Grounded in POSIX permission model (R/W/X) and Google OAuth
    # 3-tier sensitivity (non-sensitive / sensitive / restricted).
    #
    # PROVENANCE: claude-suggested — validate tool classifications

    Returns: tier, operations, and body-detected capabilities.
    """

    TOOL_TIERS = {
        # NON-SENSITIVE: read-only, no side effects
        "Read": {"tier": "non-sensitive", "ops": ["read"]},
        "Grep": {"tier": "non-sensitive", "ops": ["read"]},
        "Glob": {"tier": "non-sensitive", "ops": ["read"]},
        "cat": {"tier": "non-sensitive", "ops": ["read"]},
        # SENSITIVE: write, execute, or network access
        "Bash": {"tier": "sensitive", "ops": ["read", "write", "execute"]},
        "Edit": {"tier": "sensitive", "ops": ["write"]},
        "Write": {"tier": "sensitive", "ops": ["write"]},
        "Task": {"tier": "sensitive", "ops": ["execute"]},
        "curl": {"tier": "sensitive", "ops": ["network_egress", "read"]},
        "gh": {"tier": "sensitive", "ops": ["network_egress"]},
        # RESTRICTED: credentials, destructive, or admin
        "op": {"tier": "restricted", "ops": ["auth_credentials"]},
    }

    TIER_ORDER = {"non-sensitive": 0, "sensitive": 1, "restricted": 2}
    TIER_DISPLAY = {
        "non-sensitive": "NON-SENSITIVE",
        "sensitive": "SENSITIVE",
        "restricted": "RESTRICTED",
    }
    ops = set()
    tier_idx = 0

    for tool in tools:
        entry = TOOL_TIERS.get(tool)
        if entry:
            ops.update(entry["ops"])
            tier_idx = max(tier_idx, TIER_ORDER[entry["tier"]])

    # Body-level escalation for capabilities not visible in tool names
    body_lower = body.lower()
    capabilities = []
    if any(
        kw in body_lower
        for kw in ["api_key", "api key", "secret", "token", "credential"]
    ):
        capabilities.append("manages credentials")
        tier_idx = max(tier_idx, TIER_ORDER["restricted"])
    if any(kw in body_lower for kw in ["delete", "destroy", "drop"]):
        capabilities.append("destructive operations")
    if "deploy" in body_lower:
        capabilities.append("deploys to infrastructure")

    tier_name = {v: k for k, v in TIER_ORDER.items()}[tier_idx]
    return {
        "tier": tier_name,
        "tier_display": TIER_DISPLAY[tier_name],
        "operations": sorted(ops),
        "capabilities": capabilities,
    }
