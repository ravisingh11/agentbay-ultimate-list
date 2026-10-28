"""Event boundaries must not promote PR evidence to a merged revision."""
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ci_context', ROOT / 'scripts/ci_context.py')
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)
HEAD, BASE, MERGE = 'a' * 40, 'b' * 40, 'c' * 40


def pr_event():
    return {'action': 'synchronize', 'pull_request': {
        'number': 12, 'head': {'sha': HEAD}, 'base': {'sha': BASE}}}


def push_event():
    return {'ref': 'refs/heads/main', 'before': BASE, 'after': MERGE, 'deleted': False}


class CIContextTests(unittest.TestCase):
    def test_pr_records_head_separately_from_synthetic_event_revision(self):
        result = ci.context('pull_request', pr_event(), 'refs/pull/12/merge', MERGE, HEAD)
        self.assertEqual(result['tested_revision'], HEAD)
        self.assertEqual(result['event_revision'], MERGE)
        self.assertEqual(result['comparison_base'], BASE)
        self.assertEqual(result['checkpoint'], 'PR review readiness')

    def test_main_push_records_actual_result_and_entire_push_baseline(self):
        result = ci.context('push', push_event(), 'refs/heads/main', MERGE, MERGE)
        self.assertEqual(result['tested_revision'], MERGE)
        self.assertEqual(result['comparison_base'], BASE)
        self.assertNotIn('pr_head', result)

    def test_wrong_checkout_is_rejected_for_both_events(self):
        for args in [('pull_request', pr_event(), 'refs/pull/12/merge', MERGE, MERGE),
                     ('push', push_event(), 'refs/heads/main', MERGE, HEAD)]:
            with self.subTest(event=args[0]), self.assertRaises(ValueError):
                ci.context(*args)

    def test_invalid_push_payloads_and_missing_baselines_are_rejected(self):
        for change in [{'before': '0' * 40}, {'before': 'main\nunsafe'},
                       {'after': HEAD}, {'ref': 'refs/heads/other'}, {'deleted': True}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                ci.context('push', {**push_event(), **change}, 'refs/heads/main', MERGE, MERGE)

    def test_first_push_requires_both_creation_event_and_actual_root_commit(self):
        event = {**push_event(), 'before': '0' * 40, 'created': True}
        result = ci.context('push', event, 'refs/heads/main', MERGE, MERGE, is_root=True)
        self.assertEqual(result['comparison_mode'], 'initial-tree')
        self.assertEqual(result['comparison_base'], '')
        self.assertEqual(result['checkpoint'], 'Initial main publication')
        for changed, root in [(event, False), ({**event, 'created': False}, True)]:
            with self.subTest(root=root), self.assertRaises(ValueError):
                ci.context('push', changed, 'refs/heads/main', MERGE, MERGE, is_root=root)

    def test_mismatched_pr_and_privileged_events_are_rejected(self):
        with self.assertRaises(ValueError):
            ci.context('pull_request', pr_event(), 'refs/pull/13/merge', MERGE, HEAD)
        with self.assertRaises(ValueError):
            ci.context('pull_request_target', pr_event(), 'refs/heads/main', BASE, BASE)

    def test_manual_invocation_stays_explicit(self):
        result = ci.context('workflow_dispatch', {}, 'refs/heads/main', HEAD, HEAD)
        self.assertEqual(result['checkpoint'], 'Explicit manual verification')
        self.assertEqual(result['tested_revision'], HEAD)
        root = ci.context('workflow_dispatch', {}, 'refs/heads/main', HEAD, HEAD, is_root=True)
        self.assertEqual(root['checkpoint'], 'Explicit manual verification')
        self.assertEqual(root['comparison_mode'], 'initial-tree')

    def test_output_does_not_include_unrelated_payload_data_or_claim_pass(self):
        event = pr_event()
        event['account_details'] = 'PRIVATE_SENTINEL'
        result = ci.context('pull_request', event, 'refs/pull/12/merge', MERGE, HEAD)
        with tempfile.TemporaryDirectory() as directory:
            summary, output = [pathlib.Path(directory) / f for f in ['summary', 'output']]
            ci.record(result, summary, output)
            self.assertNotIn('PRIVATE_SENTINEL', summary.read_text())
            self.assertIn('check result is reported separately', summary.read_text())
            self.assertEqual(output.read_text(), f'comparison_base={BASE}\n')

    def test_cli_binds_real_git_checkout_and_rejects_event_mismatch_without_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            subprocess.run(['git', '-C', str(root), '-c', 'user.name=CI Fixture',
                            '-c', 'user.email=ci@example.invalid', 'commit', '--allow-empty',
                            '-qm', 'fixture'], check=True)
            actual = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                                             text=True).strip()
            event_path, summary, output = [root / f for f in ['event.json', 'summary', 'output']]
            event = {**push_event(), 'after': actual}
            event_path.write_text(json.dumps(event))
            env = {**os.environ, 'GITHUB_EVENT_NAME': 'push', 'GITHUB_REF': 'refs/heads/main',
                   'GITHUB_SHA': actual, 'GITHUB_EVENT_PATH': str(event_path),
                   'GITHUB_STEP_SUMMARY': str(summary), 'GITHUB_OUTPUT': str(output),
                   'GITHUB_RUN_ID': '123', 'GITHUB_RUN_ATTEMPT': '2',
                   'GITHUB_WORKFLOW': 'CI Fixture', 'GITHUB_JOB': 'fixture'}
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/ci_context.py')],
                                    cwd=root, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['tested_revision'], actual)
            self.assertEqual(json.loads(result.stdout)['run_attempt'], '2')
            event_path.write_text(json.dumps({**event, 'before': '0' * 40, 'created': True}))
            initial = subprocess.run([sys.executable, str(ROOT / 'scripts/ci_context.py')],
                                     cwd=root, env=env, capture_output=True, text=True)
            self.assertEqual(initial.returncode, 0, initial.stderr)
            self.assertEqual(json.loads(initial.stdout)['comparison_mode'], 'initial-tree')
            self.assertIn('comparison_mode=initial-tree', output.read_text())
            before = summary.read_bytes(), output.read_bytes()
            event_path.write_text(json.dumps(push_event()))
            failed = subprocess.run([sys.executable, str(ROOT / 'scripts/ci_context.py')],
                                    cwd=root, env={**env, 'GITHUB_SHA': MERGE},
                                    capture_output=True, text=True)
            self.assertNotEqual(failed.returncode, 0)
            self.assertEqual(before, (summary.read_bytes(), output.read_bytes()))


if __name__ == '__main__':
    unittest.main()
