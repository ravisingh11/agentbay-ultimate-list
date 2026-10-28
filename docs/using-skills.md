# Install AgentBay Skill Installer and try it

[Simple install by app](install.md) · [Read the GitHub skill](../skills/agentbay-skill-installer/SKILL.md) · [Browse skills](../skills/README.md) · [Home](../README.md)

AgentBay finds and verifies skills for your task using its curated repository catalogue. When you ask to install and use a selected skill, it installs a focused choice and applies its instructions. It works with Codex desktop, CLI and IDE extension. Start in one project.

## What you are installing

There are three separate pieces:

1. **AgentBay Skill Installer:** its `SKILL.md` tells Codex how to find, verify, install and use a suitable skill. This first-party MD contains the workflow; it reads the repository catalogue and publisher registry when needed.
2. **The catalogue:** listings and source links that help with discovery. The installer searches this repository's `skills/catalog.json`, including our reviewed additions and corrections, and uses `data/preferred-providers.json` to identify official owners. It reads both at one recorded revision. It searches the data locally and loads only relevant candidate details into context; you do not need to read thousands of listings yourself.
3. **Individual skills:** the actual `SKILL.md` files and any companion scripts or resources maintained by their publishers, often on GitHub. When you ask to install or use one, AgentBay retrieves the selected skill package from that upstream source, then reads and applies it. Installing AgentBay alone does not install those other skills.

For example, an HTML review can start with this GitHub MD, use AgentBay's catalogue to locate a relevant listing, then fetch the selected publisher's actual skill. AgentBay's generated summaries are search aids; the installer reads the upstream instructions to establish task fit. An explicit official source can be inspected directly if the catalogue lacks it.

## Install

Follow [Install AgentBay](install.md) for the Codex desktop/CLI, Claude Code or Claude desktop steps, prerequisites and private-repository access. Install in the project where you will use it. For Codex, inspect `.agents/skills/agentbay-skill-installer/SKILL.md`, then check the app's own Skills view or selector.

The installer listing is also available from your project:

```sh
npx skills@1.7.4 list --agent codex
```

