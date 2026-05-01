from __future__ import annotations

import argparse
import json
import subprocess
import sys


def gather_diff() -> str:
    """Gather the full git diff of this branch vs the default branch."""
    try:
        default_branch = subprocess.run(
            ["gh", "repo", "view", "--json", "defaultBranchRef", "--jq", ".defaultBranchRef.name"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        default_branch = "main"

    result = subprocess.run(
        ["git", "diff", f"{default_branch}...HEAD"],
        capture_output=True,
        text=True,
    )
    return result.stdout


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find bugs, security vulnerabilities, and code quality issues in branch changes."
    )
    parser.add_argument(
        "--diff",
        type=str,
        default=None,
        help="Full git diff string. If omitted, gathered automatically via git diff.",
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text).",
    )
    args = parser.parse_args()

    diff = args.diff if args.diff is not None else gather_diff()

    from .pipeline import run_pipeline

    report = run_pipeline(diff=diff)

    if args.output_format == "json":
        print(report.model_dump_json(indent=2))
    else:
        if not report.issues:
            print("No significant issues found.")
        else:
            print(f"Found {len(report.issues)} issue(s):\n")
            for issue in report.issues:
                print(f"  [{issue.severity}] {issue.file_line}")
                print(f"  Problem:   {issue.problem}")
                print(f"  Evidence:  {issue.evidence}")
                print(f"  Fix:       {issue.fix}")
                if issue.references:
                    print(f"  Refs:      {', '.join(issue.references)}")
                print()

        print("Reviewed files:")
        for f in report.reviewed_files:
            print(f"  {f}")

        if report.unverified_areas:
            print("\nUnverified areas:")
            for area in report.unverified_areas:
                print(f"  {area}")


if __name__ == "__main__":
    main()
