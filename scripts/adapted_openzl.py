#!/usr/bin/env python3
"""Build or verify the attributed OpenZL skill download, without executing it."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAME = 'agentbay-openzl-benchmark-scenarios'
MEMBERS = {'SKILL.md', 'LICENSE', 'NOTICE.txt', 'provenance.json',
           'agents/openai.yaml', 'references/build-and-verify.md',
           'references/scenario-patterns.md', 'scripts/prepare_data.py'}


def outputs(root=ROOT):
    folder = root / 'skills' / NAME
    paths = sorted(folder.rglob('*'))
    if folder.is_symlink() or any(p.is_symlink() for p in paths):
        raise ValueError('Symlinks are not package inputs')
    files = {p.relative_to(folder).as_posix(): p for p in paths if p.is_file()}
    if set(files) != MEMBERS:
        raise ValueError('Unexpected or missing OpenZL package file')
    provenance = json.loads(files['provenance.json'].read_text())
    for record in provenance['adapted_files']:
        raw = files[record['path']].read_bytes()
        if hashlib.sha256(raw).hexdigest() != record['sha256'] or len(raw) != record['bytes']:
            raise ValueError('Stale adapted file provenance')
    if provenance['adaptation_publisher'] != 'AgentBay' or provenance['official_meta_distribution']:
        raise ValueError('Adaptation attribution changed')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, path in sorted(files.items()):
            info = zipfile.ZipInfo(NAME + '/' + name, date_time=(2026, 11, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o100755 if name == 'scripts/prepare_data.py' else 0o100644) << 16
            archive.writestr(info, path.read_bytes())
    raw = buffer.getvalue()
    path = 'downloads/' + NAME + '.zip'
    manifest = {'path': path, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                'publisher': 'AgentBay', 'official_meta_distribution': False,
                'files': {name: hashlib.sha256(p.read_bytes()).hexdigest() for name, p in files.items()}}
    return {path: raw, 'downloads/adapted-openzl-manifest.json':
            (json.dumps(manifest, indent=2) + '\n').encode()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['build', 'check'])
    args = parser.parse_args()
    for name, raw in outputs().items():
        target = ROOT / name
        if target.is_symlink():
            raise ValueError('Refusing symlink output')
        if args.command == 'build':
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(raw)
        elif not target.is_file() or target.read_bytes() != raw:
            raise ValueError('Stale OpenZL download: ' + name)
    print('Attributed OpenZL download: ' + args.command + ' passed')


if __name__ == '__main__':
    main()
