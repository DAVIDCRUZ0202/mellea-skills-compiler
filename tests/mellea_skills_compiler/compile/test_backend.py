"""Unit tests for mellea_skills_compiler.compile.backend module.

Tests the backend protocol, registry, and global convenience functions.
"""

from pathlib import Path
from typing import Optional

import pytest

from mellea_skills_compiler.compile.backend import (
    BackendRegistry,
    CompilationBackend,
    CompilationContext,
    CompilationResult,
    get_backend,
    list_backends,
    register_backend,
)


class MockBackend:
    """Mock backend implementation for testing."""
    
    def __init__(self, name: str = "Mock Backend", supports_repair: bool = True):
        self._name = name
        self._supports_repair = supports_repair
    
    def compile(self, context: CompilationContext) -> CompilationResult:
        """Mock compile implementation."""
        return CompilationResult(
            success=True,
            package_dir=context.package_dir,
            metadata={"backend": self._name},
        )
    
    def validate_environment(self) -> tuple[bool, Optional[str]]:
        """Mock validation - always succeeds."""
        return True, None
    
    def get_backend_name(self) -> str:
        """Return mock backend name."""
        return self._name
    
    def supports_repair_mode(self) -> bool:
        """Return repair mode support."""
        return self._supports_repair


class FailingMockBackend:
    """Mock backend that fails validation."""
    
    def compile(self, context: CompilationContext) -> CompilationResult:
        """Mock compile implementation."""
        return CompilationResult(
            success=False,
            package_dir=context.package_dir,
            error_message="Mock backend failure",
        )
    
    def validate_environment(self) -> tuple[bool, Optional[str]]:
        """Mock validation - always fails."""
        return False, "Mock backend not available: missing prerequisites"
    
    def get_backend_name(self) -> str:
        """Return mock backend name."""
        return "Failing Mock Backend"
    
    def supports_repair_mode(self) -> bool:
        """Return repair mode support."""
        return False


@pytest.fixture
def registry():
    """Create a fresh BackendRegistry for each test."""
    return BackendRegistry()


@pytest.fixture
def mock_context(tmp_path):
    """Create a mock CompilationContext for testing."""
    return CompilationContext(
        spec_path=tmp_path / "spec.md",
        package_dir=tmp_path / "output",
        intermediate_dir=tmp_path / "output" / "intermediate",
    )


class TestBackendRegistry:
    """Test cases for BackendRegistry class."""
    
    def test_register_backend_success(self, registry):
        """Test successful backend registration."""
        registry.register_backend("mock", MockBackend)
        
        # Should be able to retrieve the backend
        backend = registry.get_backend("mock")
        assert isinstance(backend, MockBackend)
        assert backend.get_backend_name() == "Mock Backend"
    
    def test_register_backend_duplicate_raises_error(self, registry):
        """Test that registering duplicate backend name raises ValueError."""
        registry.register_backend("mock", MockBackend)
        
        with pytest.raises(ValueError, match="Backend 'mock' is already registered"):
            registry.register_backend("mock", MockBackend)
    
    def test_get_backend_unknown_raises_error(self, registry):
        """Test that getting unknown backend raises KeyError with helpful message."""
        with pytest.raises(KeyError, match="Unknown backend 'nonexistent'"):
            registry.get_backend("nonexistent")
        
        # Error message should list available backends
        with pytest.raises(KeyError, match="Available backends:"):
            registry.get_backend("nonexistent")
    
    def test_get_backend_returns_new_instance(self, registry):
        """Test that get_backend returns a new instance each time."""
        registry.register_backend("mock", MockBackend)
        
        backend1 = registry.get_backend("mock")
        backend2 = registry.get_backend("mock")
        
        # Should be different instances
        assert backend1 is not backend2
        # But same type
        assert type(backend1) == type(backend2)
    
    def test_list_backends_empty(self, registry):
        """Test that list_backends returns empty list for empty registry."""
        assert registry.list_backends() == []
    
    def test_list_backends_single(self, registry):
        """Test that list_backends returns single backend."""
        registry.register_backend("mock", MockBackend)
        assert registry.list_backends() == ["mock"]
    
    def test_list_backends_multiple_sorted(self, registry):
        """Test that list_backends returns sorted list of backends."""
        registry.register_backend("zebra", MockBackend)
        registry.register_backend("alpha", MockBackend)
        registry.register_backend("beta", MockBackend)
        
        backends = registry.list_backends()
        assert backends == ["alpha", "beta", "zebra"]
    
    def test_registry_isolation(self):
        """Test that different registry instances are isolated."""
        registry1 = BackendRegistry()
        registry2 = BackendRegistry()
        
        registry1.register_backend("mock1", MockBackend)
        registry2.register_backend("mock2", MockBackend)
        
        assert registry1.list_backends() == ["mock1"]
        assert registry2.list_backends() == ["mock2"]


