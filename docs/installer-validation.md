# Installer verification

[Install by app](install.md) · [Run the checks](installer-maintenance.md) · [Publication procedure](public-release.md)

**Observed on 2026-10-27, while this repository was private.** The repository was recreated with clean Git history on 2026-10-28. The earlier install/use observations identify source bytes below; their retired commit IDs are not references in the recreated repository. Fresh CI runs validate its new initial commit separately. File installation, native discovery and successful task execution are separate checks. The complete Codex CLI Cloudflare journey passed; desktop and Claude limits remain below. These results cover the tested versions and sources, not every app or listed skill.

## Tested sources

| Item | Revision or SHA-256 |
| --- | --- |
| Tested catalogue SHA-256 | `add645be69979aeb280817f78fcf847d915dcbf4a2f0bacb4c244875784c96e7` |
| Tested publisher registry SHA-256 | `736332c4e4173bee01540bb8a0b6209f227f686df550f44c1ad6007e5f6708f3` |
| Maintained `SKILL.md` (13,856 bytes) | `c9795b56df4e31f0c2803f3560727a06908f5f9ce4bd804dce764c3ac66579eb` |
| Claude upload ZIP | `ced3e47c38a72762b77463d92fdfbd00e7936be82a3f624f95ee10b6268666b2` |
| Cloudflare example ZIP | `a9f34d446be404e28849717a7735d8e7041fb60cd658b8d73385ddeaa49c3aeb` |

The source, website download, installed project MD and Claude desktop's exported MD had identical bytes. Claude repackages its export as a plugin ZIP; equality applies to the inner `SKILL.md`, not that exported archive.

