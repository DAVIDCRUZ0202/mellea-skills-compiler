"""Unit tests for mellea_skills_compiler.compile.smoke_check module."""

import json
import time

import pytest

from mellea_skills_compiler.compile.smoke_check import (
    _classify_exception,
    _run_one_fixture,
    run_smoke_check,
)


class TestClassifyException:
    """Test cases for _classify_exception()."""

    def test_connection_error_classified_as_skipped(self):
        reason = _classify_exception(ConnectionError("nope"))
        assert reason is not None
        assert reason.startswith("backend unreachable: ConnectionError")

    def test_timeout_error_classified_as_skipped(self):
        reason = _classify_exception(TimeoutError("slow"))
        assert reason is not None
        assert reason.startswith("backend unreachable: timeout")

    def test_http_unauthorized_classified_as_skipped(self):
        reason = _classify_exception(Exception("HTTP 401 Unauthorized"))
        assert reason is not None
        assert "authentication failed" in reason

    def test_http_forbidden_classified_as_skipped(self):
        reason = _classify_exception(Exception("403 Forbidden"))
        assert reason is not None
        assert "authentication failed" in reason

    def test_value_error_classified_as_failed(self):
        reason = _classify_exception(ValueError("schema mismatch"))
        assert reason is None

    def test_assertion_error_classified_as_failed(self):
        reason = _classify_exception(AssertionError("boom"))
        assert reason is None

    def test_named_httpx_connect_error_classified_as_skipped(self):
        connect_error_cls = type(
            "ConnectError", (Exception,), {"__module__": "httpx"}
        )
        exc = connect_error_cls("conn refused")
        reason = _classify_exception(exc)
        assert reason is not None
        assert "backend unreachable: httpx.ConnectError" in reason


class TestRunOneFixture:
    """Test cases for _run_one_fixture()."""

    def test_passes_when_pipeline_returns(self):
        pipeline_fn = lambda **k: "ok"  # noqa: E731
        fixture = {"id": "f1", "context": {"x": 1}}
        result = _run_one_fixture(pipeline_fn, fixture)
        assert result.verdict == "passed"
        assert result.failure_message is None
        assert result.fixture_id == "f1"

    def test_failed_on_value_error(self):
        def pipeline_fn(**kwargs):
            raise ValueError("schema bad")

        fixture = {"id": "f-fail", "context": {}}
        result = _run_one_fixture(pipeline_fn, fixture)
        assert result.verdict == "failed"
        assert "ValueError" in result.failure_message
        assert result.failure_traceback
        assert len(result.failure_traceback) > 0

    def test_skipped_on_connection_error(self):
        def pipeline_fn(**kwargs):
            raise ConnectionError("ollama down")

        fixture = {"id": "f-skip", "context": {}}
        result = _run_one_fixture(pipeline_fn, fixture)
        assert result.verdict == "skipped"
        assert result.skipped_reason
        assert len(result.skipped_reason) > 0

    def test_records_duration(self):
        def pipeline_fn(**kwargs):
            time.sleep(0.05)

        fixture = {"id": "f-dur", "context": {}}
        result = _run_one_fixture(pipeline_fn, fixture)
        assert result.duration_seconds > 0

    def test_handles_dict_context_as_kwargs(self):
        captured = []

        def pipeline_fn(name, value):
            captured.append((name, value))

        fixture = {"id": "f-kwargs", "context": {"name": "x", "value": 42}}
        result = _run_one_fixture(pipeline_fn, fixture)
        assert result.verdict == "passed"
        assert captured == [("x", 42)]

    def test_handles_non_dict_context_as_positional(self):
        captured = []

        def pipeline_fn(arg):
            captured.append(arg)

        fixture = {"id": "f-pos", "context": "raw_input_string"}
        result = _run_one_fixture(pipeline_fn, fixture)
        assert result.verdict == "passed"
        assert captured == ["raw_input_string"]


