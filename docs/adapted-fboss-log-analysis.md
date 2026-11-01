# AgentBay adaptations of FBOSS log-analysis skills

These two maintained packages are **AgentBay adaptations**, derived from
[Meta FBOSS](https://github.com/meta/fboss) revision
`d2cd70e1a46bbe87b280475e2aa7ee710da40ea3`. They are not official Meta
publications or endorsed by Meta.

- [FBOSS Link Log Analysis — AgentBay adaptation](../skills/agentbay-fboss-link-log-analysis/SKILL.md)
- [FBOSS QSFP Log Analysis — AgentBay adaptation](../skills/agentbay-fboss-qsfp-log-analysis/SKILL.md)

Each package includes Meta attribution, the exact original three-condition
BSD-style license, an adaptation notice and per-file source hashes. The
repository's general MIT license does not replace those package licenses.
The source entrypoints are rewritten around supplied local files; remote CI
fetching and device-operation instructions are omitted. All required references
are included. Neither package requires the other.

The helpers analyze supplied log text. They do not access switches, change
configuration, restart services, fetch CI logs, upload data or edit known-bad
policy. Missing evidence remains unconfirmed. Parser success means parsing
completed, not that hardware or a test passed. Instructions and small reports
must keep private log data local.

The packages are listed in AgentBay's broader catalog. Existing homepage
Finder official-owner and adoption thresholds are unchanged; these adaptations
must not be attributed to the Meta official-provider group.

## Downloads and checks

- [Link-log ZIP](../downloads/agentbay-fboss-link-log-analysis.zip)
- [QSFP-log ZIP](../downloads/agentbay-fboss-qsfp-log-analysis.zip)

Rebuild/check deterministic downloads with `python3 scripts/adapted_fboss.py
build` and `python3 scripts/adapted_fboss.py check`. Run
`python3 -m unittest discover -s tests -v` for fixture and existing catalog
coverage. The 42 adaptation checks use synthetic inputs, with no live device,
SDK or private CI. Real device diagnosis and cross-platform compatibility are
not certified by those checks.

The nine other reviewed paths remain excluded in
[data/adapted-fboss-review.json](../data/adapted-fboss-review.json).
