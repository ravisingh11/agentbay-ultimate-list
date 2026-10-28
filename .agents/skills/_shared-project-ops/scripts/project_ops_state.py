#!/usr/bin/env python3
"""Deterministic state management for project-ops findings and reports."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

FINDING_SUMMARY_ORDER = [
    "Audit date",
    "Scope",
    "Branch",
    "GitHub issue sync",
    "Final state",
]

FINDING_LIST_FIELDS = [
    ("Evidence", "evidence"),
    ("Impact", "impact"),
    ("Verification", "verification"),
    ("Fix Plan", "fix_plan"),
    ("Resolution Notes", "resolution_notes"),
]

REPORT_SUMMARY_ORDER = [
    "Mode",
    "Profile",
    "Scope",
    "Branch",
    "Dirty worktree",
    "GitHub issue sync",
    "Final state",
    "Updated at",
]

STATUS_ORDER = {
    "confirmed-open": 0,
    "in-progress": 1,
    "blocked": 2,
    "needs-context": 3,
    "resolved": 4,
}

SEVERITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}

TYPE_ORDER = {
    "security": 0,
    "api-contract": 1,
    "bug": 2,
    "release": 3,
    "dependency": 4,
    "migration": 5,
    "testing": 6,
    "health": 7,
    "config": 8,
    "observability": 9,
    "frontend": 10,
    "docs": 11,
}

NONE_MARKER = "none"


@dataclass
class Finding:
    finding_id: str
    title: str
    status: str = "confirmed-open"
    finding_type: str = "bug"
    severity: str = "medium"
    surface: str = ""
    github_issue: str = "none"
    evidence: list[str] = field(default_factory=list)
    impact: list[str] = field(default_factory=list)
    verification: list[str] = field(default_factory=list)
    fix_plan: list[str] = field(default_factory=list)
    resolution_notes: list[str] = field(default_factory=list)

    def apply_update(self, payload: dict[str, Any]) -> None:
        scalar_map = {
            "title": "title",
            "status": "status",
            "type": "finding_type",
            "finding_type": "finding_type",
            "severity": "severity",
            "surface": "surface",
            "github_issue": "github_issue",
        }
        for key, attr in scalar_map.items():
            if key in payload and payload[key] is not None:
                setattr(self, attr, str(payload[key]))

        list_map = {
            "evidence": "evidence",
            "impact": "impact",
            "verification": "verification",
            "fix_plan": "fix_plan",
            "resolution_notes": "resolution_notes",
        }
        for key, attr in list_map.items():
            if key in payload and payload[key] is not None:
                setattr(self, attr, [str(item) for item in payload[key]])

    def merge_from(self, duplicate: "Finding") -> None:
        for attr in ("evidence", "impact", "verification", "fix_plan", "resolution_notes"):
            merged = list(getattr(self, attr))
            for item in getattr(duplicate, attr):
                if item not in merged:
                    merged.append(item)
            setattr(self, attr, merged)

        if self.github_issue == "none" and duplicate.github_issue != "none":
            self.github_issue = duplicate.github_issue

        if STATUS_ORDER.get(duplicate.status, 99) < STATUS_ORDER.get(self.status, 99):
            self.status = duplicate.status

        if SEVERITY_ORDER.get(duplicate.severity, 99) < SEVERITY_ORDER.get(self.severity, 99):
            self.severity = duplicate.severity

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.finding_id,
            "title": self.title,
            "status": self.status,
            "type": self.finding_type,
            "severity": self.severity,
            "surface": self.surface,
            "github_issue": self.github_issue,
            "evidence": self.evidence,
            "impact": self.impact,
            "verification": self.verification,
            "fix_plan": self.fix_plan,
            "resolution_notes": self.resolution_notes,
        }


@dataclass
class FindingsDocument:
    summary: dict[str, str] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)

    def set_summary_defaults(self) -> None:
        for key in FINDING_SUMMARY_ORDER:
            self.summary.setdefault(key, "unknown")

    def upsert_finding(self, payload: dict[str, Any]) -> Finding:
        finding_id = payload.get("id") or payload.get("finding_id")
        if not finding_id:
            raise ValueError("Finding payload must include `id`.")
        existing = self.get_finding(finding_id)
        if existing is None:
            title = payload.get("title")
            if not title:
                raise ValueError(f"New finding {finding_id} must include `title`.")
            existing = Finding(finding_id=finding_id, title=str(title))
            self.findings.append(existing)
        existing.apply_update(payload)
        self.findings.sort(key=_finding_sort_key)
        return existing

    def merge_findings(self, canonical_id: str, duplicate_id: str) -> Finding:
        if canonical_id == duplicate_id:
            raise ValueError("Canonical and duplicate IDs must differ.")
        canonical = self.get_finding(canonical_id)
        duplicate = self.get_finding(duplicate_id)
        if canonical is None or duplicate is None:
            raise ValueError("Both canonical and duplicate findings must exist.")
        canonical.merge_from(duplicate)
        if f"Merged duplicate finding {duplicate_id}." not in canonical.resolution_notes:
            canonical.resolution_notes.append(f"Merged duplicate finding {duplicate_id}.")
        self.findings = [finding for finding in self.findings if finding.finding_id != duplicate_id]
        self.findings.sort(key=_finding_sort_key)
        return canonical

    def get_finding(self, finding_id: str) -> Finding | None:
        for finding in self.findings:
            if finding.finding_id == finding_id:
                return finding
        return None

    def build_fix_queue(self, statuses: list[str] | None = None) -> list[dict[str, Any]]:
        allowed_statuses = statuses or ["confirmed-open", "in-progress"]
        queue = [
            finding
            for finding in self.findings
            if finding.status in allowed_statuses
        ]
        queue.sort(
            key=lambda finding: (
                SEVERITY_ORDER.get(finding.severity, 99),
                TYPE_ORDER.get(finding.finding_type, 99),
                _finding_sort_key(finding),
            )
        )
        return [finding.to_dict() for finding in queue]

    def counts(self) -> dict[str, int]:
        counts = {
            "confirmed-open": 0,
            "in-progress": 0,
            "resolved": 0,
            "blocked": 0,
            "needs-context": 0,
        }
        for finding in self.findings:
            counts[finding.status] = counts.get(finding.status, 0) + 1
        return counts

    def final_state(self) -> str:
        counts = self.counts()
        open_count = counts.get("confirmed-open", 0) + counts.get("in-progress", 0)
        if open_count == 0 and counts.get("blocked", 0) == 0 and counts.get("needs-context", 0) == 0:
            return "no confirmed-open findings"
        if open_count == 0:
            return "no confirmed-open findings; blocked or needs-context items remain"
        return "confirmed findings remain"


@dataclass
class ReportDocument:
    summary: dict[str, str] = field(default_factory=dict)
    skills_run: list[dict[str, str]] = field(default_factory=list)
    findings: dict[str, int] = field(default_factory=dict)
    fix_queue: list[str] = field(default_factory=list)
    verification: list[str] = field(default_factory=list)
    issue_activity: dict[str, list[str]] = field(default_factory=lambda: {
        "Created": [],
        "Updated": [],
        "Closed": [],
    })
    remaining_items: list[str] = field(default_factory=list)

    def set_summary_defaults(self) -> None:
        defaults = {
            "Mode": "default",
            "Profile": "core",
            "Scope": "repo-wide",
            "Branch": "unknown",
            "Dirty worktree": "unknown",
            "GitHub issue sync": "unavailable",
            "Final state": "confirmed findings remain",
            "Updated at": "unknown",
        }
        for key in REPORT_SUMMARY_ORDER:
            self.summary.setdefault(key, defaults.get(key, "unknown"))

    def upsert_skill(self, skill: str, status: str, note: str | None = None) -> None:
        for item in self.skills_run:
            if item["name"] == skill:
                item["status"] = status
                item["note"] = note or ""
                return
        self.skills_run.append({"name": skill, "status": status, "note": note or ""})

    def append_unique(self, field_name: str, item: str) -> None:
        target = getattr(self, field_name)
        if item not in target:
            target.append(item)

    def add_issue_activity(self, action: str, issue_id: str) -> None:
        normalized = action.capitalize()
        self.issue_activity.setdefault(normalized, [])
        if issue_id not in self.issue_activity[normalized]:
            self.issue_activity[normalized].append(issue_id)


def _finding_sort_key(finding: Finding) -> tuple[str, int, str]:
    match = re.match(r"([A-Z]+)-(\d+)$", finding.finding_id)
    if match:
        return (match.group(1), int(match.group(2)), finding.finding_id)
    return ("ZZZ", 999999, finding.finding_id)


def _clean_list(items: list[str]) -> list[str]:
    cleaned = [item.strip() for item in items if item.strip()]
    if cleaned == [NONE_MARKER]:
        return []
    return cleaned


def _load_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def load_findings(path: str | Path) -> FindingsDocument:
    document = FindingsDocument()
    text = _load_text(Path(path))
    if not text.strip():
        document.set_summary_defaults()
        return document

    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if line == "## Summary":
            index += 1
            while index < len(lines) and lines[index].startswith("- "):
                key, value = _split_key_value(lines[index][2:])
                document.summary[key] = value
                index += 1
            continue

        match = re.match(r"^### ([A-Z]+-\d+) - (.+)$", line)
        if match:
            finding = Finding(finding_id=match.group(1), title=match.group(2))
            index += 1
            while index < len(lines):
                current = lines[index]
                if current.startswith("### "):
                    break
                if current.startswith("- Status: "):
                    finding.status = current.removeprefix("- Status: ").strip()
                elif current.startswith("- Type: "):
                    finding.finding_type = current.removeprefix("- Type: ").strip()
                elif current.startswith("- Severity: "):
                    finding.severity = current.removeprefix("- Severity: ").strip()
                elif current.startswith("- Surface: "):
                    finding.surface = current.removeprefix("- Surface: ").strip()
                elif current.startswith("- GitHub Issue: "):
                    finding.github_issue = current.removeprefix("- GitHub Issue: ").strip()
                else:
                    handled = False
                    for heading, attr in FINDING_LIST_FIELDS:
                        if current == f"- {heading}:":
                            items, index = _parse_nested_bullets(lines, index + 1)
                            setattr(finding, attr, _clean_list(items))
                            handled = True
                            break
                    if handled:
                        continue
                index += 1
            document.findings.append(finding)
            continue
        index += 1

    document.set_summary_defaults()
    document.findings.sort(key=_finding_sort_key)
    return document


def save_findings(path: str | Path, document: FindingsDocument) -> None:
    document.summary["Final state"] = document.final_state()
    document.set_summary_defaults()
    lines = ["# Project Audit Findings", "", "## Summary"]
    for key in FINDING_SUMMARY_ORDER:
        lines.append(f"- {key}: {document.summary.get(key, 'unknown')}")
    lines.append("")

    for finding in sorted(document.findings, key=_finding_sort_key):
        lines.extend(_render_finding(finding))
        lines.append("")

    Path(path).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _render_finding(finding: Finding) -> list[str]:
    lines = [
        f"### {finding.finding_id} - {finding.title}",
        f"- Status: {finding.status}",
        f"- Type: {finding.finding_type}",
        f"- Severity: {finding.severity}",
        f"- Surface: {finding.surface or NONE_MARKER}",
        f"- GitHub Issue: {finding.github_issue or NONE_MARKER}",
    ]
    for heading, attr in FINDING_LIST_FIELDS:
        lines.append(f"- {heading}:")
        values = getattr(finding, attr) or [NONE_MARKER]
        for item in values:
            lines.append(f"  - {item}")
    return lines


def load_report(path: str | Path) -> ReportDocument:
    document = ReportDocument()
    text = _load_text(Path(path))
    if not text.strip():
        document.set_summary_defaults()
        return document

    lines = text.splitlines()
    index = 0
    current_section = ""
    while index < len(lines):
        line = lines[index]
        if line.startswith("## "):
            current_section = line.removeprefix("## ").strip()
            index += 1
            continue

        if not line.startswith("- "):
            index += 1
            continue

        content = line[2:]
        if current_section == "Run Summary":
            key, value = _split_key_value(content)
            document.summary[key] = value
        elif current_section == "Skills Run":
            match = re.match(r"^([^:]+): ([^(]+?)(?: \((.+)\))?$", content)
            if match:
                document.skills_run.append(
                    {
                        "name": match.group(1).strip(),
                        "status": match.group(2).strip(),
                        "note": (match.group(3) or "").strip(),
                    }
                )
            else:
                document.skills_run.append({"name": content.strip(), "status": "completed", "note": ""})
        elif current_section == "Findings":
            key, value = _split_key_value(content)
            try:
                document.findings[key] = int(value)
            except ValueError:
                document.findings[key] = 0
        elif current_section == "Fix Queue":
            document.fix_queue.append(content.strip())
        elif current_section == "Verification":
            document.verification.append(content.strip())
        elif current_section == "Issue Activity":
            key, value = _split_key_value(content)
            items = [] if value == NONE_MARKER else [item.strip() for item in value.split(",") if item.strip()]
            document.issue_activity[key] = items
        elif current_section == "Remaining Items":
            document.remaining_items.append(content.strip())
        index += 1

    document.fix_queue = _clean_list(document.fix_queue)
    document.verification = _clean_list(document.verification)
    document.remaining_items = _clean_list(document.remaining_items)
    for key in ("Created", "Updated", "Closed"):
        document.issue_activity.setdefault(key, [])
    document.set_summary_defaults()
    return document


def save_report(path: str | Path, document: ReportDocument) -> None:
    document.set_summary_defaults()
    lines = ["# Full Test Suite Report", "", "## Run Summary"]
    for key in REPORT_SUMMARY_ORDER:
        lines.append(f"- {key}: {document.summary.get(key, 'unknown')}")

    lines.extend(["", "## Skills Run"])
    for skill in sorted(document.skills_run, key=lambda item: item["name"]):
        line = f"- {skill['name']}: {skill['status']}"
        if skill.get("note"):
            line += f" ({skill['note']})"
        lines.append(line)
    if not document.skills_run:
        lines.append(f"- {NONE_MARKER}")

    lines.extend(["", "## Findings"])
    for key in [
        "Confirmed-open findings",
        "In-progress findings",
        "Resolved findings",
        "Blocked findings",
        "Needs-context findings",
    ]:
        lines.append(f"- {key}: {document.findings.get(key, 0)}")

    lines.extend(["", "## Fix Queue"])
    for item in document.fix_queue or [NONE_MARKER]:
        lines.append(f"- {item}")

    lines.extend(["", "## Verification"])
    for item in document.verification or [NONE_MARKER]:
        lines.append(f"- {item}")

    lines.extend(["", "## Issue Activity"])
    for key in ("Created", "Updated", "Closed"):
        items = ", ".join(document.issue_activity.get(key, [])) or NONE_MARKER
        lines.append(f"- {key}: {items}")

    lines.extend(["", "## Remaining Items"])
    for item in document.remaining_items or [NONE_MARKER]:
        lines.append(f"- {item}")

    Path(path).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def sync_report_from_findings(report: ReportDocument, findings: FindingsDocument, updated_at: str | None = None) -> ReportDocument:
    counts = findings.counts()
    report.findings = {
        "Confirmed-open findings": counts.get("confirmed-open", 0),
        "In-progress findings": counts.get("in-progress", 0),
        "Resolved findings": counts.get("resolved", 0),
        "Blocked findings": counts.get("blocked", 0),
        "Needs-context findings": counts.get("needs-context", 0),
    }
    report.fix_queue = [
        f"{item['id']} [{item['severity']}/{item['type']}] - {item['title']}"
        for item in findings.build_fix_queue(["confirmed-open", "in-progress"])
    ]
    report.remaining_items = [
        f"{finding.finding_id} ({finding.status}) - {finding.title}"
        for finding in findings.findings
        if finding.status in {"confirmed-open", "in-progress", "blocked", "needs-context"}
    ]
    report.summary["Final state"] = findings.final_state()
    if updated_at:
        report.summary["Updated at"] = updated_at
    return report


def _parse_nested_bullets(lines: list[str], index: int) -> tuple[list[str], int]:
    items: list[str] = []
    while index < len(lines) and lines[index].startswith("  - "):
        items.append(lines[index][4:].strip())
        index += 1
    return items, index


def _split_key_value(text: str) -> tuple[str, str]:
    key, value = text.split(":", 1)
    return key.strip(), value.strip()


def _load_payload(args: argparse.Namespace) -> dict[str, Any]:
    if getattr(args, "payload", None):
        return json.loads(args.payload)
    payload_file = getattr(args, "payload_file", None)
    if payload_file:
        return json.loads(Path(payload_file).read_text(encoding="utf-8"))
    raise ValueError("Provide either --payload or --payload-file.")


def _print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_findings = subparsers.add_parser("init-findings")
    init_findings.add_argument("--path", required=True)
    init_findings.add_argument("--audit-date", required=True)
    init_findings.add_argument("--scope", required=True)
    init_findings.add_argument("--branch", required=True)
    init_findings.add_argument("--github-sync", required=True)
    init_findings.add_argument("--final-state", default="confirmed findings remain")

    upsert_finding = subparsers.add_parser("upsert-finding")
    upsert_finding.add_argument("--path", required=True)
    upsert_finding.add_argument("--payload")
    upsert_finding.add_argument("--payload-file")

    merge_finding = subparsers.add_parser("merge-findings")
    merge_finding.add_argument("--path", required=True)
    merge_finding.add_argument("--canonical-id", required=True)
    merge_finding.add_argument("--duplicate-id", required=True)

    fix_queue = subparsers.add_parser("build-fix-queue")
    fix_queue.add_argument("--path", required=True)
    fix_queue.add_argument("--statuses", default="confirmed-open,in-progress")

    show_findings = subparsers.add_parser("show-findings")
    show_findings.add_argument("--path", required=True)

    init_report = subparsers.add_parser("init-report")
    init_report.add_argument("--path", required=True)
    init_report.add_argument("--mode", required=True)
    init_report.add_argument("--profile", required=True)
    init_report.add_argument("--scope", required=True)
    init_report.add_argument("--branch", required=True)
    init_report.add_argument("--dirty-worktree", required=True)
    init_report.add_argument("--github-sync", required=True)
    init_report.add_argument("--updated-at", required=True)
    init_report.add_argument("--skills", default="")

    update_report = subparsers.add_parser("update-report")
    update_report.add_argument("--path", required=True)
    update_report.add_argument("--payload")
    update_report.add_argument("--payload-file")

    sync_report = subparsers.add_parser("sync-report")
    sync_report.add_argument("--report-path", required=True)
    sync_report.add_argument("--findings-path", required=True)
    sync_report.add_argument("--updated-at", required=True)

    show_report = subparsers.add_parser("show-report")
    show_report.add_argument("--path", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init-findings":
        document = load_findings(args.path)
        document.summary.update(
            {
                "Audit date": args.audit_date,
                "Scope": args.scope,
                "Branch": args.branch,
                "GitHub issue sync": args.github_sync,
                "Final state": args.final_state,
            }
        )
        save_findings(args.path, document)
        _print_json({"path": args.path, "summary": document.summary, "findings": len(document.findings)})
        return 0

    if args.command == "upsert-finding":
        document = load_findings(args.path)
        finding = document.upsert_finding(_load_payload(args))
        save_findings(args.path, document)
        _print_json({"path": args.path, "finding": finding.to_dict(), "counts": document.counts()})
        return 0

    if args.command == "merge-findings":
        document = load_findings(args.path)
        finding = document.merge_findings(args.canonical_id, args.duplicate_id)
        save_findings(args.path, document)
        _print_json({"path": args.path, "finding": finding.to_dict(), "counts": document.counts()})
        return 0

    if args.command == "build-fix-queue":
        document = load_findings(args.path)
        statuses = [item.strip() for item in args.statuses.split(",") if item.strip()]
        queue = document.build_fix_queue(statuses)
        _print_json({"path": args.path, "queue": queue})
        return 0

    if args.command == "show-findings":
        document = load_findings(args.path)
        _print_json({"summary": document.summary, "findings": [finding.to_dict() for finding in document.findings]})
        return 0

    if args.command == "init-report":
        document = load_report(args.path)
        document.summary.update(
            {
                "Mode": args.mode,
                "Profile": args.profile,
                "Scope": args.scope,
                "Branch": args.branch,
                "Dirty worktree": args.dirty_worktree,
                "GitHub issue sync": args.github_sync,
                "Updated at": args.updated_at,
            }
        )
        skills = [skill.strip() for skill in args.skills.split(",") if skill.strip()]
        for skill in skills:
            document.upsert_skill(skill, "pending")
        save_report(args.path, document)
        _print_json({"path": args.path, "summary": document.summary, "skills": document.skills_run})
        return 0

    if args.command == "update-report":
        document = load_report(args.path)
        payload = _load_payload(args)
        summary = payload.get("summary", {})
        document.summary.update({str(key): str(value) for key, value in summary.items()})
        for skill in payload.get("skills_run", []):
            document.upsert_skill(skill["name"], skill["status"], skill.get("note"))
        for item in payload.get("verification", []):
            document.append_unique("verification", str(item))
        for item in payload.get("fix_queue", []):
            if item not in document.fix_queue:
                document.fix_queue.append(str(item))
        for item in payload.get("remaining_items", []):
            if item not in document.remaining_items:
                document.remaining_items.append(str(item))
        issue_activity = payload.get("issue_activity", {})
        for action, issues in issue_activity.items():
            for issue in issues:
                document.add_issue_activity(action, str(issue))
        findings = payload.get("findings", {})
        if findings:
            document.findings.update({str(key): int(value) for key, value in findings.items()})
        save_report(args.path, document)
        _print_json({"path": args.path, "summary": document.summary})
        return 0

    if args.command == "sync-report":
        report = load_report(args.report_path)
        findings = load_findings(args.findings_path)
        sync_report_from_findings(report, findings, args.updated_at)
        save_report(args.report_path, report)
        _print_json({"report_path": args.report_path, "final_state": report.summary["Final state"]})
        return 0

    if args.command == "show-report":
        report = load_report(args.path)
        _print_json(
            {
                "summary": report.summary,
                "skills_run": report.skills_run,
                "findings": report.findings,
                "fix_queue": report.fix_queue,
                "verification": report.verification,
                "issue_activity": report.issue_activity,
                "remaining_items": report.remaining_items,
            }
        )
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