class TestRunSmokeCheck:
    """Test cases for run_smoke_check()."""

    def _patch_loaders(self, monkeypatch, pipeline_fn, fixtures):
        monkeypatch.setattr(
            "mellea_skills_compiler.compile.smoke_check.load_skill_pipeline",
            lambda d: pipeline_fn,
        )
        monkeypatch.setattr(
            "mellea_skills_compiler.compile.smoke_check.load_fixtures",
            lambda d: fixtures,
        )

    def test_passed_runs_first_fixture_only_by_default(
        self, monkeypatch, tmp_path
    ):
        fixtures = [
            {"id": "f1", "context": {}},
            {"id": "f2", "context": {}},
            {"id": "f3", "context": {}},
        ]
        self._patch_loaders(monkeypatch, lambda **k: "ok", fixtures)

        result = run_smoke_check(tmp_path, all_fixtures=False)

        assert len(result.fixtures) == 1
        assert result.fixtures[0].fixture_id == "f1"
        assert result.overall_verdict == "passed"
        report_path = tmp_path / "intermediate" / "step_7b_report.json"
        assert report_path.exists()

    def test_runs_all_when_all_fixtures_true(self, monkeypatch, tmp_path):
        fixtures = [
            {"id": "f1", "context": {}},
            {"id": "f2", "context": {}},
            {"id": "f3", "context": {}},
        ]
        self._patch_loaders(monkeypatch, lambda **k: "ok", fixtures)

        result = run_smoke_check(tmp_path, all_fixtures=True)

        assert len(result.fixtures) == 3
        assert result.overall_verdict == "passed"

    def test_overall_failed_when_any_fixture_failed(
        self, monkeypatch, tmp_path
    ):
        call_count = {"n": 0}

        def pipeline_fn(**kwargs):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise ValueError("second failure")
            return "ok"

        fixtures = [
            {"id": "f1", "context": {}},
            {"id": "f2", "context": {}},
        ]
        self._patch_loaders(monkeypatch, pipeline_fn, fixtures)

        result = run_smoke_check(tmp_path, all_fixtures=True)

        assert result.overall_verdict == "failed"

    def test_overall_skipped_when_all_skipped(self, monkeypatch, tmp_path):
        def pipeline_fn(**kwargs):
            raise ConnectionError("backend down")

        fixtures = [{"id": "f1", "context": {}}]
        self._patch_loaders(monkeypatch, pipeline_fn, fixtures)

        result = run_smoke_check(tmp_path, all_fixtures=False)

        assert result.overall_verdict == "skipped"

    def test_step_7b_report_shape(self, monkeypatch, tmp_path):
        fixtures = [{"id": "f1", "context": {}}]
        self._patch_loaders(monkeypatch, lambda **k: "ok", fixtures)

        run_smoke_check(tmp_path, all_fixtures=False)

        report_path = tmp_path / "intermediate" / "step_7b_report.json"
        assert report_path.exists()
        data = json.loads(report_path.read_text())
        assert "format_version" in data
        assert "checked_at" in data
        assert "package_path" in data
        assert "overall_verdict" in data
        assert "fixtures" in data
        assert isinstance(data["fixtures"], list)
        assert len(data["fixtures"]) == 1
        fx = data["fixtures"][0]
        assert "fixture_id" in fx
        assert "verdict" in fx
        assert "duration_seconds" in fx

    def test_exit_code_passed_is_zero(self, monkeypatch, tmp_path):
        fixtures = [{"id": "f1", "context": {}}]
        self._patch_loaders(monkeypatch, lambda **k: "ok", fixtures)

        result = run_smoke_check(tmp_path, all_fixtures=False)
        assert result.exit_code == 0

    def test_exit_code_failed_is_twelve(self, monkeypatch, tmp_path):
        def pipeline_fn(**kwargs):
            raise ValueError("bad")

        fixtures = [{"id": "f1", "context": {}}]
        self._patch_loaders(monkeypatch, pipeline_fn, fixtures)

        result = run_smoke_check(tmp_path, all_fixtures=False)
        assert result.exit_code == 12

    def test_exit_code_skipped_is_zero(self, monkeypatch, tmp_path):
        def pipeline_fn(**kwargs):
            raise ConnectionError("down")

        fixtures = [{"id": "f1", "context": {}}]
        self._patch_loaders(monkeypatch, pipeline_fn, fixtures)

        result = run_smoke_check(tmp_path, all_fixtures=False)
        assert result.exit_code == 0
