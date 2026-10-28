#!/usr/bin/env python3
"""Exercise narrow CSV exceptions with the exact pinned CI Gitleaks producer.

Requires Git and Docker. Fixtures contain public names and a generated synthetic
sentinel; no credentials or user files are mounted into the container.
"""
import csv
import json
import pathlib
import re
import secrets
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent


def check():
    workflow = (ROOT / '.github/workflows/gitleaks.yml').read_text()
    images = set(re.findall(r'ghcr\.io/gitleaks/gitleaks@sha256:[0-9a-f]{64}', workflow))
    if len(images) != 1:
        raise ValueError('Expected one immutable Gitleaks image in the CI workflow')
    image = images.pop()
    names = ('fly0pants/admapix', 'normalled/apijack')
    artifacts = ROOT / '.artifacts'
    artifacts.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='secret-policy-', dir=artifacts) as directory:
        base = pathlib.Path(directory)
        fixture = base / 'repo'; fixture.mkdir()
        reports = base / 'reports'; reports.mkdir()
        (fixture / '.gitleaks.toml').write_bytes((ROOT / '.gitleaks.toml').read_bytes())

        def git(*args):
            result = subprocess.run(['git', '-c', 'user.name=AgentBay policy test',
                            '-c', 'user.email=policy-test@example.invalid', *args],
                           cwd=fixture, check=True, capture_output=True)
            return result.stdout.decode().strip()

        def write_csv(relative, sentinel=None):
            target = fixture / relative; target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('w', newline='') as stream:
                writer = csv.writer(stream)
                writer.writerow(['id', 'name', 'description'])
                for number, name in enumerate(names):
                    description = name + ' Skill.'
                    if sentinel and number == 0:
                        description += ' api_key = ' + sentinel + ';'
                    writer.writerow([str(number), name, description])

        def scan(label):
            git('add', '.')
            git('commit', '-qm', label)
            revision = git('rev-parse', 'HEAD')
            result = subprocess.run([
                'docker', 'run', '--rm', '--network', 'none',
                '--mount', 'type=bind,source=' + str(fixture) + ',target=/repo,readonly',
                '--mount', 'type=bind,source=' + str(reports) + ',target=/report',
                '-w', '/repo', image, 'git', '--redact', '--no-banner',
                '--log-opts=-1 ' + revision, '--report-format', 'json',
                '--report-path', '/report/' + label + '.json', '.'],
                capture_output=True, text=True, timeout=120)
            if result.returncode not in (0, 1):
                raise ValueError('Gitleaks could not evaluate fixture: ' + label)
            report = reports / (label + '.json')
            if not report.is_file():
                raise ValueError('Gitleaks produced no fixture report: ' + label)
            findings = json.loads(report.read_text())
            return result.returncode, findings

        git('init', '-q')
        for path in ('catalog.csv', 'skills/catalog.csv'):
            write_csv(path)
        code, findings = scan('public-names')
        if code != 0 or findings:
            raise ValueError('The reviewed CSV names were not narrowly allowed')

        # A new credential-like value in the SAME row must still be detected.
        write_csv('catalog.csv', secrets.token_urlsafe(24))
        code, findings = scan('new-sentinel')
        if code != 1 or not any(f['RuleID'] == 'generic-api-key' and f['File'] == 'catalog.csv' for f in findings):
            raise ValueError('Default detection failed for a synthetic value in an allowed CSV row')

        # The same names outside the two allowed paths must retain normal checks.
        write_csv('other.csv')
        code, findings = scan('outside-path')
        if code != 1 or not any(f['RuleID'] == 'generic-api-key' and f['File'] == 'other.csv' for f in findings):
            raise ValueError('The CSV exception escaped its two allowed paths')
        # Naming fixtures in this helper is allowed; credentials in it are not.
        helper = fixture / 'scripts/check_secret_scan_policy.py'
        helper.parent.mkdir()
        helper.write_text('api_key = ' + secrets.token_urlsafe(24) + '\n')
        code, findings = scan('helper-sentinel')
        if code != 1 or not any(f['RuleID'] == 'generic-api-key' and f['File'] == 'scripts/check_secret_scan_policy.py' for f in findings):
            raise ValueError('The fixture-source exception suppressed a new synthetic value')
    print('Gitleaks policy passed: public names allowed; CSV/helper sentinels and other paths detected.')


if __name__ == '__main__':
    check()
