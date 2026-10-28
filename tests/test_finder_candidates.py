import base64
import datetime
import hashlib
import importlib.util
import pathlib
import unittest

spec = importlib.util.spec_from_file_location('finder_candidates', pathlib.Path(__file__).resolve().parents[1] / 'scripts/finder_candidates.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
RAW = b'---\nname: worker\ndescription: Diagnose Workers.\n---\nRead the project.\n'
BLOB = hashlib.sha1(b'blob ' + str(len(RAW)).encode() + b'\0' + RAW).hexdigest()
SKILL = {'repository': 'cloudflare/skills', 'commit': 'a' * 40, 'path': 'skills/worker/SKILL.md', 'blob': BLOB, 'name': 'worker'}
POLICY = {'providers': [{'github_owners': ['cloudflare']}]}
CURATION = {'additions': [], 'corrections': [], 'exclusions': []}
META = {'full_name': 'cloudflare/skills', 'private': False, 'archived': False, 'disabled': False,
        'stargazers_count': 0, 'forks_count': 0, 'license': None}


class FinderCandidateTests(unittest.TestCase):
    def propose(self, skill=None, rows=None, curation=None, verify=None):
        return m.propose({'skills': [skill or SKILL], 'repositories': {}}, rows or [], curation or CURATION, POLICY,
                         verify=verify or (lambda _: META), now=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc))

    def test_official_zero_star_source_has_stable_id_and_unknown_license(self):
        a, report = self.propose(); b, _ = self.propose()
        self.assertEqual(a, b); self.assertEqual(a[0]['fields']['license'], '')
        self.assertEqual(report['automatic_removals'], 0)

    def test_existing_path_matches_across_upstream_revisions(self):
        url = 'https://github.com/cloudflare/skills/blob/main/skills/worker/SKILL.md'
        a, report = self.propose(rows=[{'id': 'keep', 'website_url': url}])
        self.assertEqual(a, []); self.assertEqual(report['duplicates_or_exclusions'], 1)

    def test_existing_skill_folder_is_not_duplicated_as_its_instruction_file(self):
        rows = [{'id': 'keep', 'website_url': 'https://github.com/cloudflare/skills/tree/main/skills/worker'}]
        self.assertEqual(self.propose(rows=rows)[0], [])

    def test_explicitly_inactive_new_candidate_is_deferred_without_removals(self):
        def unavailable(_): raise m.IneligibleSource('Archived')
        additions, report = self.propose(verify=unavailable)
        self.assertEqual(additions, []); self.assertEqual(report['deferred'], 1)
        self.assertEqual(report['automatic_removals'], 0)

    def test_excluded_source_cannot_return_with_a_new_uuid(self):
        source = 'https://github.com/cloudflare/skills/blob/main/skills/worker/SKILL.md'
        curation = {**CURATION, 'exclusions': [{'id': 'old-id', 'evidence': [{'url': source}]}]}
        self.assertEqual(self.propose(curation=curation)[0], [])

    def test_spoofed_provider_does_not_bypass_community_threshold(self):
        skill = {**SKILL, 'repository': 'community/cloudflare', 'publisher': 'Cloudflare'}
        self.assertEqual(self.propose(skill)[0], [])

    def test_corrupt_file_and_moved_repository_fail_inspection(self):
        def get(endpoint):
            if '/contents/' not in endpoint:
                return META
            return {'type': 'file', 'sha': BLOB, 'size': len(RAW), 'encoding': 'base64', 'content': base64.b64encode(RAW + b'x').decode()}
        with self.assertRaises(ValueError): m.inspect(SKILL, get)
        with self.assertRaises(ValueError): m.inspect(SKILL, lambda _: {**META, 'full_name': 'community/skills'})

    def test_actual_pinned_path_and_blob_are_checked(self):
        calls = []
        def get(endpoint):
            calls.append(endpoint)
            return META if '/contents/' not in endpoint else {'type': 'file', 'sha': BLOB, 'size': len(RAW), 'encoding': 'base64', 'content': base64.b64encode(RAW).decode()}
        self.assertEqual(m.inspect(SKILL, get), META)
        self.assertIn('?ref=' + 'a' * 40, calls[-1])

    def test_mirrored_blob_does_not_duplicate_a_retained_component(self):
        source = 'https://github.com/cloudflare/skills/blob/main/skills/worker/SKILL.md'
        index = {'skills': [{**SKILL, 'path': 'copies/worker/SKILL.md'}, SKILL], 'repositories': {}}
        rows = [{'id': 'retained', 'website_url': source}]
        additions, _ = m.propose(index, rows, CURATION, POLICY, verify=lambda _: META)
        self.assertEqual(additions, [])

    def test_malformed_source_and_rate_limit_do_not_mutate_inputs(self):
        for patch in [{'path': '../SKILL.md'}, {'commit': 'main'}, {'repository': 'evil.test/x?token=y'}]:
            with self.subTest(patch=patch), self.assertRaises(ValueError): self.propose({**SKILL, **patch})
        before = repr(CURATION)
        def fail(_): raise ValueError('rate limit')
        with self.assertRaises(ValueError): self.propose(verify=fail)
        self.assertEqual(repr(CURATION), before)
