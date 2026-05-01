import argparse
import sys

from .pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="superpowers-systematic-debugging",
        description=(
            "Systematic debugging investigation pipeline. "
            "Guides through all four phases: Root Cause Investigation, Pattern Analysis, "
            "Hypothesis and Testing, and Implementation planning. "
            "NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "issue_description",
        help="Description of the bug, test failure, or unexpected behavior to investigate",
    )
    parser.add_argument(
        "--error-text",
        default="",
        metavar="TEXT",
        help="Error messages, stack traces, or log output from the failure",
    )
    parser.add_argument(
        "--recent-changes",
        default="",
        metavar="TEXT",
        help="Recent code changes that may be related (git diff, commit log, dependency updates)",
    )
    parser.add_argument(
        "--code-context",
        default="",
        metavar="TEXT",
        help="Relevant code snippets or file contents for data flow tracing",
    )
    parser.add_argument(
        "--working-examples",
        default="",
        metavar="TEXT",
        help="Similar working code or reference implementation to compare against",
    )
    parser.add_argument(
        "--fix-attempts",
        type=int,
        default=0,
        metavar="N",
        help="Number of fix attempts already made in this debugging session (default: 0)",
    )
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format: human-readable text (default) or structured JSON",
    )

    args = parser.parse_args()

    result = run_pipeline(
        issue_description=args.issue_description,
        error_text=args.error_text,
        recent_changes=args.recent_changes,
        code_context=args.code_context,
        working_examples_text=args.working_examples,
        fix_attempts_count=args.fix_attempts,
    )

    if args.output == "json":
        print(result.model_dump_json(indent=2))
    else:
        _print_report(result)


def _print_report(report) -> None:
    print("\n=== SYSTEMATIC DEBUGGING REPORT ===\n")
    print(f"Summary: {report.summary}\n")

    if report.error_analysis:
        print(f"Error Type: {report.error_analysis.error_type}")
        print(f"Message:    {report.error_analysis.error_message}")
        if report.error_analysis.key_indicators:
            print(f"Indicators: {'; '.join(report.error_analysis.key_indicators)}")
        print()

    if report.reproduction_status:
        reproducible = "YES" if report.reproduction_status.is_reproducible else "NO"
        print(f"Reproducible: {reproducible} ({report.reproduction_status.frequency})")
        if report.reproduction_status.reproduction_steps:
            print("Steps:")
            for step in report.reproduction_status.reproduction_steps:
                print(f"  - {step}")
        print()

    if report.root_cause_evidence:
        print(f"Root Cause Origin: {report.root_cause_evidence.origin_location}")
        print(f"Root Source:       {report.root_cause_evidence.root_source}")
        print(f"Fix Recommendation: {report.root_cause_evidence.fix_recommendation}")
        print()

    if report.hypothesis:
        print(f"Hypothesis [{report.hypothesis.confidence_level} confidence]:")
        print(f"  {report.hypothesis.root_cause_statement}")
        print(f"  Test: {report.hypothesis.test_approach}")
        print()

    if report.fix_plan:
        print("Fix Plan:")
        print(f"  Test first: {report.fix_plan.failing_test_description}")
        print(f"  Fix:        {report.fix_plan.fix_description}")
        if report.fix_plan.files_to_change:
            print(f"  Files:      {', '.join(report.fix_plan.files_to_change)}")
        print()

    if report.architectural_issue_detected:
        print("⚠  ARCHITECTURAL ISSUE DETECTED")
        print("   3+ fix attempts have each revealed new problems in different places.")
        print("   STOP. Discuss architecture with your team before attempting more fixes.\n")

    if report.next_steps:
        print("Next Steps:")
        for i, step in enumerate(report.next_steps, 1):
            print(f"  {i}. {step}")
    print()


if __name__ == "__main__":
    main()
