from typing import Optional

from pydantic import BaseModel, Field


class ErrorAnalysis(BaseModel):
    error_type: str = Field(description="Category of the error (e.g., TypeError, RuntimeError, ImportError, AttributeError)")
    error_message: str = Field(description="The primary error message text")
    stack_trace_summary: str = Field(description="Key frames from the stack trace focusing on application code, not library internals")
    line_numbers: list[str] = Field(default_factory=list, description="Relevant line numbers and file paths from the error trace")
    key_indicators: list[str] = Field(default_factory=list, description="Specific patterns or signals in the error that point toward the root cause")


class ReproductionResult(BaseModel):
    is_reproducible: bool = Field(description="Whether the issue can be triggered consistently")
    reproduction_steps: list[str] = Field(default_factory=list, description="Exact steps to reproduce the issue in order")
    frequency: str = Field(description="Reproduction frequency: every_time, intermittent, or cannot_reproduce")
    blocking_factor: Optional[str] = Field(default=None, description="If the issue cannot be reproduced, extract the factor preventing reproduction from the description; otherwise null. Do not ask for it.")


class RootCauseEvidence(BaseModel):
    origin_location: str = Field(description="Where the bad value or incorrect behavior originates in the code (file and line if known)")
    trace_steps: list[str] = Field(default_factory=list, description="Backward call-chain steps tracing from the error symptom back to the origin, one step per list item")
    bad_value_description: str = Field(description="Description of the incorrect value or state that is being propagated through the system")
    root_source: str = Field(description="The actual source of the defect — the specific location where the fix must be applied")
    fix_recommendation: str = Field(description="High-level recommendation for fixing the issue at the root source rather than at the symptom")


class PatternAnalysis(BaseModel):
    working_examples: list[str] = Field(default_factory=list, description="Similar working code patterns or implementations found that contrast with the broken code")
    key_differences: list[str] = Field(default_factory=list, description="Every difference between the working and broken implementation, however small — do not omit any")
    missing_dependencies: list[str] = Field(default_factory=list, description="Dependencies, configuration values, or environment requirements that are missing or incorrect")
    pattern_summary: str = Field(description="Summary of what the pattern comparison reveals about the likely root cause")


class Hypothesis(BaseModel):
    root_cause_statement: str = Field(description="Specific, written-down hypothesis: 'I think X is the root cause because Y'")
    evidence_basis: str = Field(description="Evidence from Phases 1 and 2 that directly supports this specific hypothesis")
    test_approach: str = Field(description="The single minimal change that would confirm or definitively refute this hypothesis")
    confidence_level: str = Field(description="Confidence in this hypothesis based on available evidence: high, medium, or low")


class HypothesisTestResult(BaseModel):
    hypothesis_confirmed: bool = Field(description="Whether the hypothesis was confirmed by the test result")
    test_performed: str = Field(description="The minimal change that was made or should be made to test the hypothesis")
    result_observed: str = Field(description="What actually happened after applying the test change, or what is predicted to happen")
    new_information: Optional[str] = Field(default=None, description="If hypothesis was not confirmed, extract the new information learned from the test; null if confirmed. Do not ask for it.")


class FixPlan(BaseModel):
    failing_test_description: str = Field(description="The simplest possible failing test to create first — it must prove the bug exists before any fix is attempted")
    fix_description: str = Field(description="The single change addressing the identified root cause — not the symptom. ONE change at a time.")
    files_to_change: list[str] = Field(default_factory=list, description="Specific files that need to be modified by the fix")
    verification_steps: list[str] = Field(default_factory=list, description="Ordered steps to verify the fix worked without breaking other tests")
    is_architectural_issue: bool = Field(default=False, description="Whether 3 or more failed fix attempts indicate a deeper architectural problem that requires team discussion")


class DebuggingReport(BaseModel):
    phase1_complete: bool = Field(description="Whether Phase 1 Root Cause Investigation was completed with sufficient evidence")
    error_analysis: Optional[ErrorAnalysis] = Field(default=None, description="Phase 1 error message analysis; if no error text was provided extract what is available from the issue description")
    reproduction_status: Optional[ReproductionResult] = Field(default=None, description="Phase 1 reproducibility assessment based on the provided information")
    root_cause_evidence: Optional[RootCauseEvidence] = Field(default=None, description="Phase 1 data flow trace and root cause evidence; null if investigation could not determine origin")
    pattern_analysis: Optional[PatternAnalysis] = Field(default=None, description="Phase 2 pattern comparison results; null if no working examples or code context provided")
    hypothesis: Optional[Hypothesis] = Field(default=None, description="Phase 3 hypothesis formed from accumulated evidence")
    hypothesis_test: Optional[HypothesisTestResult] = Field(default=None, description="Phase 3 hypothesis test result or assessment")
    fix_plan: Optional[FixPlan] = Field(default=None, description="Phase 4 fix plan addressing the root cause; null if architectural issue requires discussion first")
    summary: str = Field(description="High-level summary of the investigation findings and the recommended path forward")
    next_steps: list[str] = Field(default_factory=list, description="Concrete ordered actions to resolve the issue")
    fix_attempts_count: int = Field(default=0, description="Number of fix attempts already made in this debugging session")
    architectural_issue_detected: bool = Field(default=False, description="Whether the investigation indicates an architectural problem that requires broader team discussion")
