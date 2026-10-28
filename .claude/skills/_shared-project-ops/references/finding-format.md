# Shared Finding Format

Use `project-audit-findings.md` as the local source of truth for project-ops skills unless the user specifies another path.
When deterministic updates matter, prefer `../scripts/project_ops_state.py` instead of editing the log by hand.

## Header

```md
# Project Audit Findings

## Summary
- Audit date: 2026-03-12 10:00 EDT
- Scope: [short scope]
- Branch: [branch]
- GitHub issue sync: available | unavailable | disabled
- Final state: no confirmed-open findings | confirmed findings remain
```

## One section per finding

```md
### BUG-001 - Title
- Status: confirmed-open | in-progress | resolved | blocked | needs-context
- Type: bug | security | docs | api-contract | health | release | testing | dependency | observability | migration | frontend
- Severity: critical | high | medium | low
- Surface: [short subsystem or path]
- GitHub Issue: #123 | none
- Evidence:
  - [code reference, repro note, test trace, or static proof]
- Impact:
  - [user, security, reliability, or maintenance impact]
- Verification:
  - [test command, check, or manual reasoning]
- Fix Plan:
  - [minimal intended change]
- Resolution Notes:
  - [only when resolved or partially resolved]
```

## Rules

- Promote only verified findings into the log.
- Update status in place instead of duplicating entries.
- Use stable prefixes by skill family when possible: `OPS`, `BUG`, `SEC`, `DOC`, `API`, `REL`, `TEST`, `DEP`, `OBS`, `CFG`, `DB`, `UI`.
- If multiple skills identify the same root cause, merge them into one canonical finding and append evidence.
- Prefer the shared state utility for upserts and merges:
  - `python3 ../scripts/project_ops_state.py upsert-finding --path project-audit-findings.md --payload '{"id":"BUG-001","title":"Example","type":"bug"}'`
  - `python3 ../scripts/project_ops_state.py merge-findings --path project-audit-findings.md --canonical-id BUG-001 --duplicate-id SEC-001`
