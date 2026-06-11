#!/usr/bin/env python3
"""Mellea Skills Compiler — Full Pipeline: SKILL.md → decomposed pipeline → Guardian → certification.

End-to-end demonstration:
  1. Ingest a SKILL.md → parse, classify sensitivity, compose use-case
  2. Identify risks via AI Atlas Nexus → policy manifest
  3. Configure Guardian hooks from manifest (pre + post generation)
  4. Run test fixtures through the DECOMPOSED pipeline
     → Guardian intercepts every m.instruct() call inside the pipeline
     → Audit trail captures every generation + Guardian verdict
  5. Compliance classification
  6. Certification report with runtime evidence
"""

import json
import sys
from pathlib import Path
from typing import Callable, Dict, Optional

from mellea.plugins import PluginViolationError
from rich.console import Console

from mellea_skills_compiler.certification.classification import (
    classify_governance_requirements,
)
from mellea_skills_compiler.certification.data import get_data_path
from mellea_skills_compiler.certification.nexus_policy import (
    generate_policy_manifest,
    generate_policy_markdown,
    load_policy_manifest,
)
from mellea_skills_compiler.certification.report import (
    generate_certification_report,
    load_audit_trail,
)
from mellea_skills_compiler.enums import (
    InferenceEngineType,
    PipelineMode,
    SpecFileFormat,
)
from mellea_skills_compiler.models import PolicyManifest
from mellea_skills_compiler.plugins.audit import AuditTrailPlugin
from mellea_skills_compiler.plugins.guardian import (
    GuardianPlugin,
    GuardianPluginFactory,
)
from mellea_skills_compiler.toolkit.file_utils import (
    load_fixtures,
    load_skill_pipeline,
    parse_spec_file,
)
from mellea_skills_compiler.toolkit.logging import configure_logger


console = Console(log_time=True)

LOGGER = configure_logger()


def _run_single_fixture(pipeline_fn: Callable, fixture: Dict):
    report = None
    try:
        context = fixture["context"]

        # Unpack dict context as kwargs (Pattern 2 pipelines expect keyword args)
        if isinstance(context, dict):
            report = pipeline_fn(**context)
        else:
            report = pipeline_fn(context)

        LOGGER.info("Pipeline executed successfully.")

        # Log key fields if available
        for field in ["location", "weather_data", "action", "summary"]:
            if hasattr(report, field) and getattr(report, field):
                LOGGER.info("  %s: %s", field, str(getattr(report, field))[:100])

    except PluginViolationError as e:
        print()
        LOGGER.warning("Pipeline BLOCKED by Guardian enforcement: %s", e.reason)
        LOGGER.warning("  The decomposed pipeline was halted because a generation")
        LOGGER.warning("  triggered a Guardian risk detection in ENFORCE mode.")
        print()

    return report


def _get_fixture(fixture_id, fixtures):
    # Get the desired fixture
    if fixture_id is None:
        return fixtures[0]
    else:
        for f in fixtures:
            if fixture_id == f["id"]:
                return f

        available = [f["id"] for f in fixtures]
        raise ValueError(f"Unknown fixture '{fixture_id}'. Available: {available}")


