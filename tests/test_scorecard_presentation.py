"""Keep recorded examples separate from current policy results and subjects."""
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('agentbay_badge', ROOT / '.proof/render_scorecard_badge.py')
BADGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BADGE)
FACTS = json.loads((ROOT / 'tests/fixtures/scorecard-checkpoints.json').read_text())
REPOSITORY = 'ravisingh11/agentbay-ultimate-list'


class ScorecardPresentationTests(unittest.TestCase):
    def test_pr_and_main_examples_match_independently_recorded_subjects(self):
        self.assertTrue(FACTS['merged'])
        self.assertNotEqual(FACTS['head'], FACTS['merge_commit'])
        for example in BADGE._AGENTBAY_CHECKPOINT_EXAMPLES:
            facts = FACTS[example['id']]
            self.assertEqual(example['revision'], facts['head_sha'])
            self.assertEqual(example['run_id'], facts['id'])
            self.assertEqual(example['created_at'], facts['created_at'])
            self.assertEqual(example['run_attempt'], facts['run_attempt'])
            self.assertEqual({row[0] for row in example['checks']}, set(facts['checks']))
            for identifier, _, status, url in example['checks']:
                self.assertEqual((status, url), (facts['checks'][identifier]['status'], facts['checks'][identifier]['url']))
        self.assertEqual(FACTS['pr']['head_sha'], FACTS['head'])
        self.assertEqual(FACTS['main']['head_sha'], FACTS['merge_commit'])
        self.assertEqual(FACTS['pr']['event'], 'pull_request_target')
        self.assertEqual(FACTS['main']['event'], 'push')

    def test_gallery_uses_agentbay_evidence_without_borrowing_other_repositories(self):
        page = BADGE._checkpoint_examples_html(REPOSITORY)
        self.assertEqual(page.count('<article class="checkpoint-card '), 2)
        self.assertIn('PR #4 and the main commit produced by its merge', page)
        self.assertIn('separate from the latest PR scorecard below', page)
        self.assertIn('There is no combined score', page)
        self.assertNotIn('/ai-software-toolkit/actions/', page)
        self.assertNotIn('/ai-software-toolkit-reference-app/actions/', page)
        self.assertIn('Failed · advisory', page)
        main = page.split('id="checkpoint-main-example"', 1)[1]
        self.assertNotIn('data-example-check="pr-metadata"', main)
        self.assertNotIn('data-example-check="change-scope"', main)
        self.assertIn('pull_request + pull_request_target', page)
        self.assertIn('push: refs/heads/main', main)
        self.assertIn('not a Proof policy score', main)

    def test_missing_or_blocked_example_results_never_become_passes(self):
        pr, main = BADGE._AGENTBAY_CHECKPOINT_EXAMPLES
        changed = {**pr, 'checks': (('absent', 'Missing', 'no_result', 'https://example.com'),
                                   ('blocked', 'Blocked', 'blocked', 'https://example.com'))}
        with patch.object(BADGE, '_AGENTBAY_CHECKPOINT_EXAMPLES', (changed, main)):
            page = BADGE._checkpoint_examples_html(REPOSITORY).split('</article>', 1)[0]
        self.assertIn('Unverified · advisory', page)
        self.assertIn('Blocked · advisory', page)
        self.assertNotIn('Passed', page)

    def test_explanation_is_short_and_definitions_are_closed_by_default(self):
        page = BADGE._controls_html([], 'https://example.com', {'availability': 'unavailable'})
        intro = re.search(r'<p class="checks-intro">(.*?)</p>', page).group(1)
        self.assertLessEqual(len(intro.split()), 30)
        self.assertIn('does not mean the check ran or passed', intro)
        help_box = re.search(r'<details class="checks-help">(.*?)</details>', page, re.S).group(1)
        self.assertIn('<summary>How to read these results</summary>', help_box)
        for definition in ['Not configured means', 'Not reported means', 'A dash means', 'selection could not be validated', 'activation-summary']:
            self.assertIn(definition, help_box)
        self.assertNotIn('<details class="checks-help" open', page)

    def test_historical_examples_do_not_change_latest_score_or_json(self):
        card = {'version': 2, 'status': 'GREEN', 'decision': 'allow', 'policy': 'test-policy',
                'operation': 'change', 'subject': {'type': 'git-commit', 'revision': 'a' * 40},
                'enforced': {'passed': 0, 'total': 0, 'percent': None},
                'advisory': {'passed': 1, 'total': 1, 'percent': 100.0},
                'controls': [{'id': 'private-control', 'provider': 'secret-provider'}],
                'findings': [{'message': 'PRIVATE_FINDING'}]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            source.mkdir()
            (source / 'scorecard-20261029-150000Z.json').write_text(json.dumps(card))
            (source / 'scorecard-20261029-150000Z.md').write_text('PRIVATE_MARKDOWN')
            result = BADGE.render_badge(source, root / 'output', REPOSITORY, 12345, 1,
                                       f'https://github.com/{REPOSITORY}/actions/runs/12345/attempts/1',
                                       '2026-10-29T15:00:00Z', 'a' * 40)
            published = json.loads((root / 'output/scorecard.json').read_text())
            page = (root / 'output/index.html').read_text()
        self.assertEqual((published['passed'], published['total']), (1, 1))
        self.assertEqual(result['message'], 'GREEN 1/1')
        self.assertNotIn('checkpoint_examples', published)
        self.assertNotIn('PRIVATE_FINDING', page)
        self.assertNotIn('PRIVATE_MARKDOWN', page)
        self.assertLess(page.index('id="checkpoint-examples-title"'), page.index('id="scorecard"'))


if __name__ == '__main__':
    unittest.main()