class TestGlobalRegistryFunctions:
    """Test cases for global registry convenience functions."""
    
    def test_register_backend_global(self):
        """Test that register_backend uses global registry."""
        # Note: This test affects global state, so we need to be careful
        # In a real scenario, we'd want to reset the global registry after tests
        
        # Register a backend with unique name to avoid conflicts
        test_backend_name = "test_global_mock_backend"
        register_backend(test_backend_name, MockBackend)
        
        # Should be able to retrieve it
        backend = get_backend(test_backend_name)
        assert isinstance(backend, MockBackend)
        
        # Should appear in list
        assert test_backend_name in list_backends()
    
    def test_get_backend_global(self):
        """Test that get_backend uses global registry."""
        test_backend_name = "test_global_get_backend"
        register_backend(test_backend_name, MockBackend)
        
        backend = get_backend(test_backend_name)
        assert backend.get_backend_name() == "Mock Backend"
    
    def test_list_backends_global(self):
        """Test that list_backends uses global registry."""
        # Register multiple backends
        register_backend("test_global_list_1", MockBackend)
        register_backend("test_global_list_2", MockBackend)
        
        backends = list_backends()
        assert "test_global_list_1" in backends
        assert "test_global_list_2" in backends
        # Should be sorted
        assert backends == sorted(backends)


class TestCompilationContext:
    """Test cases for CompilationContext dataclass."""
    
    def test_required_fields(self, tmp_path):
        """Test that CompilationContext requires spec_path, package_dir, intermediate_dir."""
        context = CompilationContext(
            spec_path=tmp_path / "spec.md",
            package_dir=tmp_path / "output",
            intermediate_dir=tmp_path / "output" / "intermediate",
        )
        
        assert context.spec_path == tmp_path / "spec.md"
        assert context.package_dir == tmp_path / "output"
        assert context.intermediate_dir == tmp_path / "output" / "intermediate"
    
    def test_optional_fields_defaults(self, tmp_path):
        """Test that optional fields have correct defaults."""
        context = CompilationContext(
            spec_path=tmp_path / "spec.md",
            package_dir=tmp_path / "output",
            intermediate_dir=tmp_path / "output" / "intermediate",
        )
        
        assert context.model is None
        assert context.timeout == 0
        assert context.repair_mode is False
        assert context.skill_backend is None
        assert context.skill_model is None
        assert context.refresh_cache is False
    
    def test_optional_fields_can_be_set(self, tmp_path):
        """Test that optional fields can be set."""
        context = CompilationContext(
            spec_path=tmp_path / "spec.md",
            package_dir=tmp_path / "output",
            intermediate_dir=tmp_path / "output" / "intermediate",
            model="claude-3-7-sonnet-20250219",
            timeout=300,
            repair_mode=True,
            skill_backend="claude",
            skill_model="claude-3-5-sonnet-20241022",
            refresh_cache=True,
        )
        
        assert context.model == "claude-3-7-sonnet-20250219"
        assert context.timeout == 300
        assert context.repair_mode is True
        assert context.skill_backend == "claude"
        assert context.skill_model == "claude-3-5-sonnet-20241022"
        assert context.refresh_cache is True


