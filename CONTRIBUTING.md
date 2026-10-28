# Contributing to AgentBay Ultimate List

[Choose a change](#choose-a-contribution) · [Prepare a PR](#prepare-a-pull-request) · [Review policy](#maintainer-review) · [Guardrails](docs/guardrails.md)

> [!TIP]
> A broken link, clearer installation step or well-sourced correction is a useful first contribution. Start small; explain what the next person will find easier.

AgentBay sources and maintains this list. Contributions help expand it, correct facts and make the data easier to use. You can contribute through a GitHub issue or pull request; you do not need access to the AgentBay website code.

Read the [data reference](docs/data.md) and search the existing list before adding a record. Different components in one repository can have separate entries. Repeated links to the same named component should be consolidated, not submitted as new listings.

## Choose a contribution

- **Add a listing:** a public repository for a useful AI skill, agent, framework or related tool, with a direct source for the specific component.
- **Correct a listing:** identify its stable ID and provide evidence for the revised source, category, type, license or other metadata.
- **Report a removal:** explain a duplicate, dead or private source, rights concern, archived project or other inclusion problem. A single failed network request is not evidence of permanent removal.
- **Improve maintenance:** propose changes to the generator, documentation, validation or contribution workflow.

Use the [issue templates](https://github.com/ravisingh11/agentbay-ultimate-list/issues/new/choose) for suggestions. Maintainers review public evidence before accepting data changes. For sensitive reports, follow [SECURITY.md](SECURITY.md).

## Maintained inputs and generated outputs

The accepted list is retained in root `catalog.json`. Future AgentBay imports add new entries and update factual metadata. Reviewed changes in [`data/curation.json`](data/curation.json) are applied afterward, so a website import cannot overwrite them. An entry missing from the next import remains available until its removal is reviewed.

Edit curation inputs, then regenerate the outputs together. Do not independently edit generated descriptions, CSVs, subset JSON, browsing pages, summary/alias provenance or `sync-manifest.json`. All six downloads share one schema and one record set. See [maintenance](docs/maintenance.md) for the import policy. Keep execution traces, temporary projects and local validation output outside the checkout. Include the tested revision and observed results in your pull request; retain catalogue source provenance and stable-ID aliases.

Hand-maintained documentation can be edited directly. The root README, browsing pages under `skills/` and `projects/`, and `docs/providers.md` are generated; change their rendering in `scripts/catalog.py` instead. The official-owner registry is maintained separately in [`data/preferred-providers.json`](data/preferred-providers.json).

### Contribute to AgentBay Skill Installer

[`skills/agentbay-skill-installer/SKILL.md`](skills/agentbay-skill-installer/SKILL.md) is a maintained source file inside the otherwise generated skills browsing directory. Edit it directly in a focused pull request. The website copy is published from an approved repository revision; do not edit that copy independently.

Follow [installer maintenance](docs/installer-maintenance.md) for source validation, the clean Codex install-and-use test and the stage/deploy/verify publication procedure. Run `python3 scripts/installer.py check` alongside the regular pull-request checks below. Changes to the skill instructions also need the full install-and-use check; CI's credential-free install/discovery job does not validate task execution. Include the tested revision or source hash and results in the pull request. Maintainers publish the approved revision after review.

## Add a record

Add an entry to the `additions` array in `data/curation.json`. Use a new UUID prefixed with `community:`; generate it with `python3 -c 'import uuid; print("community:"+str(uuid.uuid4()))'`. Keep that ID unchanged in subsequent corrections.

The following is a structural example. Replace the placeholders and date with real public evidence before submitting it:

```json
{
  "id": "community:REPLACE-WITH-A-UUID",
  "fields": {
    "name": "Project name",
    "type": "Skill",
    "website_url": "https://github.com/OWNER/REPOSITORY/blob/COMMIT/skills/NAME/SKILL.md",
    "repository_url": "https://github.com/OWNER/REPOSITORY",
    "categories": ["Software development"],
    "tags": ["Python", "SKILL.md"],
    "license": "",
    "license_scope": "",
    "repository_archived": false,
    "repository_status_checked_at": null
  },
  "evidence": [
    {
      "url": "https://github.com/OWNER/REPOSITORY",
      "checked_at": "2026-10-25",
      "note": "Replace with what you verified: repository identity, public/active state and the specific skill path."
    }
  ]
}
```

A record needs `name`, `type`, `website_url`, `repository_url`, `categories` and `tags`. Unknown licenses remain empty strings and unknown statistics or status timestamps remain null. Do not invent check dates, licenses, star counts or compatibility claims.

Use `Skill` for a specific reusable instruction package, `Skill Repository` for a repository of skills, or `Skill Collection` for a curated collection. Cite an actual `SKILL.md` path when claiming an individual skill exists. Other supported types include `Framework`, `Tool`, `Project` and `Agent Example`; types starting with “skill”, ignoring case, enter the skills subset.

Choose a specific purpose category already present in the list where possible. Framework names and technologies belong in tags. Keep spelling consistent. The first nonempty category controls the browsing location; the complete category and tag arrays remain in the downloads.

Descriptions and use cases are generated from structured facts using original templates. Supply capability evidence in the review; do not paste publisher marketing text into generated summaries. If the current vocabulary cannot represent an important capability, propose an improvement to the documented summary policy.

## Correct an existing record

Find its `id` in the JSON download. Check [`provenance/aliases.json`](provenance/aliases.json) if an older ID has been consolidated. Add a `corrections` entry using the retained ID:

```json
{
  "id": "EXISTING-ID",
  "fields": {
    "categories": ["Browser automation"],
    "tags": ["Playwright"]
  },
  "evidence": [
    {
      "url": "https://github.com/OWNER/REPOSITORY",
      "checked_at": "2026-10-25",
      "note": "Explain how the linked source supports this correction."
    }
  ]
}
```

Allowed correction fields are `name`, `type`, `website_url`, `repository_url`, `categories`, `tags`, `license`, `license_scope`, `repository_archived`, `repository_status_checked_at`, `github_stars` and `github_stars_checked_at`. IDs and generated summaries/attribution cannot be overridden. A changed description or recommendation alone is not a supported correction.

If there is already a correction for an ID, update that entry and preserve its relevant evidence instead of adding a second one. Corrections remain effective on future imports until intentionally revised or removed.

## Exclude a record

Add an entry to `exclusions` with `id`, `reason` and an `evidence` array in the same format. Explain the decision precisely. Exclusions are explicit maintainer decisions; website UI changes and temporary source outages do not silently remove records here. For duplicate components, prefer consolidation with a retained ID and metadata rather than dropping provenance.

## Official publisher attribution

The registry matches verified GitHub owners, not repository names or self-declared labels. When a source matches, the generated listing shows **Provider · Official source** and sets `preferred_provider` to the verified provider name. The `recommended` compatibility field remains false; use `preferred_provider` for verified publisher attribution. Neither label establishes quality, security, affiliation with AgentBay or suitability for a particular task.

To change an owner, provide an official provider page linking the GitHub organization or equivalent ownership evidence. Do not add a community fork as an official source. Registry changes need maintainer review and coordination with AgentBay's published policy.

The website finder has its own eligibility rules: preferred official sources have no star/fork minimum; community finder repositories need 5,000 stars or 2,000 forks. This broader catalogue also contains repository and collection listings. Do not apply finder counts or eligibility to the whole catalogue.

## Prepare a pull request

1. Fork and clone the repository when forking is available, or use an authorized branch as an invited collaborator. Create a branch for one focused change. While this repo is private, access requires an invitation; these guidelines do not grant access.
2. Edit the maintained input or documentation and include public supporting evidence. Use your own factual wording.
3. Regenerate and validate with Python 3.9+; no third-party Python packages or AgentBay checkout are required:

   ```sh
   python3 scripts/catalog.py render
   python3 scripts/catalog.py check
   python3 -m unittest discover -s tests -v
   ```

4. Review the diff. Check the affected records, category pages, counts and ID aliases. Generated files are included so reviewers and download users see the proposed result immediately.
5. Submit a pull request describing the problem, evidence, changed IDs and validation performed. Keep unrelated formatting or metadata changes out of it.

Regular contributor validation is offline. You do not need to run a live import or refresh thousands of repository statistics for a focused correction. CI validates the inputs, reproducible outputs and maintenance behavior without executing any linked skill.

If you change the Cloudflare example or the repository license, regenerate its small downloadable ZIP with `python3 scripts/example_bundle.py build`, then run `python3 scripts/example_bundle.py check`. The ZIP includes only the maintained example, its original file manifest and the MIT license; do not add local settings or dependency folders. CI checks the download against its sources. See the [example bundle maintenance instructions](docs/installer-maintenance.md#maintain-the-example-download).

Maintainers may request clearer evidence, merge related proposals, or decline listings outside the catalogue's purpose. Acceptance does not promise promotion on the website or any usage level. Website application changes belong in AgentBay's application workflow, not this data repository.

## Maintainer review

Every normal change to the default branch goes through a pull request. [CODEOWNERS](.github/CODEOWNERS) assigns all paths, including workflows, policy and the ownership file, to `@ravisingh11` for review. External contributor PRs need the owner's approval before merge. New commits after review need another look at the updated diff and checks.

Use the PR template to explain **why**, the resulting behavior, where to review, observed verification, documentation and risk/rollback. Link the issue when one exists. Propose broad schema, provider-policy, installer-permission or workflow changes in an issue before implementing them; small corrections can go straight to a focused PR.

AI-assisted contributions are welcome. You remain responsible for the source, rights, generated output and checks. Explain material use of AI or generated content and what you independently inspected. Agents using owner credentials must not approve or merge an external contributor's PR without the owner's explicit instruction. Passing CI or a Proof decision is not merge, deployment or publication authorization.

> [!IMPORTANT]
> Owner approval is the repository's review policy. GitHub branch-rule enforcement is currently unavailable under this private repository's account plan. `CODEOWNERS` routes review after it reaches the base branch; it does not, by itself, block merges. See [the current guardrails and their limits](docs/guardrails.md).

Keep contributor CI separate from privileged operations. The catalogue workflow uses read-only repository permissions and does not execute linked publisher skills. Credential-free installation runs in an isolated test environment. Model-backed tests, authenticated source access and website publication are maintainer operations: never send contributor code, private files or secrets to a service without an explicit, reviewed reason. Do not introduce `pull_request_target` execution of contributor-controlled code with secrets or write credentials.

Changes to secret-scan exceptions need a concrete false-positive explanation and must pass `python3 scripts/check_secret_scan_policy.py` with Git/Docker. Keep default detection and full-history scanning enabled; see the [reviewed CSV exception](docs/guardrails.md#a-narrow-tested-secret-scan-exception).

These practices are adapted from [AI Software Toolkit's contribution guidance](https://github.com/ravisingh11/ai-software-toolkit/blob/main/CONTRIBUTING.md), with AgentBay's catalogue and installer boundaries retained.

## Rights, privacy and conduct

Original contributions are accepted under this repository's [MIT License](LICENSE). You retain your copyright; no assignment is required. Identify third-party content and its permissions. A project's software license does not automatically grant permission to reuse its branding or website prose; see [LICENSING.md](LICENSING.md).

Share only public information you are authorized to contribute. Exclude credentials, account exports, private notes, personal contact details and private repositories. Do not execute a discovered skill or send it project data merely to verify a listing.

Follow the [community conduct policy](CODE_OF_CONDUCT.md): be respectful, discuss evidence and behavior, and disclose material affiliations when proposing your own project. It explains moderation and private conduct reporting. Use [SECURITY.md](SECURITY.md) for sensitive security or privacy concerns.
