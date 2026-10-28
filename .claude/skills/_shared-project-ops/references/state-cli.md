# State CLI

Use `../scripts/project_ops_state.py` to update bundle artifacts deterministically.

## Findings log

- Initialize or refresh the summary header:
  - `python3 ../scripts/project_ops_state.py init-findings --path project-audit-findings.md --audit-date "2026-03-12 10:00 EDT" --scope "repo-wide" --branch codex/example --github-sync available`
- Upsert a confirmed finding:
  - `python3 ../scripts/project_ops_state.py upsert-finding --path project-audit-findings.md --payload '{"id":"BUG-001","title":"Example","type":"bug","severity":"high","surface":"App/Services"}'`
- Merge duplicates after consolidating a root cause:
  - `python3 ../scripts/project_ops_state.py merge-findings --path project-audit-findings.md --canonical-id BUG-001 --duplicate-id SEC-001`
- Build the current fix queue:
  - `python3 ../scripts/project_ops_state.py build-fix-queue --path project-audit-findings.md`

## Execution report

- Initialize the report:
  - `python3 ../scripts/project_ops_state.py init-report --path full-test-suite-report.md --mode default --profile core --scope "repo-wide" --branch codex/example --dirty-worktree yes --github-sync available --updated-at "2026-03-12 10:00 EDT" --skills "project-health-check,bug-hunter,security-audit-lite,api-contract-auditor,docs-sync,issue-operator"`
- Append verification or issue activity:
  - `python3 ../scripts/project_ops_state.py update-report --path full-test-suite-report.md --payload '{"verification":["xcodebuild ... passed"],"issue_activity":{"Updated":["#8"]}}'`
- Sync counts, queue, final state, and remaining items from the findings log:
  - `python3 ../scripts/project_ops_state.py sync-report --report-path full-test-suite-report.md --findings-path project-audit-findings.md --updated-at "2026-03-12 10:30 EDT"`
