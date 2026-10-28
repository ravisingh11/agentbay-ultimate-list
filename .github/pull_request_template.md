## Why

Describe the problem and link the issue when available. Disclose any affiliation with a proposed project.

## Outcome

Explain what changes for the next person using the catalogue or installer.

## Review map

List affected IDs and maintained sources. Identify generated output, policy/workflow changes and third-party material separately.

## Evidence and verification

Link public sources and observation dates. List the exact commands run, source revision/hash, results and anything untested. For duplicates, identify the retained ID; for exclusions, explain the removal.

- [ ] I edited maintained inputs or source templates, then regenerated the outputs.
- [ ] `python3 scripts/catalog.py render`
- [ ] `python3 scripts/catalog.py check`
- [ ] `python3 -m unittest discover -s tests -v`
- [ ] I reviewed generated counts, records and aliases and included the resulting files.
- [ ] Installer/example changes include source and bundle checks. Install, discovery and use results are reported separately; an unperformed app check is not marked passed.
- [ ] I identified any material AI assistance and independently reviewed its output.

## Documentation

Name the canonical documents updated, or explain why documentation is unaffected.

## Risk and rollback

Explain failure cases and how to undo the change. Flag changes to IDs, schema, ownership attribution, permissions or publication.

## Out of scope

State related work intentionally left out, if any.

## Rights and review

- [ ] My original contribution is MIT licensed; third-party permissions and attribution are identified.
- [ ] No credentials, private account data or private sources are included.
- [ ] I understand that external contributor changes need owner review; CI and Proof do not authorize merge, deployment or publication.
