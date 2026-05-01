"""Integration tests for compile() function with backend abstraction.

These tests verify that the compile() function correctly:
- Validates and uses the backend parameter
- Calls backend.validate_environment() before compilation
- Passes correct CompilationContext to backend.compile()
- Handles backend compilation results appropriately
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mellea_skills_compiler.compile.backend import CompilationResult, CompilationContext
from mellea_skills_compiler.compile.mellea_skills import compile


@pytest.fixture
def mock_spec_file(tmp_path):
    """Create a minimal valid skill spec file."""
    spec_path = tmp_path / "test_skill" / "spec.md"
    spec_path.parent.mkdir(parents=True)
    spec_path.write_text(
        """---
name: test-skill
---

# Test Skill

A test skill for integration testing.
"""
    )
    return spec_path


@pytest.fixture
def successful_backend_mock():
    """Create a mock backend that succeeds."""
    mock_backend = MagicMock()
    mock_backend.validate_environment.return_value = (True, None)
    mock_backend.get_backend_name.return_value = "Claude Code"
    mock_backend.supports_repair_mode.return_value = True
    
    def mock_compile(context):
        # Simulate successful compilation
        return CompilationResult(
            success=True,
            package_dir=context.package_dir,
            error_message=None,
            intermediate_artifacts={},
            metadata={"backend": "claude"},
        )
    
    mock_backend.compile.side_effect = mock_compile
    return mock_backend


@pytest.fixture
def failing_backend_mock():
    """Create a mock backend that fails validation."""
    mock_backend = MagicMock()
    mock_backend.validate_environment.return_value = (False, "Claude CLI not found")
    mock_backend.get_backend_name.return_value = "Claude Code"
    return mock_backend


class TestCompileWithBackendParameter:
    """Test that compile() function uses backend parameter correctly."""

    @patch("mellea_skills_compiler.compile.mellea_skills.subprocess.call")
    @patch("mellea_skills_compiler.compile.mellea_skills.validate")
    @patch("mellea_skills_compiler.compile.mellea_skills.write_mellea_doc_index")
    @patch("mellea_skills_compiler.compile.mellea_skills.write_mellea_api_ref")
    @patch("mellea_skills_compiler.compile.mellea_skills.get_backend")
    def test_backend_parameter_is_used(
        self,
        mock_get_backend,
        mock_api_ref,
        mock_doc_index,
        mock_validate,
        mock_subprocess,
        mock_spec_file,
        successful_backend_mock,
        tmp_path,
    ):
        """Test that the backend parameter is passed to get_backend()."""
        mock_get_backend.return_value = successful_backend_mock
        mock_api_ref.return_value = tmp_path / "mellea_api_ref.json"
        mock_doc_index.return_value = tmp_path / "mellea_doc_index.json"
        
        compile(
            spec_path=mock_spec_file,
            model="claude-3-5-sonnet-20241022",
            timeout=300,
            backend="claude",
        )
        
        # Verify get_backend was called with correct backend name
        mock_get_backend.assert_called_once_with("claude")

    @patch("mellea_skills_compiler.compile.mellea_skills.subprocess.call")
    @patch("mellea_skills_compiler.compile.mellea_skills.validate")
    @patch("mellea_skills_compiler.compile.mellea_skills.write_mellea_doc_index")
    @patch("mellea_skills_compiler.compile.mellea_skills.write_mellea_api_ref")
    @patch("mellea_skills_compiler.compile.mellea_skills.get_backend")
    def test_backend_validation_is_called(
        self,
        mock_get_backend,
        mock_api_ref,
        mock_doc_index,
        mock_validate,
        mock_subprocess,
        mock_spec_file,
        successful_backend_mock,
        tmp_path,
    ):
        """Test that backend.validate_environment() is called before compilation."""
        mock_get_backend.return_value = successful_backend_mock
        mock_api_ref.return_value = tmp_path / "mellea_api_ref.json"
        mock_doc_index.return_value = tmp_path / "mellea_doc_index.json"
        
        compile(
            spec_path=mock_spec_file,
            model="claude-3-5-sonnet-20241022",
            timeout=300,
            backend="claude",
        )
        
        # Verify validate_environment was called
        successful_backend_mock.validate_environment.assert_called_once()

    @patch("mellea_skills_compiler.compile.mellea_skills.subprocess.call")
    @patch("mellea_skills_compiler.compile.mellea_skills.write_mellea_doc_index")
    @patch("mellea_skills_compiler.compile.mellea_skills.write_mellea_api_ref")
    @patch("mellea_skills_compiler.compile.mellea_skills.get_backend")
    def test_backend_validation_failure_raises_error(
        self,
        mock_get_backend,
        mock_api_ref,
        mock_doc_index,
        mock_subprocess,
        mock_spec_file,
        failing_backend_mock,
        tmp_path,
    ):
        """Test that compilation fails when backend validation fails."""
        mock_get_backend.return_value = failing_backend_mock
        mock_api_ref.return_value = tmp_path / "mellea_api_ref.json"
        mock_doc_index.return_value = tmp_path / "mellea_doc_index.json"
        
        with pytest.raises(RuntimeError, match="Backend 'claude' not available"):
            compile(
                spec_path=mock_spec_file,
                model="claude-3-5-sonnet-20241022",
                timeout=300,
                backend="claude",
            )

    @patch("mellea_skills_compiler.compile.mellea_skills.subprocess.call")
    @patch("mellea_skills_compiler.compile.mellea_skills.validate")
    @patch("mellea_skills_compiler.compile.mellea_skills.write_mellea_doc_index")
    @patch("mellea_skills_compiler.compile.mellea_skills.write_mellea_api_ref")
    @patch("mellea_skills_compiler.compile.mellea_skills.get_backend")
    def test_backend_compile_is_called_with_context(
        self,
        mock_get_backend,
        mock_api_ref,
        mock_doc_index,
        mock_validate,
        mock_subprocess,
        mock_spec_file,
        successful_backend_mock,
        tmp_path,
    ):
        """Test that backend.compile() is called with correct CompilationContext."""
        mock_get_backend.return_value = successful_backend_mock
        mock_api_ref.return_value = tmp_path / "mellea_api_ref.json"
        mock_doc_index.return_value = tmp_path / "mellea_doc_index.json"
        
        compile(
            spec_path=mock_spec_file,
            model="claude-3-5-sonnet-20241022",
            timeout=300,
            backend="claude",
            repair_mode=False,
            skill_backend="ollama",
            skill_model="granite3.3:8b",
            refresh_cache=False,
        )
        
        # Verify compile was called
        successful_backend_mock.compile.assert_called_once()
        
        # Verify the context passed to compile
        call_args = successful_backend_mock.compile.call_args[0][0]
        assert isinstance(call_args, CompilationContext)
        assert call_args.spec_path == mock_spec_file
        assert call_args.model == "claude-3-5-sonnet-20241022"
        assert call_args.timeout == 300
        assert call_args.repair_mode is False
        assert call_args.skill_backend == "ollama"
        assert call_args.skill_model == "granite3.3:8b"
        assert call_args.refresh_cache is False

    @patch("mellea_skills_compiler.compile.mellea_skills.subprocess.call")
    @patch("mellea_skills_compiler.compile.mellea_skills.validate")
    @patch("mellea_skills_compiler.compile.mellea_skills.write_mellea_doc_index")
    @patch("mellea_skills_compiler.compile.mellea_skills.write_mellea_api_ref")
    @patch("mellea_skills_compiler.compile.mellea_skills.get_backend")
    def test_backend_compilation_failure_raises_error(
        self,
        mock_get_backend,
        mock_api_ref,
        mock_doc_index,
        mock_validate,
        mock_subprocess,
        mock_spec_file,
        tmp_path,
    ):
        """Test that compilation fails when backend returns failure result."""
        mock_backend = MagicMock()
        mock_backend.validate_environment.return_value = (True, None)
        mock_backend.compile.return_value = CompilationResult(
            success=False,
            package_dir=mock_spec_file.parent / "test_skill_mellea",
            error_message="Compilation timeout",
            intermediate_artifacts={},
            metadata={},
        )
        mock_get_backend.return_value = mock_backend
        mock_api_ref.return_value = tmp_path / "mellea_api_ref.json"
        mock_doc_index.return_value = tmp_path / "mellea_doc_index.json"
        
        with pytest.raises(RuntimeError, match="Compilation failed: Compilation timeout"):
            compile(
                spec_path=mock_spec_file,
                model="claude-3-5-sonnet-20241022",
                timeout=300,
                backend="claude",
            )

    @patch("mellea_skills_compiler.compile.mellea_skills.subprocess.call")
    @patch("mellea_skills_compiler.compile.mellea_skills.validate")
    @patch("mellea_skills_compiler.compile.mellea_skills.write_mellea_doc_index")
    @patch("mellea_skills_compiler.compile.mellea_skills.write_mellea_api_ref")
    @patch("mellea_skills_compiler.compile.mellea_skills.get_backend")
    def test_validation_runs_after_successful_compilation(
        self,
        mock_get_backend,
        mock_api_ref,
        mock_doc_index,
        mock_validate,
        mock_subprocess,
        mock_spec_file,
        successful_backend_mock,
        tmp_path,
    ):
        """Test that validate() is called after successful backend compilation."""
        mock_get_backend.return_value = successful_backend_mock
        mock_api_ref.return_value = tmp_path / "mellea_api_ref.json"
        mock_doc_index.return_value = tmp_path / "mellea_doc_index.json"
        
        compile(
            spec_path=mock_spec_file,
            model="claude-3-5-sonnet-20241022",
            timeout=300,
            backend="claude",
        )
        
        # Verify validate was called
        mock_validate.assert_called_once()
        
        # Verify it was called with the package directory
        call_args = mock_validate.call_args
        package_dir_arg = call_args[0][0]
        assert package_dir_arg == mock_spec_file.parent / "test_skill_mellea"


class TestCompileInvalidBackend:
    """Test error handling for invalid backend parameter."""

    def test_invalid_backend_raises_value_error(self, mock_spec_file):
        """Test that invalid backend name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown backend 'invalid'"):
            compile(
                spec_path=mock_spec_file,
                model="claude-3-5-sonnet-20241022",
                timeout=300,
                backend="invalid",
            )