class TestCompilationResult:
    """Test cases for CompilationResult dataclass."""
    
    def test_success_result(self, tmp_path):
        """Test successful compilation result."""
        result = CompilationResult(
            success=True,
            package_dir=tmp_path / "output",
        )
        
        assert result.success is True
        assert result.package_dir == tmp_path / "output"
        assert result.error_message is None
        assert result.intermediate_artifacts == {}
        assert result.metadata == {}
    
    def test_failure_result(self, tmp_path):
        """Test failed compilation result."""
        result = CompilationResult(
            success=False,
            package_dir=tmp_path / "output",
            error_message="Compilation failed: syntax error",
        )
        
        assert result.success is False
        assert result.error_message == "Compilation failed: syntax error"
    
    def test_with_artifacts_and_metadata(self, tmp_path):
        """Test result with intermediate artifacts and metadata."""
        result = CompilationResult(
            success=True,
            package_dir=tmp_path / "output",
            intermediate_artifacts={
                "inventory": tmp_path / "output" / "intermediate" / "inventory.json",
                "classification": tmp_path / "output" / "intermediate" / "classification.json",
            },
            metadata={
                "model": "claude-3-7-sonnet-20250219",
                "duration_seconds": 45.2,
                "tokens_used": 12500,
            },
        )
        
        assert result.success is True
        assert len(result.intermediate_artifacts) == 2
        assert "inventory" in result.intermediate_artifacts
        assert "classification" in result.intermediate_artifacts
        assert result.metadata["model"] == "claude-3-7-sonnet-20250219"
        assert result.metadata["duration_seconds"] == 45.2


class TestMockBackendProtocolCompliance:
    """Test that mock backends conform to CompilationBackend protocol."""
    
    def test_mock_backend_implements_protocol(self, mock_context):
        """Test that MockBackend implements all protocol methods."""
        backend = MockBackend()
        
        # Test compile method
        result = backend.compile(mock_context)
        assert isinstance(result, CompilationResult)
        assert result.success is True
        
        # Test validate_environment method
        is_valid, error = backend.validate_environment()
        assert isinstance(is_valid, bool)
        assert is_valid is True
        assert error is None
        
        # Test get_backend_name method
        name = backend.get_backend_name()
        assert isinstance(name, str)
        assert name == "Mock Backend"
        
        # Test supports_repair_mode method
        supports_repair = backend.supports_repair_mode()
        assert isinstance(supports_repair, bool)
        assert supports_repair is True
    
    def test_failing_mock_backend_implements_protocol(self, mock_context):
        """Test that FailingMockBackend implements all protocol methods."""
        backend = FailingMockBackend()
        
        # Test compile method
        result = backend.compile(mock_context)
        assert isinstance(result, CompilationResult)
        assert result.success is False
        assert result.error_message is not None
        
        # Test validate_environment method
        is_valid, error = backend.validate_environment()
        assert isinstance(is_valid, bool)
        assert is_valid is False
        assert isinstance(error, str)
        assert "Mock backend not available" in error
        
        # Test get_backend_name method
        name = backend.get_backend_name()
        assert isinstance(name, str)
        
        # Test supports_repair_mode method
        supports_repair = backend.supports_repair_mode()
        assert isinstance(supports_repair, bool)
        assert supports_repair is False
    
    def test_backend_can_be_used_through_registry(self, registry, mock_context):
        """Test that backends work correctly when retrieved from registry."""
        registry.register_backend("mock", MockBackend)
        
        backend = registry.get_backend("mock")
        result = backend.compile(mock_context)
        
        assert result.success is True
        assert result.metadata["backend"] == "Mock Backend"
