from __future__ import annotations

from mellea import generative


@generative
def extract_modified_files(diff: str) -> str:
    """Set `result` to a comma-separated list of file paths modified in the diff.
    Include only files that appear in the diff headers (lines starting with 'diff --git').
    If no files are found, set `result` to an empty string."""
    ...


@generative
def extract_attack_surface_raw(diff: str, file_list: str) -> str:
    """Set `result` to a JSON object mapping each file path from file_list to an object with keys:
    user_inputs, db_queries, auth_checks, session_ops, external_calls, crypto_ops.
    Each key maps to a list of strings describing the relevant operations found in the diff for that file.
    Use empty lists for categories with no operations. Only include files present in file_list."""
    ...