def skill_pipeline(
    pipeline_dir: Path,
    fixture_id: str,
    enforce: bool = False,
    no_guardian: bool = False,
):
    guardian_plugin = None
    audit_plugin = None

    if no_guardian:
        LOGGER.info("Guardian checks disabled (--no-guardian)")
    else:
        # Set audit directory
        audit_dir = pipeline_dir.parent / "audit"

        try:
            if not audit_dir.is_dir():
                raise Exception(
                    f"The audit directory is not available in {pipeline_dir.parent}."
                )
            else:
                manifest_path = audit_dir / "policy_manifest.json"
                if not manifest_path.exists():
                    raise Exception("Unable to locate policy manifest [manifest_path].")
                else:
                    # Get pipeline mode - AUDIT or ENFORCE
                    pipeline_mode = PipelineMode(enforce)

                    # Load existing policy manifest
                    manifest = load_policy_manifest(manifest_path)

                    # Configure plugins from manifest
                    LOGGER.info(
                        f"Configuring Guardian hooks from Policy Manifest [{pipeline_mode} mode]...",
                    )
                    guardian_plugin: GuardianPlugin = GuardianPluginFactory.create(
                        pipeline_mode, manifest
                    )
                    guardian_plugin.register()
                    audit_plugin = AuditTrailPlugin(
                        output_dir=audit_dir, guardian_plugin=guardian_plugin
                    )
                    audit_plugin.register()
        except Exception as e:
            console.print(
                f"[yellow]Warning:[/] {str(e)}"
                f" Run [bold]mellea-skills ingest[/] or "
                f"[bold]mellea-skills certify[/] first for Guardian protection. "
            )
            LOGGER.info("Running unguarded.")

    try:

        # Load skill pipeline
        pipeline_fn = load_skill_pipeline(pipeline_dir)

        # Load fixtures from the pipeline directory
        fixtures = load_fixtures(pipeline_dir)

        # Get the desired fixture
        fixture = _get_fixture(fixture_id, fixtures)

        # run given fixture
        output = _run_single_fixture(pipeline_fn, fixture)

        # output
        console.print("[bold blue]OUTPUT:[/]")
        print(output)

    except Exception as e:
        LOGGER.error(f"Pipeline run failed: {str(e)}")
    finally:
        if guardian_plugin:
            guardian_plugin.deregister()
            audit_plugin.deregister()


