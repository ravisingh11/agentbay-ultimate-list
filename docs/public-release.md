# Publishing AgentBay

[Home](../README.md) · [Maintenance](maintenance.md) · [Installer checks](installer-maintenance.md) · [Security](../SECURITY.md)

This procedure is for maintainers who already have a repository checkout. End users install the skill folder using the README quick start; they do not need to check out this catalogue. These preparation commands do not change repository visibility.

## Validate the source revision

Use a clean checkout of the reviewed commit. Record `git rev-parse HEAD`, confirm that `git status --porcelain` is empty, and run:

```sh
python3 scripts/catalog.py check
python3 scripts/installer.py check
python3 scripts/example_bundle.py check
python3 scripts/skill_bundle.py check
python3 -m unittest discover -s tests -v
```

Run the offline regeneration commands from CI and confirm that they create no diff or untracked outputs. The adopted [main-push source checks](guardrails.md#two-events-two-tested-revisions), including `validate` and `installer-install`, must pass on the exact candidate. Main-push checks are inspected directly in Actions; the Proof scorecard remains PR-specific. Record the source skill's SHA-256 and the example ZIP checksum. The MIT license covers this repository's original material; it does not relicense linked skills or certify their compatibility.

For instruction changes, also run the documented natural discovery and representative use checks:

```sh
python3 scripts/smoke_installer.py --discovery-only --output ../agentbay-discovery-release-check
python3 scripts/smoke_installer.py --scenario cloudflare --output ../agentbay-cloudflare-release-check
```

Choose new evidence directories and follow the runtime/authentication prerequisites in [installer maintenance](installer-maintenance.md#reproduce-the-codex-first-use-test). CI tests file installation and native discovery; it does not run an authenticated model task. Keep receipts and raw execution output outside the checkout; include the tested revision, hashes and any failed attempts in the release review.

## Verify the real GitHub route

In a disposable Git project, use the README install command with `main` replaced by the full candidate commit. Confirm the installed `SKILL.md` bytes against that committed source, inspect the source revision in `skills-lock.json`, and check Codex discovery. This is separate from CI's staged local-source substitution.

For desktop support, complete the [manual desktop journey](cloudflare-first-use.md#desktop-verification) and record the app version and result. CLI/native-registry success does not establish a desktop UI test. Do not bypass an automation tool's access refusal.

The maintained context-check helper verifies one pinned catalogue snapshot against that commit's manifest. Before public release, authorized maintainers can use:

```sh
python3 scripts/catalogue_context.py --access github --revision FULL_CANDIDATE_COMMIT --output ../agentbay-private-context-check
```

`source.json` records the revision, retrieval mode and hashes. The command fetches metadata only, writes into a new directory, preserves existing snapshots, and never installs or executes a listed skill. Its public mode cannot invoke GitHub CLI. Source checksums establish consistency with that commit, not independent trust in the content.

## Align published entry points

Confirm the root README, direct skill link, download links and issue forms work at the chosen revision. There is one maintained installer MD. If publishing its website copy as part of this release, stage the approved commit and verify the exact deployed bytes and `release.json` using [the publication procedure](installer-maintenance.md#publish-an-approved-revision). Do not publish a working-tree candidate or compare an older release against an unrelated new `main` commit.

The website's existing installer may intentionally be an older, separately identified release. Record that fact instead of implying all copies are current. A website design update is not a catalogue or installer release.

## Owner publication decision

Review the candidate tree and reachable Git history for unintended data and credentials; keep raw scan output, authentication files and execution traces outside Git. Check the repository description, homepage, MIT detection, contribution/conduct/security files, enabled issues and maintainer contact. Verify the [active hardening settings](repository-hardening.md), all eleven required check names and owner-review rules rather than assuming a passing workflow protects `main`.

Repository visibility is an explicit owner decision after review. Do not change it as a side effect of merging, running checks or preparing a release. After the owner makes the chosen revision public, immediately verify it from a signed-out browser and run:

```sh
python3 scripts/catalogue_context.py --access public --revision FULL_PUBLIC_COMMIT --output ../agentbay-anonymous-context-check
```

This mode uses public HTTPS only and skips the GitHub commit API when a full commit is provided. It must fetch and verify both context files without GitHub credentials. Then test the exact README GitHub installation command in a clean environment without GitHub authentication. An anonymous 404 while the repository is private is expected; it is not a passed public-access check.

Check public issue forms and private vulnerability reporting settings after the visibility change, since feature availability can depend on visibility and plan. The [security policy](../SECURITY.md) provides a direct private contact even when GitHub's reporting feature is unavailable. If public access fails, stop announcing the release and correct access/distribution before calling it usable.

## Record the result

Record the source commit, clean-tree status, test/tool versions, source/download hashes, installed-file and native-discovery results, representative task result and public-access result. Separate observations from assumptions. Any unperformed desktop or anonymous check remains explicitly unverified; do not substitute a merge, workflow success or model self-report for it. A version tag or GitHub release is a separate maintainer action, not part of the checks above.
