#!/usr/bin/env python3
"""Record an invocation's actual checkout identity; never reports a check pass."""
import json
import os
from pathlib import Path
import re
import subprocess


def commit(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{40}', value) or value == '0' * 40:
        raise ValueError('A nonzero full commit SHA is required')
    return value


def context(event_name, event, ref, event_sha, checkout_sha, is_root=False):
    """Bind PR checks to the head and main-push checks to the resulting commit."""
    checkout_sha = commit(checkout_sha)
    result = {'event': event_name, 'ref': ref, 'event_revision': commit(event_sha),
              'tested_revision': checkout_sha}
    if event_name == 'pull_request':
        pr = event['pull_request']
        head, base = commit(pr['head']['sha']), commit(pr['base']['sha'])
        number = pr['number']
        action = event['action']
        if type(number) is not int or number <= 0 or ref != f'refs/pull/{number}/merge':
            raise ValueError('PR identity and event ref must agree')
        if action not in {'opened', 'synchronize', 'reopened'}:
            raise ValueError('Unsupported source-check PR action')
        result.update(checkpoint='PR review readiness', expected_revision=head,
                      comparison_base=base, pr_head=head, pr_base=base, action=action)
    elif event_name == 'push':
        if ref != 'refs/heads/main' or event.get('ref') != ref or event.get('deleted') is not False:
            raise ValueError('Only a live main-branch push is supported')
        after = commit(event['after'])
        if after != result['event_revision']:
            raise ValueError('Push payload and event revision must agree')
        if event['before'] == '0' * 40:
            if event.get('created') is not True or not is_root:
                raise ValueError('Only a verified root commit can use an initial-tree comparison')
            result.update(checkpoint='Initial main publication', expected_revision=after,
                          comparison_base='', comparison_mode='initial-tree')
        else:
            before = commit(event['before'])
            result.update(checkpoint='Post-merge/main validation', expected_revision=after,
                          comparison_base=before)
    elif event_name == 'workflow_dispatch':
        result.update(checkpoint='Explicit manual verification',
                      expected_revision=result['event_revision'], comparison_base='HEAD~1')
        if is_root:
            result.update(comparison_base='', comparison_mode='initial-tree')
    else:
        raise ValueError('Unsupported source-check event')
    if checkout_sha != result['expected_revision']:
        raise ValueError('Checkout does not match the revision for this event')
    # Do not echo arbitrary event fields, titles, account data or credentials.
    return result


def record(result, summary_path, output_path):
    rows = ['## Check invocation', '',
            *[f'- **{key.replace("_", " ")}:** `{value}`' for key, value in result.items()],
            '- Invocation context only; the check result is reported separately.', '']
    with Path(summary_path).open('a', encoding='utf-8') as summary:
        summary.write('\n'.join(rows))
    with Path(output_path).open('a', encoding='utf-8') as output:
        output.write(f'comparison_base={result["comparison_base"]}\n')
        if result.get('comparison_mode') == 'initial-tree':
            output.write('comparison_mode=initial-tree\n')


def main():
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text(encoding='utf-8'))
    checkout = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    is_root = not subprocess.check_output(['git', 'show', '-s', '--format=%P', 'HEAD'],
                                         text=True).strip()
    result = context(os.environ['GITHUB_EVENT_NAME'], event, os.environ['GITHUB_REF'],
                     os.environ['GITHUB_SHA'], checkout, is_root=is_root)
    run_id, attempt = os.environ['GITHUB_RUN_ID'], os.environ['GITHUB_RUN_ATTEMPT']
    if not run_id.isdigit() or not attempt.isdigit():
        raise ValueError('Invalid run identity')
    result.update(workflow=os.environ['GITHUB_WORKFLOW'], job=os.environ['GITHUB_JOB'],
                  run_id=run_id, run_attempt=attempt)
    record(result, os.environ['GITHUB_STEP_SUMMARY'], os.environ['GITHUB_OUTPUT'])
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError):
        raise SystemExit('CI invocation could not be bound to the expected checkout')
