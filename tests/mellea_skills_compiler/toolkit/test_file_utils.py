"""Unit tests for mellea_skills_compiler.toolkit.file_utils module."""

import tempfile
from pathlib import Path

import pytest

from mellea_skills_compiler.toolkit.file_utils import parse_spec_file


class TestParseSkillMd:
    """Test cases for parse_spec_file function."""

    def test_parse_with_valid_frontmatter(self):
        """Test parsing a SKILL.md with valid YAML frontmatter."""
        content = """---
name: test-skill
description: A test skill
allowed-tools: Bash, Read, Write
---

This is the body of the skill."""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            path = Path(f.name)

        try:
            result = parse_spec_file(path)

            assert result["frontmatter"]["name"] == "test-skill"
            assert result["frontmatter"]["description"] == "A test skill"
            assert result["frontmatter"]["allowed-tools"] == ["Bash", "Read", "Write"]
            assert result["body"] == "This is the body of the skill."
            assert str(path) in result["path"]
        finally:
            path.unlink()

    def test_parse_without_frontmatter(self):
        """Test parsing a file without frontmatter."""
        content = "This is just markdown content without frontmatter."

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            path = Path(f.name)

        try:
            result = parse_spec_file(path)

            assert result["frontmatter"] == {}
            assert result["body"] == content
            assert str(path) in result["path"]
        finally:
            path.unlink()

    def test_parse_allowed_tools_as_comma_separated_string(self):
        """Test parsing allowed-tools as comma-separated string."""
        content = """---
allowed-tools: "Bash, Read, Write, Glob"
---

Body content."""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            path = Path(f.name)

        try:
            result = parse_spec_file(path)
            assert result["frontmatter"]["allowed-tools"] == [
                "Bash",
                "Read",
                "Write",
                "Glob",
            ]
        finally:
            path.unlink()

    def test_parse_allowed_tools_as_space_separated_string(self):
        """Test parsing allowed-tools as space-separated string without commas."""
        content = """---
allowed-tools: Bash Read Write
---

Body content."""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            path = Path(f.name)

        try:
            result = parse_spec_file(path)
            assert result["frontmatter"]["allowed-tools"] == ["Bash", "Read", "Write"]
        finally:
            path.unlink()

    def test_parse_allowed_tools_as_list(self):
        """Test parsing allowed-tools as YAML list."""
        content = """---
allowed-tools:
  - Bash
  - Read
  - Write
---

Body content."""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            path = Path(f.name)

        try:
            result = parse_spec_file(path)
            assert result["frontmatter"]["allowed-tools"] == ["Bash", "Read", "Write"]
        finally:
            path.unlink()

    def test_parse_openclaw_requires_bins(self):
        """Test that openclaw.requires.bins are added to allowed-tools."""
        content = """---
allowed-tools:
  - Bash
metadata:
  openclaw:
    requires:
      bins:
        - git
        - docker
      anyBins:
        - kubectl
---

Body content."""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            path = Path(f.name)

        try:
            result = parse_spec_file(path)
            tools = result["frontmatter"]["allowed-tools"]
            assert "Bash" in tools
            assert "git" in tools
            assert "docker" in tools
            assert "kubectl" in tools
        finally:
            path.unlink()

    def test_parse_openclaw_no_duplicates(self):
        """Test that openclaw tools don't create duplicates."""
        content = """---
allowed-tools:
  - git
  - docker
metadata:
  openclaw:
    requires:
      bins:
        - git
        - docker
---

Body content."""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            path = Path(f.name)

        try:
            result = parse_spec_file(path)
            tools = result["frontmatter"]["allowed-tools"]
            assert tools.count("git") == 1
            assert tools.count("docker") == 1
        finally:
            path.unlink()

    def test_parse_empty_frontmatter(self):
        """Test parsing with empty frontmatter section."""
        content = """Just a body."""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            path = Path(f.name)

        try:
            result = parse_spec_file(path)
            # Empty frontmatter is parsed as None by yaml.safe_load, which becomes {}
            assert result["frontmatter"] == {} or result["frontmatter"] is None
            assert result["body"] == "Just a body."
        finally:
            path.unlink()

    def test_parse_malformed_yaml(self):
        """Test that malformed YAML in frontmatter raises an error."""
        content = """---
name: test
invalid yaml: [unclosed bracket
---

Body content."""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(Exception):  # yaml.YAMLError
                parse_spec_file(path)
        finally:
            path.unlink()
