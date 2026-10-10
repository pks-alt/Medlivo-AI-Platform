#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "docs/ENGINEERING_OPERATING_MODEL.md",
    "docs/CURRENT_PLATFORM_STATE.md",
    "docs/PHASE1_COMPLETION_MATRIX.md",
    "docs/NEXT_DEVELOPMENT_SLICE.md",
    "docs/decisions/001-jobdiva-system-of-record.md",
    "docs/decisions/002-role-and-rate-ownership.md",
    "docs/decisions/003-ai-human-decision-boundary.md",
    "docs/decisions/004-division-channel-model.md",
    "docs/decisions/005-submission-vs-start-readiness.md",
    "RELEASE_STATE.json",
]

OPERATING_MODEL_REQUIRED_TEXT = [
    "`main` is the only canonical development baseline",
    "One coherent capability per PR",
    "Build vertical slices, not disconnected pieces",
    "System-of-record boundaries are explicit",
    "Human consequential decisions remain explicit",
    "Staging mirrors the real application architecture",
    "Architecture decisions are deliberate",
    "Product expansion is expected",
]

CURRENT_STATE_REQUIRED_TEXT = [
    "JobDiva remains system of record",
    "Phase 1 JobDiva access remains read-only",
    "Nursing & Allied",
    "MSP/VMS only",
    "Locum Tenens",
    "Submission Studio",
    "Submission → Start",
]


def fail(message: str) -> None:
    print(f"PLATFORM CONTROL ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).is_file()]
    if missing:
        fail("missing required control files: " + ", ".join(missing))

    operating = (ROOT / "docs/ENGINEERING_OPERATING_MODEL.md").read_text()
    for required in OPERATING_MODEL_REQUIRED_TEXT:
        if required not in operating:
            fail(f"engineering operating model no longer contains required rule: {required}")

    current = (ROOT / "docs/CURRENT_PLATFORM_STATE.md").read_text()
    for required in CURRENT_STATE_REQUIRED_TEXT:
        if required not in current:
            fail(f"current platform state no longer contains required boundary: {required}")

    try:
        release = json.loads((ROOT / "RELEASE_STATE.json").read_text())
    except json.JSONDecodeError as exc:
        fail(f"RELEASE_STATE.json is invalid JSON: {exc}")

    if release.get("canonical_repository") != "pks-alt/Medlivo-AI-Platform":
        fail("canonical repository changed unexpectedly")
    if release.get("canonical_branch") != "main":
        fail("canonical branch must remain main")

    policy = release.get("source_of_truth_policy") or {}
    if policy.get("jobdiva_is_ats") is not True:
        fail("JobDiva ATS boundary changed without an explicit architecture update")
    if policy.get("phase1_jobdiva_writeback_allowed") is not False:
        fail("Phase 1 JobDiva writeback must remain disabled")
    if policy.get("medlivo_second_ats_allowed") is not False:
        fail("Medlivo must not become a second ATS")

    print("Platform control layer is present and internally consistent.")


if __name__ == "__main__":
    main()
