# OpenZL Benchmark Scenarios — AgentBay adaptation

This maintained package is an **AgentBay adaptation** of Meta Platforms, Inc.
and affiliates' [OpenZL skill](https://github.com/meta/openzl/blob/d5d872059bad85da410eb66e3d7f9cac107be263/.claude/skills/unitbench-scenarios/SKILL.md).
It is not an official Meta skill or endorsed by Meta. The exact original
BSD-3-Clause license is retained inside the package; the repository MIT license
does not replace it. Original inputs and adapted files have immutable hashes.

- [Read the skill](../skills/agentbay-openzl-benchmark-scenarios/SKILL.md)
- [Download the ZIP](../downloads/agentbay-openzl-benchmark-scenarios.zip)
- [Source provenance](../skills/agentbay-openzl-benchmark-scenarios/provenance.json)
- [Scope and eight deferred paths](../data/adapted-openzl-review.json)

Use it to add local kernel or graph benchmark scenarios in an OpenZL checkout.
It documents public Make builds, bounded synthetic fixtures, separate correctness
and timing checks, CSV skipping decompression, partial-block truncation and
STORE fallback behavior. Review build prerequisites before running it.

Verification on macOS arm64: native Make build, exact new graph registration and
execution, twelve complete length/byte round trips, twelve undersized-buffer
rejections, and fifteen helper tests passed. CMake, a new kernel scenario and
independent-model first use were not run. Synthetic smoke timings are not a
representative compression performance claim.

Rebuild or verify the deterministic ZIP with `python3 scripts/adapted_openzl.py
build` or `python3 scripts/adapted_openzl.py check`. The full unittest suite also
checks package bytes and helper behavior without compiling or fetching OpenZL.
No dependency sources or binaries are bundled. The broader catalog listing has
no official Meta badge and does not alter Finder eligibility or provider policy.
