"""Verification report data models and serialization (YP §11, specs.md §9)."""

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from aethel_codex.constants import TOOL_NAME, TOOL_PROFILE, TOOL_VERSION, YELLOW_PAPER_VERSION


class Status(StrEnum):
    """Verification check status."""

    PASS = "PASS"  # noqa: S105
    WARN = "WARN"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True)
class CheckResult:
    """Individual verification check result (V1-V8)."""

    id: str  # V1 .. V8
    status: str | Status  # PASS, WARN, FAIL, SKIPPED
    code: str | None = None
    detail: str | None = None
    items: list[dict[str, Any]] = field(default_factory=list)

    def status_value(self) -> str:
        """Return raw string status value."""
        return self.status.value if isinstance(self.status, Status) else str(self.status)

    def status_summary(self) -> str:
        """Format concise status string (e.g. 'PASS', 'SKIPPED:NO_PARENTS')."""
        val = self.status_value()
        if self.code and val in ("WARN", "FAIL", "SKIPPED"):
            return f"{val}:{self.code}"
        return val

    def to_dict(self) -> dict[str, Any]:
        """Convert check result to dictionary for JSON output."""
        return {
            "id": self.id,
            "status": self.status_value(),
            "code": self.code,
            "detail": self.detail,
            "items": self.items,
        }


@dataclass(frozen=True)
class AttributionReport:
    """Attribution assessment per Yellow Paper §11.3."""

    cls: str  # Unattributed, Partially attributed, Attributed, Dual-family
    signed: int
    declared: int
    keccak_independent: bool
    keys: list[dict[str, Any]] = field(default_factory=list)
    other_signatures: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict matching CLI JSON schema."""
        return {
            "class": self.cls,
            "signed": self.signed,
            "declared": self.declared,
            "keccak_independent": self.keccak_independent,
            "keys": self.keys,
            "other_signatures": self.other_signatures,
        }


@dataclass(frozen=True)
class VerifyReport:
    """Comprehensive verification report (YP §11.3, specs.md §9)."""

    bundle_path: str
    manifest_id: str | None
    work_id: str | None
    integrity: str  # PASS, FAIL, INCONCLUSIVE
    attribution: AttributionReport
    history: dict[str, Any]
    time: dict[str, Any]
    checks: list[CheckResult]
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    exit_code: int = 0

    def checks_dict(self) -> dict[str, str]:
        """Return dict of check id to concise status string matching fixture expected.json."""
        return {c.id: c.status_summary() for c in self.checks}

    def to_dict(self) -> dict[str, Any]:
        """Convert report to schema-compliant dictionary matching aethel.verify/1."""
        return {
            "schema": "aethel.verify/1",
            "tool": {
                "name": TOOL_NAME,
                "version": TOOL_VERSION,
                "profile": TOOL_PROFILE,
                "yellow_paper": YELLOW_PAPER_VERSION,
            },
            "bundle": {
                "path": self.bundle_path,
                "manifest_id": self.manifest_id or "",
                "work_id": self.work_id or "",
            },
            "integrity": self.integrity,
            "attribution": self.attribution.to_dict(),
            "history": self.history,
            "time": self.time,
            "checks": [c.to_dict() for c in self.checks],
            "warnings": self.warnings,
            "notes": self.notes,
        }

    def to_json(self, indent: int | None = None) -> str:
        """Serialize report to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
