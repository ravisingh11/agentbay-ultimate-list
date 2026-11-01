# Scenario implementation patterns

Adapted from Meta's unitBench scenario guide; retain its license/attribution.
Check these paths in the selected public OpenZL checkout:

| Purpose | Public path |
| --- | --- |
| Scenario entry and callback types | `benchmark/unitBench/bench_entry.h` |
| Kernel implementations and declarations | `benchmark/unitBench/scenarios/codecs/` |
| Graph implementations | `benchmark/unitBench/scenarios/` |
| Registration | `benchmark/unitBench/benchList.h` |
| Runtime options, block handling and graph comparison | `benchmark/unitBench/unitBench.c` |
| Make source discovery | `Makefile`, `build-scripts/make/multiconf.make` |
| CMake source discovery | `benchmark/unitBench/CMakeLists.txt` |

## Kernel scenarios

Match the exact callback types in `bench_entry.h`:

```c
size_t codec_prep(void* src, size_t srcSize, const BenchPayload* bp);
size_t codec_outSize(const void* src, size_t srcSize);
size_t codec_wrapper(const void* src, size_t srcSize,
                     void* dst, size_t dstCapacity, void* customPayload);
```

A `prep` callback can mutate input to construct the kernel's required encoded
layout. Its return value controls the bytes subsequently benchmarked. Verify
that layout and size instead of benchmarking arbitrary bytes as encoded data.
Use the neighboring codec's actual API and capacity rules. Decode output sizes
depend on its stream/element widths; encode sizes can expand. Guard arithmetic
and alignment, and do not assume `srcSize` is always a sufficient destination.

Declare the wrapper/prep/outSize in a header and include it in `benchList.h`.
Register its actual functions, for example:

```c
{ "codecEncode", codec_wrapper, .prep = codec_prep, .outSize = codec_outSize },
```

Names/functions here are explanatory shapes, not APIs to paste unchanged.
Follow `scenarios/codecs/bitSplit.c` or the chosen codec's real neighboring case.
A kernel benchmark only times that callback. Add an independent encode/decode
test that compares both reconstructed length and bytes against expected input;
an exit-zero timing row does not establish kernel correctness.

## Graph scenarios

Use a tokenizer matching the input element width. For example, the following
complete graph pattern accepts 32-bit little-endian integers and stores them:

```c
// Copyright (c) Meta Platforms, Inc. and affiliates.
// AgentBay adaptation: minimal public 32-bit graph example.
#include <stdlib.h>
#include "openzl/zl_compressor.h"
#include "openzl/zl_public_nodes.h"

ZL_GraphID agentbay_u32_store_graph(ZL_Compressor* cgraph)
{
    if (ZL_isError(ZL_Compressor_setParameter(
                cgraph, ZL_CParam_formatVersion, ZL_MAX_FORMAT_VERSION))) {
        abort();
    }
    if (ZL_isError(ZL_Compressor_setParameter(
                cgraph, ZL_CParam_compressionLevel, 1))) {
        abort();
    }
    if (ZL_isError(ZL_Compressor_setParameter(
                cgraph, ZL_CParam_minStreamSize, -1))) {
        abort();
    }
    if (ZL_isError(ZL_Compressor_setParameter(
                cgraph, ZL_CParam_storeOnExpansion, ZL_TernaryParam_disable))) {
        abort();
    }
    return ZL_Compressor_registerStaticGraph_fromNode1o(
            cgraph, ZL_NODE_INTERPRET_AS_LE32, ZL_GRAPH_STORE);
}
```

For a real codec benchmark, replace the downstream graph with the intended
node/pipeline and compare equivalent work. STORE is a smoke example, not a
claim about codec performance. Add a matching declaration in a header, include
that header in `benchList.h`, and insert the entry among the scenarios:

```c
{ "agentbay_u32_store", .graphF = agentbay_u32_store_graph },
```

The example's level 1 and disabled automatic STORE fallbacks are explicit smoke
test settings, not mandatory settings for every benchmark. At this revision,
`minStreamSize=0` means the default threshold, and `storeOnExpansion=0` means
enabled; disabling them requires a negative threshold and
`ZL_TernaryParam_disable`, respectively. Preserve the user's intended pipeline
behavior, and record whether a test isolates the codec or measures its fallbacks.

Keep new entries alphabetically ordered within their existing section; avoid
reformatting unrelated registrations. The checked Make and CMake unitBench
targets discover `.c` files recursively, so a new `.c` in the scenario tree
does not need a hand-maintained public source list. If the user's project
actually maintains Buck targets, update its own build graph too; do not require
an internal `//openzl/dev` target for the public workflow.

Use 16/32/64-bit tokenizers according to the actual element size; structured
nodes require their own header/record layout. Read `scenarios/sao_graph.c` only
when that structured pattern is relevant.

After registering, rebuild and confirm the exact new name appears in `--list`.
Run it normally without `--csv`, `-z` or `--no-decompress`, then run its explicit
round-trip regression with exact expected length and bytes. A benchmark's own
graph comparison uses the returned decoded length; it is not a substitute for
that length assertion. Collect optional CSV timings separately and label the
missing decompression measurement. Preserve any failure output.
