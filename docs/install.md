# Install AgentBay

[Read the skill](../skills/agentbay-skill-installer/SKILL.md) · [Home](../README.md) · [Detailed usage](using-skills.md)

Choose your app. You do not need to check out this whole repository.

## Codex desktop or CLI

Open your project's terminal and paste:

```sh
npx --yes skills@1.7.4 add https://github.com/ravisingh11/agentbay-ultimate-list/tree/main/skills/agentbay-skill-installer --skill agentbay-skill-installer --agent codex --yes
```

Open that same project in Codex and start a fresh chat. Desktop and CLI share `.agents/skills/agentbay-skill-installer/SKILL.md`; installing twice is unnecessary. Check the Skills view/selector for AgentBay. If it does not appear, restart the app and confirm you opened the project where you installed it.

## Claude Code

Open your project's terminal and paste:

```sh
npx --yes skills@1.7.4 add https://github.com/ravisingh11/agentbay-ultimate-list/tree/main/skills/agentbay-skill-installer --skill agentbay-skill-installer --agent claude-code --yes
```

Start Claude Code in that same project. Check `/skills` for `agentbay-skill-installer`. The installed entry is `.claude/skills/agentbay-skill-installer/SKILL.md`, normally linked to the shared `.agents` copy. [Claude Code's skill locations](https://code.claude.com/docs/en/skills#choose-where-skills-load).

For both coding agents, use `--agent codex claude-code` in one command. This uses one shared skill package. Avoid adding a second global or synced copy.

## Available across projects (optional)

The commands above install into the current project. To make AgentBay available to your user across projects on this computer, append `--global` to the command for your app. Choose one scope; reuse an existing installation instead of creating project and global duplicates. Claude desktop uses its own upload and has no terminal scope option.

Codex shows **AgentBay** as the display name; its package and explicit invocation name stay `agentbay-skill-installer` / `$agentbay-skill-installer`. After installation, check native discovery in the intended project before trying a task. A project install will not appear in a chat opened in another folder.

## Claude desktop app

1. [Download the skill ZIP](https://github.com/ravisingh11/agentbay-ultimate-list/raw/refs/heads/main/downloads/agentbay-skill-installer.zip).
2. In Claude, go to **Customize → Skills → Add skill → Upload skill**, upload the ZIP, and enable it. This is the route observed in desktop version 3.6556.2; labels may vary. Code execution/file creation must be enabled; organization policy may control availability. [Anthropic's upload instructions](https://support.claude.com/en/articles/12512180-use-skills-in-claude).
3. Start a new chat and use the prompt below.

![AgentBay enabled in Claude desktop, with Contents selected and SKILL.md open at Safety and scope](images/claude-desktop-agentbay-enabled.png)

*After upload: the blue switch shows AgentBay enabled. Open **Contents → SKILL.md** to inspect the instructions. This screenshot shows installation and inspection; task execution is checked separately.*

The ZIP packages the [maintained SKILL.md](../skills/agentbay-skill-installer/SKILL.md) unchanged, with a [checksum](../downloads/agentbay-skill-installer.zip.sha256). The terminal command installs coding-agent files; Claude desktop requires its own upload. Its chat runtime may lack Git, Node, network access or your local GitHub sign-in, so AgentBay must report any missing capabilities before attempting a task. See [observed app results and limits](installer-validation.md#observed-results).

## Use it

Ask: **Find a skill for [my task] with AgentBay.**

Then: **Install and use the chosen skill for this task.** Choose AgentBay in your app's skill selector if it is not selected automatically. Ask it to report the selected source, missing prerequisites and the checked task result; cloud access requires your own account permissions.

## Prerequisites and public access

The repository is public. Coding-agent installation needs Node.js 22.20+, Git and internet access; no GitHub account, invitation or full checkout is required. The command installs only the selected AgentBay skill folder. AgentBay retrieves the repository catalogue when you ask it to find a skill, then inspects the original publisher's instructions.

Claude desktop uses the Claude account's runtime, not your computer's terminal or GitHub sign-in. It needs code execution/file creation and access to the public catalogue and selected upstream source. The skill ZIP contains the installer instructions, not all listed skills. If network or runtime capabilities are unavailable, AgentBay must report that limitation; a public-finder fallback has a narrower scope and must be disclosed. Installation does not grant cloud or account permissions.

## Optional installer script

The maintained [install.sh](../install.sh) wraps the same pinned Skills CLI command, checks prerequisites and refuses to overwrite existing AgentBay installations. If you have downloaded it, run **from your project**:

```sh
bash /path/to/install.sh codex
# Or: bash /path/to/install.sh claude-code
# Or: bash /path/to/install.sh both
```

It installs only in the current project and prints the next prompt. Running it again where AgentBay already exists intentionally exits with status 1 and preserves the existing files; this is an overwrite refusal. It does not open an app, grant permissions or claim native discovery. Set `AGENTBAY_REF` to a full reviewed commit SHA for a reproducible test; the default is `main`. For updates/removal, use the [existing lifecycle commands](using-skills.md#check-updates-or-remove-the-installer).

## Verification

[Installer verification](installer-validation.md) records the automated checks, outstanding app-session checks and reproduction steps. File installation, native discovery and task success are verified separately.