def full_pipeline(
    pipeline_dir: Path,
    fixture_id: Optional[str] = None,
    enforce: bool = False,
    model: Optional[str] = None,
    guardian_model: Optional[str] = None,
    inference_engine: InferenceEngineType = InferenceEngineType.OLLAMA,
):
    """Full Certification Pipeline for Mellea skill

    Args:
        pipeline_dir (Path): Compiled Mellea skill pipeline directory.
        fixture_id (Optional[str], optional): Specify a fixture to run with the certification process. Defaults to None.
        enforce (bool, optional): Run pipeline in enforce mode (block on risk detection). Defaults to False.
        model (Optional[str], optional): Model to use for Risk and Action Identification. The `inference_engine` param must support the model. If set to None, the default model for the inference engine will be used.
        guardian_model (Optional[str], optional): Model to use for Risk Assessment. The `inference_engine` param must support the model. If set to None, the default guardian model for the inference engine will be used.
        inference_engine (InferenceEngineType, optional): Service to use for LLM inference. Defaults to InferenceEngineType.OLLAMA.
    """

    # Verify skill pipeline directory exists
    if pipeline_dir.exists():
        # Verify that given path is a directory
        if not pipeline_dir.is_dir():
            raise ValueError(
                "The specified path is not a directory. Please note that the certify command only accepts a compiled skill directory."
            )
    else:
        raise FileNotFoundError(f"Skill pipeline directory not found: {pipeline_dir}")

    # Load skill pipeline
    pipeline_fn = load_skill_pipeline(pipeline_dir)

    # Load fixtures from the pipeline directory
    fixtures = load_fixtures(pipeline_dir)

    # Get the desired fixture
    fixture = _get_fixture(fixture_id, fixtures)

    # Get pipeline mode - AUDIT or ENFORCE
    pipeline_mode = PipelineMode(enforce)

    print()
    LOGGER.info("=" * 70)
    LOGGER.info(f"MelleaSkills — Full Pipeline [{pipeline_mode} mode]")
    LOGGER.info("=" * 70)

    # Certification artifacts go into the skill's audit/ directory
    output_dir = pipeline_dir.parent / "audit"
    output_dir.mkdir(exist_ok=True)

    # load and create ai atlas nexus instance
    from ai_atlas_nexus.library import AIAtlasNexus

    from mellea_skills_compiler.certification import skill_to_use_case
    from mellea_skills_compiler.certification.classification import (
        classify_skill_sensitivity,
    )

    # ── Get skill spec-file path ──────────────────────────
    spec_path: Path = pipeline_dir / SpecFileFormat.SKILL_FILE_MD
    if not spec_path.exists():
        raise FileNotFoundError(f"Skill spec file not found: {spec_path}")

    # ── Parse skill specification ──────────────────────────
    print()
    LOGGER.info(f"Ingesting... {spec_path.name}")
    parsed = parse_spec_file(spec_path)
    frontmatter = parsed["frontmatter"]
    LOGGER.info("  Name: %s", frontmatter.get("name", "unknown"))
    LOGGER.info("  Description: %.100s", frontmatter.get("description", ""))
    LOGGER.info("  Tools: %s", frontmatter.get("allowed-tools", []))

    # ── Sensitivity classification ──────────────────────────
    print()
    LOGGER.info("Tool Sensitivity Classification")
    sensitivity = classify_skill_sensitivity(
        frontmatter.get("allowed-tools", []), parsed["body"]
    )
    LOGGER.info("  Tier: %s", sensitivity["tier_display"])
    LOGGER.info("  Operations: %s", sensitivity["operations"])
    if sensitivity["capabilities"]:
        LOGGER.info("  Capabilities: %s", sensitivity["capabilities"])

    # ── Compose use-case description ────────────────────────
    print()
    LOGGER.info(f"Generating Use-case")
    use_case = skill_to_use_case(parsed, sensitivity)
    LOGGER.info(f"  Description: {use_case}")

    # ── Generate policy manifest using AI Atlas Nexus ────────────────────
    print()
    LOGGER.info("Identifying risks via AI Atlas Nexus...")
    nexus_data_path = get_data_path()
    nexus = AIAtlasNexus(base_dir=nexus_data_path)
    manifest = generate_policy_manifest(use_case, nexus, model, inference_engine)
    manifest_path = output_dir / "policy_manifest.json"
    manifest.to_json(manifest_path)

    # ── Generate policy markdown ────────────────────
    policy_md = generate_policy_markdown(manifest)
    policy_path = output_dir / "POLICY.md"
    policy_path.write_text(policy_md)

    # Log policy artifacts
    LOGGER.info("Guardian risks: %d", len(manifest.risks))
    for r in manifest.risks:
        tier = "native" if r.is_native else "custom"
        LOGGER.info("    - %s (%s)", r.name, tier)
    LOGGER.info("Governance actions: %d", len(manifest.governance_actions))
    LOGGER.info("Policy manifest: %s", manifest_path)
    LOGGER.info("Policy document: %s", policy_path)

    # ── Step 3: Configure plugins from manifest ───────────────────────
    print()
    LOGGER.info(
        f"Configuring Guardian hooks from Policy Manifest [{pipeline_mode} mode]...",
    )
    guardian_plugin: GuardianPlugin = GuardianPluginFactory.create(
        pipeline_mode, manifest, guardian_model, inference_engine
    )
    guardian_plugin.register()
    audit_plugin = AuditTrailPlugin(
        log_path=output_dir / "audit_trail.jsonl", guardian_plugin=guardian_plugin
    )
    audit_plugin.register()

    # ── Step 4: Run the decomposed pipeline ───────────────────────────
    print()
    LOGGER.info("Running decomposed pipeline from %s...", pipeline_dir.name)
    LOGGER.info(f"  - Fixture: {fixture["id"]}")
    LOGGER.info("  - Guardian checks every generation (pre + post).")
    LOGGER.info("  - Audit Trail checks every end points (pre + post).")

    try:
        # run the given fixture
        report = _run_single_fixture(pipeline_fn, fixture)
        if report:
            # Write the pipeline's report (works for any Pydantic model)
            report_json_path = output_dir / "pipeline_report.json"
            if hasattr(report, "model_dump_json"):
                report_json_path.write_text(report.model_dump_json(indent=2))
            else:
                report_json_path.write_text(json.dumps(report, indent=2, default=str))

            LOGGER.info("Pipeline report: %s", report_json_path)
    except Exception as e:
        LOGGER.error(f"Pipeline run failed: {str(e)}")
    finally:
        guardian_plugin.deregister()
        audit_plugin.deregister()

    # ── Step 5: Guardian verdict summary ──────────────────────────────
    guardian_summary = guardian_plugin.summary()
    LOGGER.info("")
    LOGGER.info("=" * 70)
    LOGGER.info("Guardian Verdict Summary")
    LOGGER.info("=" * 70)

    LOGGER.info("  Total verdicts: %d", guardian_summary["total_verdicts"])
    LOGGER.info("  Passed (No risk): %d", len(guardian_summary["passed_verdicts"]))
    LOGGER.info(
        "  Flagged (Risk detected): %d", len(guardian_summary["flagged_verdicts"])
    )
    LOGGER.info(
        "  Failed (Guardian error): %d", len(guardian_summary["failed_verdicts"])
    )
    if guardian_summary["flagged_verdicts"]:
        LOGGER.info("  Flagged risks:")
        for v in guardian_summary["flagged_verdicts"]:
            LOGGER.info(
                "    [!!] risk=%-25s raw=%.50s",
                v.risk,
                v.raw_output.replace("\n", " "),
            )

    # ── Step 6: Audit trail summary ───────────────────────────────────
    LOGGER.info("")
    summary = audit_plugin.summary()
    LOGGER.info("=" * 70)
    LOGGER.info("Audit Trail Summary")
    LOGGER.info("=" * 70)
    for k, v in summary.items():
        LOGGER.info("  %s: %s", k, v)

    # ── Step 7: Compliance classification ─────────────────────────────
    LOGGER.info("")
    LOGGER.info("=" * 70)
    LOGGER.info("Compliance Classification")
    LOGGER.info("=" * 70)
    compliance = classify_governance_requirements(manifest, nexus)
    counts = compliance.counts
    total = sum(counts.values())
    LOGGER.info(
        "  AUTOMATED: %d  |  PARTIAL: %d  |  MANUAL: %d  (total: %d)",
        counts["AUTOMATED"],
        counts["PARTIAL"],
        counts["MANUAL"],
        total,
    )

    # ── Step 8: Certification report ──────────────────────────────────
    LOGGER.info("")
    LOGGER.info("=" * 70)
    LOGGER.info("Certification Report")
    LOGGER.info("=" * 70)
    audit_entries = load_audit_trail(audit_plugin.log_path)
    cert_report = generate_certification_report(
        manifest,
        compliance,
        audit_entries,
        str(audit_plugin.log_path),
    )
    cert_path = output_dir / "CERTIFICATION.md"
    cert_path.write_text(cert_report)
    LOGGER.info(f"  Report generated: {cert_path}")

    # ── Final summary ─────────────────────────────────────────────────
    LOGGER.info("")
    any_risk = any(v.label == "Yes" for v in guardian_plugin.all_verdicts)
    LOGGER.info("=" * 70)
    skill_name = frontmatter.get("name", "unknown")
    LOGGER.info(f"COMPLETE — {skill_name} [{pipeline_mode} mode]")
    LOGGER.info("=" * 70)
    LOGGER.info("")
    LOGGER.info("  Skill: %s (%s)", skill_name, sensitivity["tier_display"])
    LOGGER.info("  Fixture: %s", fixture["id"])
    LOGGER.info("  Guardian risks: %d (from Nexus)", len(manifest.risks))
    LOGGER.info(
        "  Guardian verdicts: %d total, %d flagged",
        guardian_summary["total_verdicts"],
        len(guardian_summary["flagged_verdicts"]),
    )
    LOGGER.info("  Audit events: %d", len(audit_entries))
    LOGGER.info(
        "  Compliance: AUTOMATED=%d PARTIAL=%d MANUAL=%d",
        counts["AUTOMATED"],
        counts["PARTIAL"],
        counts["MANUAL"],
    )
    LOGGER.info("")
    LOGGER.info("  Artifacts in %s/:", output_dir)
    LOGGER.info("    policy_manifest.json — Policy manifest")
    LOGGER.info("    POLICY.md            — Policy document")
    LOGGER.info("    pipeline_report.json — Pipeline Report")
    LOGGER.info("    audit_trail.jsonl    — Runtime Audit Trail")
    LOGGER.info("    CERTIFICATION.md     — Certification Report")
    LOGGER.info("")

    if any_risk:
        LOGGER.warning("  STATUS: RISKS DETECTED — review audit trail")
    else:
        LOGGER.info("  STATUS: ALL CHECKS PASSED")
