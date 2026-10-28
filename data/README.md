# Catalogue inputs

| File | Maintained purpose |
| --- | --- |
| [curation.json](curation.json) | Reviewed additions, corrections and explicit exclusions, applied after each import. |
| [preferred-providers.json](preferred-providers.json) | Verified provider names, official GitHub owners and public homepages. |

These are the editable inputs. Follow [CONTRIBUTING.md](../CONTRIBUTING.md) for formats and evidence, then run:

```sh
python3 scripts/catalog.py render
python3 scripts/catalog.py check
```

The accepted baseline is root [catalog.json](../catalog.json). Do not edit it or the generated downloads directly. Imports augment that baseline; an upstream outage or website presentation change must not erase reviewed listings.

Generated [summary fingerprints](../provenance/descriptions.json), [stable-ID aliases](../provenance/aliases.json) and [source hashes](../sync-manifest.json) are required integrity data. They are regenerated with the catalogue and must stay tracked. See the [repository layout and maintenance workflow](../docs/maintenance.md#repository-layout).

[Home](../README.md)
