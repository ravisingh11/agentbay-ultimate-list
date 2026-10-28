# Solve a Cloudflare Worker problem with AgentBay

[Read AgentBay's skill](../skills/agentbay-skill-installer/SKILL.md) · [Installation guide](using-skills.md) · [Validation](installer-validation.md) · [Home](../README.md)

Install AgentBay once, describe your problem, and let it find the relevant specialist instructions. This example uses a deliberately broken Worker: `/hello?name=Ada` works, but `/hello` fails. The goal is a working local endpoint with a friendly default name. No Cloudflare account, API token or deployment is needed.

## 1. Prepare the example

[Download the example ZIP](https://github.com/ravisingh11/agentbay-ultimate-list/raw/refs/heads/main/docs/examples/cloudflare-worker.zip), extract it into an empty location, and open the `agentbay-cloudflare-demo` folder. No repository checkout is needed. The bundle includes the source, tests, lockfile, MIT license and a manifest of the original file hashes. [Inspect the maintained source](examples/cloudflare-worker) · [Download checksum](examples/cloudflare-worker.zip.sha256).

The example requires Node.js 22.20+ and Git. Its lockfile pins Wrangler 4.153.0 and supporting packages; the fixed compatibility date matches that release's bundled runtime. Keep these together when reproducing the example. For a PR preview, replace `main` in the download URL with the PR's full head commit.

From that new folder, initialize the local project and install the example dependencies:

```sh
git init
npm ci
npm test
```

The first test deliberately fails because a missing name causes a `TypeError`. The supplied-name and unknown-path tests pass. This failure is the problem to solve, not an installation failure.

Install AgentBay in the same folder:

```sh
npx skills@1.7.4 add https://github.com/ravisingh11/agentbay-ultimate-list/tree/main/skills/agentbay-skill-installer --skill agentbay-skill-installer --agent codex
```

While the repo is private, use authorized GitHub access for both installation and catalogue retrieval. For an unmerged PR, replace `main` with its exact head commit. [Access and version pinning](using-skills.md#repository-access-and-version-pinning).

## 2. Open the project and describe the problem

Open this folder in Codex. In desktop, open the Skills view and confirm `agentbay-skill-installer` appears; in CLI or the IDE extension, check `/skills`. Start a fresh chat if needed. Then ask:

> Find a skill for fixing this Cloudflare Worker's failing /hello request when the name is missing with AgentBay. Install one suitable official skill in this project, report readiness, then fix and test the behavior. Limit application edits to src/index.js; keep tests, package files and Wrangler config unchanged. Work locally; do not deploy or change authentication.

You do not need to know the Cloudflare skill's name. AgentBay should search its catalogue, inspect appropriate official instructions, install the selected package including its references, and read the installed copy.

## 3. Check readiness and the result

The readiness report should distinguish:

- **Skill:** installed location, supporting files, instructions read, and whether native discovery was confirmed.
- **Tools/project:** Node.js, project-local Wrangler and the existing configuration are available, or the specific setup needed.
- **Account:** not required for these local checks. Cloud account access remains a separate requirement for a future remote operation.

After the fix, all three tests should pass:

```sh
npm test
npm run check
npm run dev
```

`npm run check` validates local packaging through Wrangler's dry run; it does not deploy. With the local server running, open these URLs:

| URL | Expected result |
| --- | --- |
| `http://127.0.0.1:8787/hello` | 200; `{"message":"Hello, WORLD!"}` |
| `http://127.0.0.1:8787/hello?name=Ada` | 200; `{"message":"Hello, ADA!"}` |
| `http://127.0.0.1:8787/missing` | 404 |

Stop the local server with Ctrl+C. The original example remains broken in this repository so the next newcomer can reproduce the journey; solve it in your own copy.

## Desktop verification

The repeatable automated test uses Codex CLI and native skill discovery. To validate the desktop journey itself, use the same folder, installation command and prompt in a fresh desktop chat, confirm the selected Cloudflare skill in the Skills view, inspect its installed files, and independently run the checks above. Record the app version, source revision and outcomes. Desktop clicks and chat interaction must be recorded as unverified until this manual check succeeds; a CLI pass alone does not establish desktop UI success.
