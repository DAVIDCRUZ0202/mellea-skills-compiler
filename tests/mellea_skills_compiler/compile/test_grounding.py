"""Unit tests for mellea_skills_compiler.compile.grounding module.

These tests must NOT pollute the user's real ~/.cache/mellea-skills-compiler/.
The module-level CACHE_DIR constant is patched per-test to a temp path.
"""

import importlib.metadata
import json
import time
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mellea_skills_compiler.compile import grounding
from mellea_skills_compiler.compile.grounding import (
    _DOC_PAGES_FALLBACK,
    _FORBIDDEN_PARAM_NAMES_FALLBACK,
    _atomic_write,
    write_mellea_api_ref,
    write_mellea_doc_index,
)


@pytest.fixture
def patched_cache(monkeypatch, tmp_path):
    """Redirect grounding.CACHE_DIR to a per-test temp directory."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(grounding, "CACHE_DIR", cache_dir)
    return cache_dir


@pytest.fixture
def intermediate_dir(tmp_path):
    """A clean intermediate directory for grounding outputs."""
    d = tmp_path / "intermediate"
    d.mkdir(parents=True, exist_ok=True)
    return d


class TestAtomicWrite:
    """Test cases for the _atomic_write helper."""

    def test_writes_content_to_path(self, tmp_path):
        target = tmp_path / "out.txt"
        _atomic_write(target, "hello world")
        assert target.read_text() == "hello world"

    def test_creates_parent_directory(self, tmp_path):
        target = tmp_path / "new" / "sub" / "file.txt"
        _atomic_write(target, "nested")
        assert target.exists()
        assert target.read_text() == "nested"
        assert target.parent.is_dir()

    def test_no_tmp_file_left_behind(self, tmp_path):
        target = tmp_path / "out.txt"
        _atomic_write(target, "data")
        # No sibling .tmp file should remain after a successful write.
        siblings = list(target.parent.glob("*.tmp"))
        assert siblings == []

    def test_overwrites_existing_file(self, tmp_path):
        target = tmp_path / "out.txt"
        _atomic_write(target, "first")
        assert target.read_text() == "first"
        _atomic_write(target, "second")
        assert target.read_text() == "second"


class TestWriteMelleaApiRef:
    """Test cases for write_mellea_api_ref."""

    def test_writes_grounding_unavailable_when_mellea_missing(
        self, patched_cache, intermediate_dir, monkeypatch
    ):
        def _raise(_pkg):
            raise importlib.metadata.PackageNotFoundError("mellea")

        monkeypatch.setattr(
            "mellea_skills_compiler.compile.grounding.importlib.metadata.version",
            _raise,
        )

        out_path = write_mellea_api_ref(intermediate_dir)
        assert out_path == intermediate_dir / "mellea_api_ref.json"
        assert out_path.exists()

        payload = json.loads(out_path.read_text())
        assert payload["grounding_unavailable"] is True
        assert payload["mellea_version"] is None
        assert payload["modules"] == {}
        assert payload["forbidden_param_names"] == list(
            _FORBIDDEN_PARAM_NAMES_FALLBACK
        )
        # The static fallback list per mellea-fy-deps.md has 9 entries.
        assert len(payload["forbidden_param_names"]) == 9
        assert payload["compatibility"] == []

    def test_writes_real_introspection_when_mellea_available(
        self, patched_cache, intermediate_dir
    ):
        pytest.importorskip("mellea")

        out_path = write_mellea_api_ref(intermediate_dir)
        assert out_path.exists()

        payload = json.loads(out_path.read_text())
        assert payload["grounding_unavailable"] is False
        assert isinstance(payload["mellea_version"], str)
        assert payload["mellea_version"]  # non-empty
        assert isinstance(payload["modules"], dict)
        assert len(payload["modules"]) > 0
        assert isinstance(payload["forbidden_param_names"], list)
        assert len(payload["forbidden_param_names"]) > 0

    def test_uses_cache_on_second_call(
        self, patched_cache, intermediate_dir, monkeypatch
    ):
        # Force a deterministic version so we can locate the cache file.
        monkeypatch.setattr(
            "mellea_skills_compiler.compile.grounding.importlib.metadata.version",
            lambda pkg: "0.4.2",
        )
        # Stub introspection to keep the test fast and avoid touching real mellea.
        monkeypatch.setattr(
            grounding, "_introspect_mellea", lambda referenced: {"fake.module": {}}
        )
        monkeypatch.setattr(
            grounding, "_extract_forbidden_param_names", lambda: ["x"]
        )
        monkeypatch.setattr(
            grounding, "_load_compatibility_entries", lambda v: []
        )

        cache_path = patched_cache / "api_ref_0.4.2.json"
        assert not cache_path.exists()

        write_mellea_api_ref(intermediate_dir)
        assert cache_path.exists()
        first_mtime = cache_path.stat().st_mtime

        # Sleep briefly so a regeneration would noticeably bump mtime.
        time.sleep(0.05)

        # Replace introspection with a sentinel that would fail if invoked.
        def _should_not_be_called(referenced):
            raise AssertionError(
                "_introspect_mellea should not run on a cache hit"
            )

        monkeypatch.setattr(grounding, "_introspect_mellea", _should_not_be_called)

        write_mellea_api_ref(intermediate_dir)
        # Cache file was not regenerated.
        assert cache_path.stat().st_mtime == first_mtime

    def test_refresh_true_rebuilds_cache(
        self, patched_cache, intermediate_dir, monkeypatch
    ):
        monkeypatch.setattr(
            "mellea_skills_compiler.compile.grounding.importlib.metadata.version",
            lambda pkg: "0.4.2",
        )

        call_count = {"n": 0}

        def _counting_introspect(referenced):
            call_count["n"] += 1
            return {"fake.module": {}}

        monkeypatch.setattr(grounding, "_introspect_mellea", _counting_introspect)
        monkeypatch.setattr(
            grounding, "_extract_forbidden_param_names", lambda: ["x"]
        )
        monkeypatch.setattr(
            grounding, "_load_compatibility_entries", lambda v: []
        )

        write_mellea_api_ref(intermediate_dir)
        assert call_count["n"] == 1

        time.sleep(0.05)
        write_mellea_api_ref(intermediate_dir, refresh=True)
        # refresh=True must re-run introspection (cache was bypassed).
        assert call_count["n"] == 2

    def test_cache_keyed_by_version(
        self, patched_cache, intermediate_dir, monkeypatch
    ):
        monkeypatch.setattr(
            grounding, "_introspect_mellea", lambda referenced: {}
        )
        monkeypatch.setattr(
            grounding, "_extract_forbidden_param_names", lambda: []
        )
        monkeypatch.setattr(
            grounding, "_load_compatibility_entries", lambda v: []
        )

        # First version.
        monkeypatch.setattr(
            "mellea_skills_compiler.compile.grounding.importlib.metadata.version",
            lambda pkg: "0.4.2",
        )
        write_mellea_api_ref(intermediate_dir)

        # Second version.
        monkeypatch.setattr(
            "mellea_skills_compiler.compile.grounding.importlib.metadata.version",
            lambda pkg: "0.5.0",
        )
        write_mellea_api_ref(intermediate_dir)

        assert (patched_cache / "api_ref_0.4.2.json").exists()
        assert (patched_cache / "api_ref_0.5.0.json").exists()

    def test_writes_to_intermediate_dir(
        self, patched_cache, intermediate_dir, monkeypatch
    ):
        monkeypatch.setattr(
            "mellea_skills_compiler.compile.grounding.importlib.metadata.version",
            lambda pkg: "0.4.2",
        )
        monkeypatch.setattr(
            grounding, "_introspect_mellea", lambda referenced: {"m": {}}
        )
        monkeypatch.setattr(
            grounding, "_extract_forbidden_param_names", lambda: ["a"]
        )
        monkeypatch.setattr(
            grounding, "_load_compatibility_entries", lambda v: []
        )

        out_path = write_mellea_api_ref(intermediate_dir)
        assert isinstance(out_path, Path)
        assert out_path == intermediate_dir / "mellea_api_ref.json"
        assert out_path.exists()

        cache_path = patched_cache / "api_ref_0.4.2.json"
        assert cache_path.exists()
        assert out_path.read_text() == cache_path.read_text()


def _make_fake_urlopen_response(body: bytes) -> MagicMock:
    """Create a context-manager-compatible fake urlopen response."""
    fake = MagicMock()
    fake.read.return_value = body
    fake.__enter__ = lambda self: self
    fake.__exit__ = lambda *a: None
    return fake


class TestWriteMelleaDocIndex:
    """Test cases for write_mellea_doc_index."""

    def test_writes_fetched_pages_when_network_succeeds(
        self, patched_cache, intermediate_dir
    ):
        body = (
            b'<html><body>'
            b'<a href="/getting-started/installation">Install</a>'
            b'<a href="/concepts/requirements-system">Reqs</a>'
            b'<a href="https://external.example/should-be-ignored">External</a>'
            b'</body></html>'
        )
        fake_response = _make_fake_urlopen_response(body)

        with patch(
            "mellea_skills_compiler.compile.grounding.urllib.request.urlopen",
            return_value=fake_response,
        ):
            out_path = write_mellea_doc_index(intermediate_dir)

        assert out_path.exists()
        payload = json.loads(out_path.read_text())
        assert payload["fetch_status"] == "ok"
        assert "/getting-started/installation" in payload["doc_pages"]
        assert "/concepts/requirements-system" in payload["doc_pages"]
        # External absolute URLs should not be picked up by the / regex.
        for page in payload["doc_pages"]:
            assert page.startswith("/")

        # `fetched_at` is recent (within last few seconds).
        fetched_at = datetime.fromisoformat(payload["fetched_at"])
        age = datetime.now(timezone.utc) - fetched_at
        assert age.total_seconds() < 60

        # Cache populated for next call.
        assert (patched_cache / "doc_index.json").exists()

    def test_writes_static_fallback_when_fetch_fails_and_no_cache(
        self, patched_cache, intermediate_dir
    ):
        # No cache file exists at the start of this test.
        cache_path = patched_cache / "doc_index.json"
        assert not cache_path.exists()

        with patch(
            "mellea_skills_compiler.compile.grounding.urllib.request.urlopen",
            side_effect=urllib.error.URLError("offline"),
        ):
            out_path = write_mellea_doc_index(intermediate_dir)

        payload = json.loads(out_path.read_text())
        assert payload["fetch_status"].startswith("failed:")
        assert payload["doc_pages"] == list(_DOC_PAGES_FALLBACK)
        assert len(payload["doc_pages"]) > 0

    def test_uses_stale_cache_when_fetch_fails_and_cache_exists(
        self, patched_cache, intermediate_dir
    ):
        # Write a stale cache file (well outside default 24h TTL).
        stale_time = (
            datetime.now(timezone.utc) - timedelta(days=30)
        ).isoformat()
        stale_payload = {
            "format_version": "1.0",
            "fetched_at": stale_time,
            "source": "https://docs.mellea.ai/",
            "fetch_status": "ok",
            "doc_pages": ["/stale/page-from-cache"],
        }
        cache_path = patched_cache / "doc_index.json"
        cache_path.write_text(json.dumps(stale_payload))

        with patch(
            "mellea_skills_compiler.compile.grounding.urllib.request.urlopen",
            side_effect=urllib.error.URLError("offline"),
        ):
            out_path = write_mellea_doc_index(intermediate_dir)

        written = json.loads(out_path.read_text())
        # Stale cache content was reused.
        assert written["doc_pages"] == ["/stale/page-from-cache"]
        assert written["fetched_at"] == stale_time

    def test_within_ttl_uses_cache_without_fetch(
        self, patched_cache, intermediate_dir
    ):
        # Fresh cache: written "now".
        fresh_time = datetime.now(timezone.utc).isoformat()
        fresh_payload = {
            "format_version": "1.0",
            "fetched_at": fresh_time,
            "source": "https://docs.mellea.ai/",
            "fetch_status": "ok",
            "doc_pages": ["/fresh/from-cache"],
        }
        cache_path = patched_cache / "doc_index.json"
        cache_path.write_text(json.dumps(fresh_payload))

        # urlopen would raise if called — proving we never hit the network.
        with patch(
            "mellea_skills_compiler.compile.grounding.urllib.request.urlopen",
            side_effect=AssertionError("urlopen must not be called within TTL"),
        ):
            out_path = write_mellea_doc_index(intermediate_dir)

        written = json.loads(out_path.read_text())
        assert written["doc_pages"] == ["/fresh/from-cache"]
        assert written["fetched_at"] == fresh_time

    def test_refresh_true_bypasses_cache(self, patched_cache, intermediate_dir):
        # Pre-populate a fresh cache so a non-refresh call would short-circuit.
        fresh_time = datetime.now(timezone.utc).isoformat()
        fresh_payload = {
            "format_version": "1.0",
            "fetched_at": fresh_time,
            "source": "https://docs.mellea.ai/",
            "fetch_status": "ok",
            "doc_pages": ["/fresh/from-cache"],
        }
        cache_path = patched_cache / "doc_index.json"
        cache_path.write_text(json.dumps(fresh_payload))

        body = b'<a href="/refreshed/page">R</a>'
        fake_response = _make_fake_urlopen_response(body)

        with patch(
            "mellea_skills_compiler.compile.grounding.urllib.request.urlopen",
            return_value=fake_response,
        ) as mock_urlopen:
            out_path = write_mellea_doc_index(intermediate_dir, refresh=True)
            assert mock_urlopen.called

        written = json.loads(out_path.read_text())
        assert written["fetch_status"] == "ok"
        assert "/refreshed/page" in written["doc_pages"]

    def test_writes_to_intermediate_dir(self, patched_cache, intermediate_dir):
        body = b'<a href="/getting-started/installation">x</a>'
        fake_response = _make_fake_urlopen_response(body)

        with patch(
            "mellea_skills_compiler.compile.grounding.urllib.request.urlopen",
            return_value=fake_response,
        ):
            out_path = write_mellea_doc_index(intermediate_dir)

        assert isinstance(out_path, Path)
        assert out_path == intermediate_dir / "mellea_doc_index.json"
        assert out_path.exists()
