# Execution Report Format

Use `full-test-suite-report.md` for bundle runs.
When deterministic updates matter, prefer `../scripts/project_ops_state.py` and `../../full-test-suite/scripts/full_test_suite_runner.py`.

```md
# Full Test Suite Report

## Run Summary
- Mode: default | scan-only | rerun-impacted | resume
- Profile: core | pre-release | deep-audit
- Scope: [short scope]
- Branch: [branch]
- Dirty worktree: yes | no
- GitHub issue sync: available | unavailable | disabled
- Final state: no confirmed-open findings | findings remain
- Updated at: 2026-03-12 10:00 EDT

## Skills Run
- project-health-check: pending | completed | skipped | blocked
- bug-hunter: pending | completed | skipped | blocked
- security-audit-lite: pending | completed | skipped | blocked
- api-contract-auditor: pending | completed | skipped | blocked
- docs-sync: pending | completed | skipped | blocked
- issue-operator: pending | completed | skipped | blocked

## Findings
- Confirmed-open findings: [count]
- In-progress findings: [count]
- Resolved findings: [count]
- Blocked findings: [count]
- Needs-context findings: [count]

## Fix Queue
- BUG-001 [high/bug] - Title
- SEC-001 [critical/security] - Title

## Verification
- [commands and outcomes]

## Issue Activity
- Created: [ids]
- Updated: [ids]
- Closed: [ids]

## Remaining Items
- [blocked or needs-context only]
```

Suggested deterministic flow:

1. `python3 ../../full-test-suite/scripts/full_test_suite_runner.py init --repo-root . --findings-path project-audit-findings.md --report-path full-test-suite-report.md --scope "repo-wide" --profile core`
2. Run the skills in profile order and record each completion with `record-skill`.
3. Upsert findings with `project_ops_state.py upsert-finding`.
4. Build and refresh the queue with `plan-fixes`.
5. Finalize with `python3 ../../full-test-suite/scripts/full_test_suite_runner.py finalize --repo-root . --findings-path project-audit-findings.md --report-path full-test-suite-report.md`
