# Repository protections

[Home](../README.md) · [Contribute](../CONTRIBUTING.md) · [Guardrails](guardrails.md) · [Security reporting](../SECURITY.md)

Verified through GitHub's settings APIs on October 28, 2026. The public repository uses the live [AI Software Toolkit settings](https://github.com/ravisingh11/ai-software-toolkit/rules) as its baseline. Configuration is enforced by GitHub; this document records it rather than implementing it.

## Protect the default branch

The active [default-branch ruleset](https://github.com/ravisingh11/agentbay-ultimate-list/rules/26075107) requires a pull request and resolved review threads. It prevents force pushes and branch deletion, including for the owner, with no bypass actors. Allowed merge methods are squash and rebase; automatic merging is disabled and merged branches are deleted automatically.

Eleven existing check-run names are required from the GitHub Actions integration (app ID `15368`):

| Required check | Purpose |
| --- | --- |
| `Validate / repository` | Repository contract |
| `Validate / docs` | Documentation relationships |
| `Validate / ground truth` | Declared reference documents |
| `Validate / standards source` | Pinned toolkit source |
| `Build` | Deterministic generated outputs and bundles |
| `Unit Tests` | Maintenance behavior |
| `Format and Lint` | Configured whitespace and syntax checks |
| `validate` | Catalogue, bundles and offline regeneration |
| `installer-install` | Credential-free installation and native discovery |
| `Semgrep CE` | Configured static analysis |
| `Gitleaks` | Secret policy regression and reachable-history scan |

These names were read from successful runs on the initial publication commit, `bda94788d045af53acd2df5c1e4a4d9048a358a0`. Future PRs need results for their own head revision. Like the Toolkit baseline, the rules do not require updating a branch after every unrelated base change. The Toolkit's migration check is not copied: AgentBay's catalogue repository has no migration surface or active producer. The advisory Proof scorecard is not a required merge check.

The separate [maintainer-review ruleset](https://github.com/ravisingh11/agentbay-ultimate-list/rules/26075108) requires one code-owner approval and dismisses stale approvals when new commits arrive. It also requires an extra approval for unattributed changes. The owner has the same **PR-only bypass of the review ruleset** as in Toolkit, allowing owner-authored work to proceed without self-approval. That exception does not bypass the independent required checks, force-push prohibition or deletion protection. Agents still need the owner's explicit authorization to merge.

## Restrict automation and protect reports

- Actions tokens default to read-only; Actions cannot approve PR reviews.
- Every outside contributor requires approval before fork-PR workflows execute.
- Only the Toolkit allowlist plus `actions/setup-python@*` is allowed. The extra action is needed by AgentBay's existing catalogue workflow. All action references must use a full commit SHA; wildcard permission does not permit floating versions.
- Secret scanning and secret push protection are enabled. Dependency vulnerability alerts and automated security-fix PRs are enabled. A feature being enabled is not evidence that a scan has completed or that every dependency is safe.
- [Private vulnerability reporting](https://github.com/ravisingh11/agentbay-ultimate-list/security/advisories/new) is enabled; use it rather than posting sensitive details in an issue.

No scanner policy, credential, paid integration or deployment permission was copied from Toolkit. GitHub visibility was already public and was not changed by this work.

## Independently verify

An authorized maintainer can inspect the settings without modifying them:

```sh
gh api repos/ravisingh11/agentbay-ultimate-list/rulesets/26075107
gh api repos/ravisingh11/agentbay-ultimate-list/rulesets/26075108
gh api repos/ravisingh11/agentbay-ultimate-list/actions/permissions
gh api repos/ravisingh11/agentbay-ultimate-list/actions/permissions/selected-actions
gh api repos/ravisingh11/agentbay-ultimate-list/actions/permissions/workflow
gh api repos/ravisingh11/agentbay-ultimate-list/actions/permissions/fork-pr-contributor-approval
gh api repos/ravisingh11/agentbay-ultimate-list/private-vulnerability-reporting
gh api repos/ravisingh11/agentbay-ultimate-list/vulnerability-alerts
gh api repos/ravisingh11/agentbay-ultimate-list --jq '{visibility,security_and_analysis,allow_merge_commit,allow_squash_merge,allow_rebase_merge,delete_branch_on_merge,allow_auto_merge}'
```

The alerts endpoint returns HTTP 204 when enabled. Check the PR's actual check runs and merge requirements separately; a local test does not prove GitHub enforcement. Recheck these settings after repository recreation, plan changes or workflow renaming. Required names must follow real producers, not missing, skipped or renamed jobs. Changes to visibility, permissions or rules need explicit owner authorization.