There is one maintained [source MD](../skills/agentbay-skill-installer/SKILL.md). Repository ZIPs are generated from it. The website has separately published [release metadata](https://agentbay.io/skills/agentbay-skill-installer/release.json); a newer documentation commit does not publish or alter that installer. Use the [publication procedure](installer-maintenance.md#publish-an-approved-revision) to verify deployed bytes against the release's source commit.

## Observed results

| Journey | Result and evidence | Limit |
| --- | --- | --- |
| Private GitHub quick start | **Passed.** The README command, pinned to the tested source revision, installed the source unchanged in a new project. `skills-lock.json` recorded that commit. Codex's native `skills/list` returned exactly one enabled project-scoped AgentBay entry at the expected path. | Used existing authorized host GitHub access; this was not an anonymous or globally clean host. |
| Both-agent installer script | **Passed.** `AGENTBAY_REF` pinned to the tested source revision, `install.sh both` created Codex and Claude Code bindings to the same source. A repeat exited 1 with an overwrite refusal; all existing project files stayed unchanged. | File installation alone does not prove either agent used the skill. |
| Authenticated catalogue retrieval | **Passed.** `catalogue_context.py --access github` fetched the catalogue, publisher registry and manifest at the same tested revision and verified their checksums. | Access was tested on the host, separately from the model container. |
| Codex natural discovery | **Passed: 15/15 acceptance checks.** A clean container installed the published website download and the staged repository package unchanged. Native discovery and the natural “with AgentBay” prompt loaded the installer, searched the pinned catalogue and read the publisher registry. A discovery-only request installed no task skills and edited no application files. | The container used a read-only catalogue snapshot and staged local package, not private GitHub credentials. The real GitHub route was tested separately above. |
| Codex Cloudflare install and use | **Passed: 40/40 acceptance checks.** AgentBay chose official `workers-best-practices`, installed it only in the project, read its instructions and references, reported catalogue provenance, fixed the Worker and passed tests plus actual local HTTP checks. | Local fixture only; no Cloudflare credentials or remote deployment. |
| Codex desktop | **Blocked.** The desktop automation tool refused access to Codex. | CLI/app-server discovery is not a passed Skills-view or desktop-chat check. No bypass was attempted. |
| Claude Code | **Installation and native recognition passed.** Version 2.1.312 startup listed AgentBay in both native `skills` and `slash_commands` metadata. | Task execution stopped because Claude Code was not signed in. This is not a completed use test. |
| Claude desktop | **Upload, enablement and source inspection passed.** Version 3.6556.2 accepted the maintained ZIP, enabled AgentBay, displayed its instructions and exported an identical inner MD. A fresh task visibly read AgentBay's instructions. | The initial task could not access the private catalogue: `gh` was absent, anonymous GitHub API access was rate-limited and the public finder did not resolve in that chat runtime. It disclosed a direct HTML review without installing a task skill; that fallback is not a passed install-and-use journey. |

Codex's clean runs used Node.js **22.23.4**, Codex CLI **0.163.0**, Skills CLI **1.7.4**, and Wrangler **4.153.0** for the Cloudflare fixture. The separate authenticated host install used Node.js **26.5.1**. Claude Code was installed in a disposable prefix, with no global skill or CLI installation.

The [Claude desktop screenshot in the install guide](install.md#claude-desktop-app) shows the enabled switch and actual `SKILL.md` inspection view. It illustrates upload/enablement, not catalogue access or a completed task.

### What the Cloudflare pass establishes

The selected catalogue ID was `ce90dd94-98d3-5123-8c26-4f85ef477e78`. The installed [Cloudflare skill](https://github.com/cloudflare/skills/blob/86505e44f87d801aa1864a3c4109e9a8ae5c409f/skills/workers-best-practices/SKILL.md) matched upstream revision `86505e44f87d801aa1864a3c4109e9a8ae5c409f`. Its `references/configuration.md`, `references/runtime-patterns.md` and `references/platform-apis.md` were independently checked against that revision.

Before the fix, `/hello` without a name returned 500 and one of three tests failed. After changing only `src/index.js` among application files, all three tests passed and the real local endpoint returned 200 with `{"message":"Hello, WORLD!"}`. The named greeting and 404 route stayed correct. Tests, package files and Wrangler configuration remained unchanged; local packaging also passed. Native discovery then showed both AgentBay and the upstream skill in project scope.

### Claude desktop: explicit public-source recovery

After the initial access failure, a separate follow-up supplied the official public [Vercel `web-design-guidelines` source](https://github.com/vercel-labs/agent-skills/blob/1a2c79d4e6c4a2283dc2c614b6538cbe1ed5ca62/skills/web-design-guidelines/SKILL.md) at revision `1a2c79d4e6c4a2283dc2c614b6538cbe1ed5ca62`. Host-side GitHub metadata verified that repository as public, active and not disabled. No private catalogue snapshot was uploaded.

**This recovery passed installation and explicit instruction use.** The visible tool trace showed HTTP 200 for the actual MD, a Skills CLI 1.7.4 installation at that revision, and an installed-file SHA-256 of `f4647ca866a3accf763777f83e7682954f0187cd6bea7eea0399796652414e8f`, matching the independently fetched host source. The agent read the instructions and fetched their [referenced guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md) with HTTP 200. That mutable reference returned 191 lines with SHA-256 `d246b026f4f29b5823a9cc857f9edf3d2507002e055e32040cadeaf3b38e0234`; it is not part of the pinned skill commit.

The final review identified the missing input label on line 3, unnamed icon button on line 4 and missing image alternative text on line 5 of the synthetic HTML. It disclosed that the source was supplied explicitly and the private catalogue was not searched. The hosted runtime used Node.js 22.22.2 and npm 10.9.7. Installation and use were confined to that chat's temporary workspace; persistent desktop discovery of the upstream task skill was not established. A Skills CLI listing is not proof of native app discovery.

To repeat this recovery, upload/enable AgentBay and start a fresh chat: “Find a skill for reviewing HTML accessibility with AgentBay. Report catalogue/tool/account readiness. Install and use one official skill if supported. Review only this synthetic HTML with line numbers; do not edit it, change credentials or deploy.” Use this exact six-line fixture:

```html
<!doctype html>
<html lang="en"><head><title>Contact demo</title></head><body>
<input type="email" placeholder="Email">
<button><svg aria-hidden="true"></svg></button>
<img src="hero.png">
</body></html>
```

If catalogue access is unavailable, supply the pinned Vercel source above. Ask AgentBay to fetch/read that MD and its referenced guidelines, install only in the temporary workspace, compare installed/source hashes and review the same unchanged HTML. Require an explicit catalogue-access disclosure and the three line-specific findings. Record the guidelines' current hash separately; if retrieval or installation fails, retain the failure instead of counting a generic review as skill use.

## Checks still requiring an app session

- **Codex desktop:** open the installed project, confirm AgentBay in Skills and complete the [desktop Cloudflare journey](cloudflare-first-use.md#desktop-verification) in a fresh chat. Record the app version and actual tests/HTTP results.
- **Claude Code:** use an account with existing access, start in the installed project and complete the [HTML example](using-skills.md#first-worked-example). Native recognition is already observed; task execution is still unverified.
- **Claude desktop:** complete repository-curated matching with authorized catalogue access in the chat runtime, then inspect/install/use a selected upstream skill. Upload success does not make the private catalogue accessible. Do not upload private snapshots or credentials to another service without authorization.
- **After explicit publication:** test signed-out links, an anonymous GitHub installation and [public catalogue retrieval](public-release.md#owner-publication-decision). A private-repository 404 is expected now and cannot count as a public-access pass.

## Reproduce results

For a fresh run, choose a reviewed commit in the recreated repository, record its full SHA with `git rev-parse HEAD`, and use a clean checkout plus a new disposable project/output directory for each run. Keep raw traces, account state, credentials and catalogue snapshots outside Git. A model-backed run needs existing account access and consumes its normal allowance.

1. Run the offline source, bundle, catalogue and unit checks in the [publication procedure](public-release.md#validate-the-source-revision). Record that clean commit and compare source/download hashes with the observations above.
2. Follow [the real GitHub route](public-release.md#verify-the-real-github-route): replace `main` in the README install command with the full reviewed commit selected for that run. Compare the installed MD byte for byte, inspect the lock's revision, and independently query native discovery. Fetch context with `catalogue_context.py --access github` at that same commit.
3. Follow [the isolated Codex smoke instructions](installer-maintenance.md#reproduce-the-codex-first-use-test), running `--discovery-only` and `--scenario cloudflare` into separate new output directories. Record the runtime versions, `receipt.json` checks and any failed attempts. Both runs must begin with a clean skill baseline; discovery-only must not install a task skill. The Cloudflare run must verify the failure before the fix and tests/HTTP behavior afterward.
4. Repeat the [per-app installation steps](install.md) for Claude Code and desktop. Record installation, native recognition, source inspection, catalogue access and task execution separately. For desktop upload, download the installed skill and compare its inner MD with the source; do not compare repackaged ZIP bytes.

Model selection and upstream repositories can change. A new run may choose another suitable skill or fail a previously passing check; retain that outcome rather than claiming this dated result applies automatically. CI checks deterministic sources, bundles and credential-free installation/discovery. It does not replace authenticated model tasks or app sessions.

## Public repository distribution check — October 28, 2026

After the repository became public, a fresh disposable Git project installed AgentBay from the real GitHub skill-folder URL pinned to `bda94788d045af53acd2df5c1e4a4d9048a358a0`, using Skills CLI 1.7.4 with `--agent codex claude-code --yes`. Git credential helpers and interactive prompts were disabled, and GitHub token environment variables were removed. Both project paths contained the maintained MD unchanged: SHA-256 `c9795b56df4e31f0c2803f3560727a06908f5f9ce4bd804dce764c3ac66579eb`.

The maintained context helper also fetched the catalogue, provider registry and manifest through anonymous HTTPS at that revision and verified both recorded input hashes. No GitHub sign-in or full repository checkout was needed. These checks establish public distribution and installed bytes; no new model task or desktop UI result is claimed. The app-specific results and deferred Claude Code execution above remain separate.

Reproduce with the [real GitHub route procedure](public-release.md#verify-the-real-github-route), the README command pinned to that full commit and `scripts/catalogue_context.py --access public --revision bda94788d045af53acd2df5c1e4a4d9048a358a0 --output ../agentbay-public-context-check`. Use a new output directory. Never include credentials or raw app traces in a contribution.

## Task matching and scope regression checks

For the input “Excel to PDF”, require inspection of the actual converter instructions and prerequisites. A PDF-to-Excel or Excel-to-Markdown match is not a successful recommendation. Check that AgentBay searches its repository catalogue even when no conversion skill is installed; catalogue access failures must remain visible. An unavailable connector must be reported before task execution.

Project-scoped installation remains the default. Check Codex native discovery for the package `agentbay-skill-installer` with display name **AgentBay**. An explicit user-wide install may use `--global`; do not silently add a second installation to fix a wrong-project chat. File parity, native discovery and task execution are distinct outcomes. See PR evidence for the exact source hash and checks performed on a candidate; these criteria alone are not a new desktop or model-backed pass.

### October 29: native Codex first-use regression

Candidate instruction SHA-256: `2d947bacbc852bed80e19dc9ae2f340661ee35838587fe9f32bff9160df693f9`. A disposable project using Codex CLI 0.163.0 installed the candidate folder through Skills CLI 1.7.4. Both `SKILL.md` and `agents/openai.yaml` matched source bytes; native `skills/list` returned exactly one enabled AgentBay package with display name **AgentBay**.

The model-backed HTML review used catalogue revision `fca4e2ea1a71214678a7c9ca3b52eeba6c2bdf7b`, read the actual installer/catalogue/provider registry, selected Vercel’s `web-design-guidelines`, installed its pinned revision `1a2c79d4e6c4a2283dc2c614b6538cbe1ed5ca62`, and applied the installed instructions. Independent checks confirmed upstream byte parity, native discovery, the expected findings at `first-use.html:11`, `:12`, and `:14`, and an unchanged HTML fixture.

The first restricted invocation correctly reported that the sandbox blocked `.agents` writes. The subsequent CLI invocation used its supported approval-aware mode; the narrowly scoped installation retry succeeded. Permission errors must not be relabelled as installs. The model’s task commands used Node 26.5.1; native discovery and the outer installer command used pinned Node 24.22.2. This was a native disposable-project test with existing user authentication, not a fresh Docker home or desktop UI session. No new Claude desktop/Code execution pass is claimed. Project/global command selection is tested separately; the test did not install a global copy.

A separate discovery-only “Excel to PDF” request searched the same catalogue and inspected pinned upstream files. It identified Adobe `adobe-anypdf` as supporting XLSX → PDF while reporting missing Adobe tools and unestablished Codex compatibility. It also inspected Microsoft `doc-format-converter` as a local reconstruction alternative, reported missing Python dependencies and layout limits, and rejected PDF → Excel / Excel → Markdown as equivalent conversions. No conversion or additional installation was performed in this test.