That listing confirms installed files; the agent's own selector confirms discovery. Start a fresh chat or restart the app if the skill does not appear. See [OpenAI's skills documentation](https://learn.chatgpt.com/docs/build-skills).

Ask naturally, replacing the bracketed task:

> Find a skill for [my task] with AgentBay.

This asks for verified choices. To install and use your chosen skill, follow up with: "Install this skill in my project, check its prerequisites, then use it for the task." If Codex does not select AgentBay automatically, choose `agentbay-skill-installer` from its Skills view or selector and repeat the request. The installed name and path stay compatible with existing installations.

The skill should report installation/discovery, tools/project configuration and account readiness separately. A missing cloud sign-in need not block a local test. Task success requires checking the requested behavior after the work; installation alone is not a success result. [Follow the Cloudflare Worker walkthrough](cloudflare-first-use.md) for a complete diagnosis-and-fix example with local runtime checks.

## Choose installation scope

The quick-start command installs only in the current project, at `.agents/skills/agentbay-skill-installer/SKILL.md`. To make the skill available across projects on this computer, add `--global` to the chosen install command. For Codex, Skills CLI installs that user-scoped copy under `~/.agents/skills/agentbay-skill-installer/`.

Choose one scope and one source. Check the installer listing and existing files before adding another copy; Codex can show duplicate names if both a project and user installation exist. A local installation does not automatically install the skill on another computer or remote environment.

## Repository access and version pinning

When the repository is public, installation and catalogue retrieval work without a GitHub account. AgentBay resolves one commit and downloads its catalogue, publisher registry and manifest over public HTTPS, then verifies the recorded checksums. GitHub CLI is optional for public access. While it remains private, use the authorized access described below.

The repository command in the install guide is the primary installation route. It installs the maintained MD from `main`. For private access, use an existing Git, GitHub CLI or SSH sign-in with access to `ravisingh11/agentbay-ultimate-list`; see the Skills CLI's [private repository instructions](https://github.com/vercel-labs/skills/blob/a80e4c9d12d607631249d4d7d059f835d4b2f13a/docs/commands.md#private-repositories).

For reproducible installation, replace `main` in the command with an approved full commit SHA. To test an unmerged PR, use that PR's exact head commit. Pinning an older release also pins its older workflow; it does not pick up these repository-first instructions automatically.

At use time, the skill reads the catalogue and publisher registry from an existing verified checkout or retrieves both at one resolved repository commit. With a private repo, keep authorized access available in the environment where Codex runs. A local installation does not grant a remote environment access. If the catalogue cannot be read, the skill reports that limitation and may use the public finder as an explicitly disclosed fallback; that does not establish a search of repository curation.

Installation access and catalogue access are separate checks. The installer command can use existing Git/SSH credentials. The MD's on-demand private catalogue example uses GitHub CLI: make `gh` available and sign in with `gh auth login`, or provide Codex with a verified catalogue checkout/snapshot. Git credentials alone do not make an unavailable `gh` command work. A full repository checkout is optional when using the API route.

The [website SKILL.md](https://agentbay.io/skills/agentbay-skill-installer/SKILL.md) is a separately published release. It may have older instructions until a new repository revision is reviewed and published. Check its [release metadata](https://agentbay.io/skills/agentbay-skill-installer/release.json) and [verification guidance](installer-validation.md) before comparing versions. It is no longer the primary quick-start route. Install from one source only.

## Check updates or remove the installer

From the project where you installed it:

```sh
npx skills@1.7.4 check
npx skills@1.7.4 update agentbay-skill-installer --project
```

The first command checks available updates; the second targets the named project skill. An update replaces the installed upstream copy, including local edits, so save any personal changes first. Use `--global` instead of `--project` for an installation shared across projects. If you need a specific reviewed revision, use the install command with that full commit instead of following a moving branch. See the pinned CLI's [update instructions](https://github.com/vercel-labs/skills/blob/a80e4c9d12d607631249d4d7d059f835d4b2f13a/docs/commands.md#skills-update).

To remove AgentBay's installer from every agent in this project, review and confirm the named removal:

```sh
npx skills@1.7.4 remove agentbay-skill-installer
```

Codex and other agents can share the same `.agents/skills` directory. An agent-filtered removal can preserve that shared copy for other agents, so inspect the files and listing rather than relying only on a success message. The command above removes the named skill and its project bindings; it does not remove the other skills. For a global installation, add `--global`. Remove separately installed upstream skills by their own names when desired. Cloud accounts and project dependencies are managed separately.

## First worked example

This example asks the installer to choose an official skill from the task, rather than giving it the desired skill name. It reviews a small HTML file without deploying it.

Copy [first-use.html](examples/first-use.html) into your project as `first-use.html`. The example deliberately contains accessibility defects. In Codex, ask:

> $agentbay-skill-installer Read .agents/skills/agentbay-skill-installer/SKILL.md. Use AgentBay's repository catalogue to find one official skill for reviewing HTML accessibility and usability. Install it for Codex in this project, then use it to review first-use.html. Explain the task fit and report the AgentBay listing ID, catalogue revision, upstream source and findings with filename and line number. Do not edit the HTML file.

The installer should search the repository's accepted catalogue, inspect relevant upstream instructions, verify the publisher and current repository state, install the selected package, read the installed instructions and perform the review. An official-owner copy of someone else's skill is not necessarily the original publisher's source.

The review should identify the unlabelled email input, the unnamed icon button and the image without alternative text. Findings must refer to the relevant lines in your copy. The HTML file should remain unchanged.

Record the selected upstream revision and referenced resources when reproducing the review.

## If something is missing

- **`npx` or Node is unavailable:** install a supported Node.js release, then retry the installation command.
- **The installer lists the skill but Codex does not:** open Codex in the project containing `.agents/skills`, check the desktop Skills view or CLI/IDE `/skills`, then start a fresh chat or restart if necessary.
- **The private repository returns an authentication or not-found error:** confirm the signed-in GitHub account has repository access. Ensure that access is available both to the installation command and to Codex when it retrieves catalogue context. The public finder is a disclosed fallback with a different scope.
- **A suitable skill is missing from the catalogue:** give an official source URL or describe the task more precisely. The installer verifies that source and reports it as outside the catalogue match.
- **The public download differs from the repository:** an unmerged or unreleased revision may be ahead of the published download. See the [publication and test procedure](installer-maintenance.md); compare with the recorded released revision.

## Source, scope and licensing

The repository maintains AgentBay's own installer skill. The website serves a published copy. Third-party skills are obtained from their upstream publishers and retain their own licenses. Inspect their instructions and required resources before using them.

A catalogue listing may represent a skill, repository or collection; it does not by itself establish runtime compatibility. The website finder and the broader catalogue also have different inclusion rules and counts. See [data documentation](data.md).
