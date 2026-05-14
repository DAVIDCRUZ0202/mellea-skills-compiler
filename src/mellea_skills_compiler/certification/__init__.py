from typing import Any


def skill_to_use_case(parsed: dict[str, Any], sensitivity: dict[str, Any]) -> str:
    """Compose a use-case description from parsed skill + sensitivity."""
    fm = parsed["frontmatter"]
    name = fm.get("name", "unknown skill")
    description = fm.get("description", "")
    tools = fm.get("allowed-tools", [])

    parts = [f"An AI agent skill called '{name}' that {description}"]

    if tools:
        parts.append(f"The skill has access to: {', '.join(tools)}.")

    parts.append(f"Sensitivity tier: {sensitivity['tier_display']}.")

    if sensitivity["operations"]:
        parts.append(f"Operations: {', '.join(sensitivity['operations'])}.")

    if sensitivity["capabilities"]:
        parts.append(f"Capabilities: {'; '.join(sensitivity['capabilities'])}.")

    return " ".join(parts)
