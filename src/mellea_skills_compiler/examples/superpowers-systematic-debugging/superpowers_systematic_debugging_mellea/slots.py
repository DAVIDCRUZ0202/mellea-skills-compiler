from typing import Literal

from mellea import generative


@generative
def extract_error_analysis_raw(error_text: str) -> str:
    """Set `result` to a structured summary of the error information extracted from the provided error text.
    Format your result as five pipe-separated sections:
    ERROR_TYPE|PRIMARY_MESSAGE|KEY_TRACE_FRAMES|LINE_NUMBERS|ROOT_CAUSE_INDICATORS
    Within each section, separate multiple items with semicolons.
    Focus on application code frames in the trace, not library internals.
    Example: TypeError|object has no attribute 'foo'|app/main.py line 42;app/utils.py line 17|42;17|attribute access on None;missing initialization"""
    ...


@generative
def extract_recent_changes_raw(issue_description: str, changes_text: str) -> str:
    """Set `result` to a summary of recent changes that could be related to the described issue.
    Format your result as three pipe-separated sections:
    CHANGE_SUMMARY|POTENTIALLY_RELATED_CHANGES|ENVIRONMENT_DIFFERENCES
    Within each section, separate multiple items with semicolons.
    CHANGE_SUMMARY: brief description of the overall recent change context.
    POTENTIALLY_RELATED_CHANGES: specific changes that could plausibly cause the described issue.
    ENVIRONMENT_DIFFERENCES: any environment, config, or dependency changes noted.
    If no changes are provided or inferable, use: UNKNOWN|UNKNOWN|UNKNOWN"""
    ...


@generative
def extract_data_flow_trace_raw(error_text: str, code_source_text: str) -> str:
    """Set `result` to a backward call-chain trace from the error symptom to its origin.
    Format your result as five pipe-separated sections:
    ORIGIN_LOCATION|TRACE_STEPS|BAD_VALUE_DESCRIPTION|ROOT_SOURCE|FIX_HINT
    Within TRACE_STEPS, separate each step with semicolons (start at the error, trace backward to origin).
    ORIGIN_LOCATION: where in the code the bad value or behavior first appears.
    TRACE_STEPS: the backward call chain, each step describing one frame or transition.
    BAD_VALUE_DESCRIPTION: what value or state is incorrect and how it propagates.
    ROOT_SOURCE: the specific location where the bug must actually be fixed.
    FIX_HINT: high-level direction for addressing the root source.
    If insufficient context to trace: UNKNOWN|UNKNOWN|UNKNOWN|UNKNOWN|UNKNOWN"""
    ...


@generative
def classify_failure_pattern(investigation_summary: str, fix_count: int) -> Literal["architectural_problem", "investigation_incomplete"]:
    """Set `result` to the failure pattern classification based on the investigation summary and fix count.
    Use 'architectural_problem' when ALL of these indicators are present:
    - Multiple fix attempts (fix_count >= 3) have each revealed new problems in different places
    - Fixes require extensive refactoring to implement correctly
    - Each fix attempt creates new symptoms elsewhere in the system
    Use 'investigation_incomplete' when:
    - The root cause has not been fully identified despite attempts
    - More investigation into a specific component or assumption is needed
    - The fix failures do not exhibit the spreading/coupling pattern above"""
    ...
