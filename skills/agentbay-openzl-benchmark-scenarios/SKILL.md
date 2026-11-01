---
name: agentbay-openzl-benchmark-scenarios
description: "Add kernel or graph benchmark scenarios to a local OpenZL checkout using unitBench. Use for codec encode/decode timings or compression/decompression pipeline benchmarks, with synthetic fixtures and separate correctness checks. AgentBay adaptation of Meta OpenZL guidance."
---

# OpenZL Benchmark Scenarios — AgentBay adaptation (Meta upstream)

Adapted by **AgentBay** from Meta's public OpenZL benchmark guidance. This is
not an official Meta skill or an endorsement. See [NOTICE.txt](NOTICE.txt), the
retained [LICENSE](LICENSE), and exact inputs/hashes in
[provenance.json](provenance.json).

Create a benchmark scenario in the user's selected **local OpenZL checkout**.
Choose a kernel wrapper when a standalone encode/decode API is available; choose
a graph when testing a node in its compression/decompression pipeline. Infer
the intended codec, element width and parameters from the task and code; ask
only for missing choices that affect the implementation.

## Inspect and implement

1. Record the checkout revision and existing changes. These examples were
   checked against `meta/openzl@d5d872059bad85da410eb66e3d7f9cac107be263`.
   Inspect the current harness when using another revision; preserve unrelated
   work and do not reset or replace the user's checkout.
2. Read [scenario-patterns.md](references/scenario-patterns.md) for the actual
   wrapper signatures, registration and graph pattern. Follow a nearby scenario
   matching the selected codec, rather than assuming all codecs accept the same
   input layout. Respect input widths, prep transformations and output capacity.
3. Add the scenario and focused correctness coverage. Kernel timing wrappers do
   **not** automatically test the inverse codec. Verify encode/decode bytes and
   lengths separately. Graphs should have a round-trip regression that checks
   the complete expected length and byte equality, including short valid inputs
   and the codec's relevant boundary cases.
   OpenZL can automatically STORE short or expanding streams. When isolating a
   codec, make those fallback settings explicit so a successful round trip is
   not mistaken for evidence that the intended codec path ran.

## Build and verify locally

Follow [build-and-verify.md](references/build-and-verify.md). Use the public Make
target or an already configured public CMake build. Inspect the build/fetch
recipe before first use; do not install tools globally, clean shared build
outputs, or remove existing dependency directories to clear a failure. A clean
build can use a separate scratch checkout. Keep generated data and results in a
new temporary directory and use synthetic inputs before user-approved datasets.

The bundled [prepare_data.py](scripts/prepare_data.py) creates a unique directory
with a bounded, width-aligned synthetic `input.bin` and hash manifest. It does
not build, run OpenZL, retrieve data, or delete an existing run.

At the checked upstream revision:

- Put options **before** the scenario, e.g. `unitBench -i=1 scenario input.bin`.
- A normal graph run performs decompression and a byte comparison; `-z` skips
  it. **`--csv` also disables decompression**, even without `-z`. Keep a separate
  normal graph run and explicit correctness test before collecting CSV timings.
- `-B` discards a final partial block. Make both file size and block size valid
  for the element layout, with file size divisible by block size. Otherwise
  report the untested remainder rather than claiming full-input coverage.
- The harness comparison uses the returned decoded length. A successful run
  alone is not proof of the full expected length; retain the independent
  length-and-bytes check for a new graph.

Do not disable or skip a failing correctness check to obtain timing output.
Keep failed, incomplete and unperformed checks distinct. Run locally; remote CI,
publication, real-device operations and unrelated policy/configuration changes
are outside this skill's benchmark task.

## Report

Summarize the changed scenario, kernel/graph choice and parameters; source
revision/diff; compiler, platform and build mode; input size/layout/hash; exact
commands, exit statuses and correctness evidence. Label CSV or `-z` results as
compression-only, and kernel results as the specific operation measured.
Separate correctness evidence from timing observations. Compare timings only
under comparable builds, data and settings; a small periodic fixture does not
establish a general speedup or production performance. Leave logs and fixtures
available for review; sharing or publishing them is a separate action.
