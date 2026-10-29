# Maintain and publish the AgentBay installer

[Source SKILL.md](../skills/agentbay-skill-installer/SKILL.md) · [First-use guide](using-skills.md) · [Verification](installer-validation.md) · [Home](../README.md)

`skills/agentbay-skill-installer/SKILL.md` is the maintained source for AgentBay's own installer. The website serves a published copy. Edit the repository file and review it through a pull request; do not edit the website copy independently.

## Validate a source change

```sh
python3 scripts/installer.py check
python3 scripts/catalog.py render
python3 scripts/catalog.py check
python3 -m unittest discover -s tests -v
```

The first command checks the entry point's name, frontmatter and body. The source change also needs an installation and use check; structural validation alone does not establish that Codex can use it.

## Publish an approved revision

After approval, choose the exact committed revision to publish. Stage its bytes into the website's public directory:

```sh
python3 scripts/installer.py stage --revision APPROVED_COMMIT --output /path/to/agentbay/public
python3 scripts/installer.py verify --revision APPROVED_COMMIT --output /path/to/agentbay/public
```

Staging writes only `skills/agentbay-skill-installer/SKILL.md` and an adjacent `release.json`. The release file records the source repository, path, commit, SHA-256, byte length and supported CLI version. The website's existing static-asset build includes both files.

Run the website's normal reviewed deployment process, then verify the public result:

```sh
python3 scripts/installer.py verify --revision APPROVED_COMMIT --url https://agentbay.io/skills/agentbay-skill-installer/SKILL.md
```

The check fails if either the downloaded bytes or recorded source revision differ. Compare against the chosen released commit, not an unreleased pull request or whichever revision happens to be on `main`. The public URL can therefore remain usable while a newer source change is under review.

A working-tree export is available for local smoke tests:

```sh
python3 scripts/installer.py stage --candidate --output /tmp/agentbay-installer-candidate
```

Its release metadata marks it `candidate_only`; it is not an approved publication artifact.

## Reproduce the Codex first-use test

The optional [smoke runner](../scripts/smoke_installer.py) creates a disposable Docker container with Node.js and a pinned Codex CLI. It extracts the repository quick-start command from the README and substitutes the staged candidate folder for its GitHub URL, preserving the selected skill and agent. This tests the candidate package without supplying private GitHub credentials to CI. Test the real authenticated GitHub URL separately at the candidate commit before claiming that route passed.

The full run supplies a read-only snapshot of the committed `skills/catalog.json` and `data/preferred-providers.json`, with their source revision and hashes. Codex receives the task-based HTML review prompt from the guide, without a desired skill name. A pass requires observed catalogue and registry access, an installed official upstream skill matching its pinned source, a reported matching catalogue ID and revision, native discovery, and the three expected HTML findings. The snapshot exercises repository context without mounting GitHub credentials; it does not establish that live authentication works in that container.

```sh
python3 scripts/smoke_installer.py --output ../agentbay-first-use-check
```

Docker must be running, and the output must be under a Docker-shared directory. The sibling-directory example works with the usual Docker Desktop and Colima workspace sharing. The test uses your existing Codex ChatGPT sign-in through a read-only auth-file mount; it does not copy credentials into the project or receipts. Use `--codex-auth-file /path/to/auth.json` when the current Codex account is stored somewhere other than its normal configured location. Model execution consumes the normal Codex allowance. The test does not change repository visibility, install global user skills or deploy a site.

The output contains source hashes, catalogue provenance, runtime versions, native `skills/list` results, the Codex execution trace and a pass/fail receipt. A pass also requires matching installed bytes, evidence that both installed skill instructions were read and an unchanged HTML fixture. These behavioral checks are separate from the ordinary offline catalogue CI checks.

The snapshot also includes `sync-manifest.json` from that same commit. For a real network retrieval check outside the model container, use `scripts/catalogue_context.py` as described in the [public-release procedure](public-release.md#verify-the-real-github-route). This separately tests public HTTPS or existing authorized GitHub access, verifies catalogue/publisher checksums and never executes catalogue content.

CI runs the credential-free installation/discovery portion in a separate job:

```sh
python3 scripts/smoke_installer.py --install-only --output ../agentbay-install-only-check
```

That mode installs the staged candidate and queries Codex's native registry without mounting an auth file or making a model request. It does not claim to test task execution. Full use is validated by the authenticated worked-example run described above.

### Cloudflare diagnosis and fix

Run the [Cloudflare walkthrough](cloudflare-first-use.md) through the same isolated harness:

```sh
python3 scripts/smoke_installer.py --scenario cloudflare --output ../agentbay-cloudflare-check
```

The runner verifies and unpacks the same example ZIP offered to newcomers, installs its pinned dependencies, confirms the expected failing unit test and a real 500 response in Wrangler's local runtime, then gives Codex the documented task without a desired skill name or explicit instruction-file path. After the fix it checks all three tests, local packaging, actual HTTP responses, unchanged tests/package/configuration, catalogue provenance, installed upstream instructions and relative reference files, and native discovery. Cloudflare credentials are not supplied and no remote resources or deployments are required. The model receives existing Codex authentication read-only, as in the HTML run. Keep raw traces and receipts outside the repository; summarize the tested revision and observed outcomes in the pull request or release review.

Desktop UI verification is separate: follow the desktop steps in the walkthrough and record the app version and observed result. If the desktop automation tool refuses access to Codex, record that limitation; CLI and app-server checks do not establish that desktop UI interaction passed.

## Maintain the example download

[`scripts/example_bundle.py`](../scripts/example_bundle.py) packages only the maintained Cloudflare example files and root MIT license into [`cloudflare-worker.zip`](examples/cloudflare-worker.zip). It adds `source-manifest.json` with original file paths, byte lengths and SHA-256 values, and writes an adjacent checksum. It does not package installed dependencies, local environment settings or the catalogue. The source folder remains the maintained input.

```sh
python3 scripts/example_bundle.py build
python3 scripts/example_bundle.py check
```

The archive uses fixed timestamps, permissions, ordering and uncompressed entries so identical inputs produce identical bytes across Python versions without depending on a compression-library version. CI checks the bundle and regenerates it to detect drift. A source change requires committing the rebuilt ZIP and checksum together. Existing unowned files, modified checksum files and symlinked inputs/outputs are preserved by refusing the build.

## Maintain the Claude desktop upload

The [upload ZIP](../downloads/agentbay-skill-installer.zip) is generated directly from the maintained MD. It contains one folder with that exact `SKILL.md`, not another edited skill source. Rebuild it whenever the source changes:

```sh
python3 scripts/skill_bundle.py build
python3 scripts/skill_bundle.py check
```

Commit its checksum with it. The builder uses fixed metadata and refuses symlinks, unowned archives/checksums and temporary output collisions. CI checks byte equality and deterministic regeneration. Structural ZIP checks do not establish a successful Claude desktop upload or task; record an actual app result separately. See [installation by app](install.md).

## Native display metadata

`skills/agentbay-skill-installer/agents/openai.yaml` gives Codex the display name **AgentBay** and an explicit default prompt. The skill directory is installed together for coding agents. The maintained `SKILL.md` remains the instruction source; the Claude desktop ZIP and website MD deliberately contain that file without Codex-specific UI metadata. Validate native discovery and the installed UI metadata separately from ZIP byte parity.
