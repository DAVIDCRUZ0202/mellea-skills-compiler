"""Type checking tests using pyright.

This test ensures that the codebase passes static type checking without
requiring additional dependencies beyond what's already installed.
"""

import subprocess
import sys
from pathlib import Path


def test_type_checking_with_pyright():
    """Ensure codebase passes static type checking with pyright.
    
    This test runs pyright (basedpyright) on the source code to catch
    type annotation issues that could lead to runtime errors.
    """
    # Get the project root directory
    project_root = Path(__file__).parent.parent.parent
    src_dir = project_root / "src" / "mellea_skills_compiler"
    
    # Try both pyright and basedpyright (different installations)
    pyright_cmd = None
    for cmd in ["basedpyright", "pyright"]:
        try:
            result = subprocess.run(
                [cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                pyright_cmd = cmd
                break
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    
    if pyright_cmd is None:
        # Neither pyright nor basedpyright available, skip test
        import pytest
        pytest.skip("pyright/basedpyright not available in environment")
    
    # Type checker satisfaction: pyright_cmd is definitely str here
    assert pyright_cmd is not None
    
    # Run pyright on the source directory
    result = subprocess.run(
        [pyright_cmd, str(src_dir)],
        capture_output=True,
        text=True,
        timeout=30
    )

    # Check for actual errors (not just warnings)
    # Pyright output format: "X errors, Y warnings, Z notes"
    if "error" in result.stdout.lower():
        # Extract error count from output
        import re
        error_match = re.search(r'(\d+)\s+error', result.stdout)
        if error_match and int(error_match.group(1)) > 0:
            error_msg = f"Type checking found {error_match.group(1)} errors:\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
            # Print to help with debugging
            print(error_msg, file=sys.stderr)
            assert False, error_msg
    
    # Success - no type errors
    assert result.returncode == 0, "Type checking should pass without errors"


def test_type_checking_cli_module():
    """Specifically test the CLI module for type correctness.
    
    The CLI module has had issues with type annotations in the past,
    so we test it separately to ensure it's always correct.
    """
    project_root = Path(__file__).parent.parent.parent
    cli_file = project_root / "src" / "mellea_skills_compiler" / "cli.py"
    
    # Try both pyright and basedpyright (different installations)
    pyright_cmd = None
    for cmd in ["basedpyright", "pyright"]:
        try:
            result = subprocess.run(
                [cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                pyright_cmd = cmd
                break
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    
    if pyright_cmd is None:
        import pytest
        pytest.skip("pyright/basedpyright not available in environment")
    
    # Type checker satisfaction: pyright_cmd is definitely str here
    assert pyright_cmd is not None
    
    # Run pyright specifically on cli.py
    result = subprocess.run(
        [pyright_cmd, str(cli_file)],
        capture_output=True,
        text=True,
        timeout=30
    )

    # Check for actual errors (not just warnings)
    # Pyright output format: "X errors, Y warnings, Z notes"
    if "error" in result.stdout.lower():
        # Extract error count from output
        import re
        error_match = re.search(r'(\d+)\s+error', result.stdout)
        if error_match and int(error_match.group(1)) > 0:
            error_msg = f"CLI module has {error_match.group(1)} type errors:\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
            print(error_msg, file=sys.stderr)
            assert False, error_msg

# Made with Bob
