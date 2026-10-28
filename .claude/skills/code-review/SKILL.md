---
name: code-review
description: "Review code changes for correctness, regressions, security, test gaps, and operational risk. Use when reviewing a local diff, pull request, recently merged change, or requested implementation before release."
---

# Code Review

Use this skill when reviewing a local diff, pull request, recently merged change, or requested implementation before release.

## Focus

- Correctness bugs and behavioral regressions.
- Security, privacy, auth, permission, and data-exposure risks.
- API, schema, serialization, and client compatibility drift.
- Migration and rollback safety.
- Missing or weak tests for changed behavior.
- Operational gaps: logging, deploy safety, smoke tests, and rollback.

## Method

1. Inspect the changed files and surrounding code.
2. Trace user-visible behavior and data flow.
3. Check whether tests cover the risky paths.
4. Prefer concrete file/line findings over broad commentary.
5. Do not suggest cosmetic rewrites unless they hide a real risk.

## Decision Rules

- Findings must be evidence-backed and tied to file or behavior references.
- Do not promote speculative concerns unless the failure mode is concrete.
- Separate real defects from verification gaps.
- Preserve unrelated user changes in dirty worktrees.

## Verification

- Prefer running focused tests for changed code when feasible.
- If tests are unavailable, explain the static evidence and residual risk.
- Record commands not run when they would materially affect confidence.

## Output

Findings first, ordered by severity:

```text
Findings
- severity: file:line - issue and impact

Questions
- assumptions that affect correctness

Verification Gaps
- checks not run or coverage missing
```
