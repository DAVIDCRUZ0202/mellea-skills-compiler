# GraniteClaw Tests

This directory contains unit tests for the GraniteClaw package.

## Dependencies

Tests require:
- `pytest>=7.0` - Testing framework
- `pytest-cov` (optional) - Coverage reporting

Or install tests dependencies:
```bash
pip install -e ".[tests]"
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run tests with coverage
```bash
pytest --cov=graniteclaw --cov-report=html
```

### Run specific test file
```bash
pytest tests/test_enums.py
```

### Run specific test class or function
```bash
pytest tests/test_compliance.py::TestComplianceSummary
pytest tests/test_file_utils.py::TestParseSkillMd::test_parse_with_valid_frontmatter
```

### Run with verbose output
```bash
pytest -v
```

### Run with output capture disabled (see print statements)
```bash
pytest -s
```

## Test Structure

- `tests/graniteclaw/toolkit/test_enums.py` - Tests for enum definitions
- `tests/graniteclaw/toolkit/test_file_utils.py` - Tests for file parsing utilities
- `tests/graniteclaw/certification/test_ingest.py` - Tests for risk only ingestion pipeline
- `tests/graniteclaw/certification/test_nexus_policy.py` - Tests for policy manifest and Nexus integration
- `tests/graniteclaw/certification/test_compliance.py` - Tests for compliance classification and reporting
- `tests/graniteclaw/test_skill_utility.py` - Tests for skill loading and validation
- `tests/graniteclaw/guardian/test_audit_trail.py` - Tests for audit trail plugin
