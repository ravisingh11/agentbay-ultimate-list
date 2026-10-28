#!/usr/bin/env bash
# Project-scoped install from the maintained GitHub skill. No global settings change.
set -euo pipefail

usage() {
  echo "Usage: bash install.sh codex|claude-code|both"
  echo "Codex covers desktop and CLI. Run from the project you will open in your agent."
  echo "Claude desktop: upload downloads/agentbay-skill-installer.zip; see docs/install.md."
}
[[ $# == 1 ]] || { usage; exit 2; }
case "$1" in
  codex) agents=(codex);;
  claude-code) agents=(claude-code);;
  both) agents=(codex claude-code);;
  *) usage; exit 2;;
esac
for tool in node npx git; do
  command -v "$tool" >/dev/null || { echo "Install Node.js 22.20+ and Git, then retry." >&2; exit 1; }
done
node -e 'const [a,b]=process.versions.node.split(".").map(Number);process.exit(a>22||(a===22&&b>=20)?0:1)' || {
  echo "Node.js 22.20 or newer is required." >&2; exit 1;
}
name=agentbay-skill-installer
for path in ".agents/skills/$name" ".claude/skills/$name"; do
  if [[ -e "$path" || -L "$path" ]]; then
    echo "AgentBay already exists at $path. Preserving it; inspect or update that installation first." >&2
    exit 1
  fi
done
ref=${AGENTBAY_REF:-main}
[[ "$ref" == main || "$ref" =~ ^[0-9a-f]{40}$ ]] || {
  echo "AGENTBAY_REF must be main or a full lowercase commit SHA." >&2; exit 2;
}
source="https://github.com/ravisingh11/agentbay-ultimate-list/tree/$ref/skills/$name"
if ! npx --yes skills@1.7.4 add "$source" --skill "$name" --agent "${agents[@]}" --yes; then
  echo "Installation failed. While the repo is private, your GitHub account needs access and working Git, gh or SSH authentication. See docs/install.md." >&2
  exit 1
fi
for agent in "${agents[@]}"; do
  if [[ "$agent" == codex ]]; then folder=.agents; else folder=.claude; fi
  test -s "$folder/skills/$name/SKILL.md" || { echo "Installed instructions missing for $agent." >&2; exit 1; }
done
echo "AgentBay files installed in this project. Open this same project in your agent and start a fresh chat."
echo 'Ask: Find a skill for [my task] with AgentBay.'
echo "Then ask it to install and use your chosen skill. Installation alone does not verify discovery or task success."
