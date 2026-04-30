"""CLI entry point for clawdefender_mellea."""

import argparse
import json
import sys

from .pipeline import run_pipeline
from .schemas import SecurityScanResult


def _cli_dispatch(args: argparse.Namespace) -> SecurityScanResult:
    """Dispatch to run_pipeline based on parsed CLI arguments."""
    return run_pipeline(
        input_text=args.input_text,
        check_mode=args.check_mode,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="clawdefender-mellea",
        description="ClawDefender security scanner — Mellea-wrapped Python interface.",
    )
    parser.add_argument(
        "input_text",
        nargs="?",
        default="",
        help=(
            "Text, URL, skill name, or directory path to scan. "
            "Leave empty for workspace-wide audit."
        ),
    )
    parser.add_argument(
        "--check-mode",
        default="validate",
        choices=["validate", "check_url", "check_prompt", "sanitize", "audit", "scan_skill", "install", "auto"],
        help=(
            "Scan operation to perform. "
            "validate: full multi-category text check (default). "
            "check_url: SSRF/exfiltration URL check. "
            "check_prompt: prompt injection stdin check. "
            "sanitize: sanitize external input. "
            "audit: workspace-wide audit. "
            "scan_skill: recursive directory scan. "
            "install: safe skill installation + scan. "
            "auto: LLM-classified intent dispatch."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON.",
    )

    args = parser.parse_args()

    try:
        result = _cli_dispatch(args)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(result.model_dump_json(indent=2))
    else:
        status = "✅ Clean" if result.clean else f"🔴 {result.severity.upper()} — action: {result.action}"
        print(status)
        if result.findings:
            for f in result.findings:
                print(f"  [{f.module}] {f.pattern} (score {f.score})")
        if result.raw_output and not result.clean:
            print("\nRaw output:")
            print(result.raw_output)

    sys.exit(0 if result.clean else 1)


if __name__ == "__main__":
    main()
