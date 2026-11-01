#!/usr/bin/env python3
"""Build/check the two maintained AgentBay adaptation downloads without execution."""
import argparse
import hashlib
import io
import json
import pathlib
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
NAMES = ('agentbay-fboss-link-log-analysis', 'agentbay-fboss-qsfp-log-analysis')


def outputs(root=ROOT):
    result, manifest = {}, {}
    for name in NAMES:
        folder = root / 'skills' / name
        files = sorted(p for p in folder.rglob('*') if p.is_file())
        if any(p.is_symlink() for p in folder.rglob('*')):
            raise ValueError('Symlinks are not package inputs')
        required = {'SKILL.md', 'LICENSE', 'NOTICE.txt', 'provenance.json'}
        if not required <= {p.relative_to(folder).as_posix() for p in files}:
            raise ValueError('Incomplete attributed package: ' + name)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for file in files:
                entry = zipfile.ZipInfo(name + '/' + file.relative_to(folder).as_posix(),
                                        date_time=(2026, 10, 31, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.create_system = 3
                entry.external_attr = (0o100755 if file.suffix == '.sh' else 0o100644) << 16
                archive.writestr(entry, file.read_bytes())
        raw = buffer.getvalue()
        path = 'downloads/' + name + '.zip'
        result[path] = raw
        manifest[name] = {'path': path, 'bytes': len(raw),
                          'sha256': hashlib.sha256(raw).hexdigest(),
                          'publisher': 'AgentBay', 'official_meta_distribution': False}
    result['downloads/adapted-fboss-manifest.json'] = (
        json.dumps(manifest, indent=2) + '\n').encode()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['build', 'check'])
    args = parser.parse_args()
    for name, raw in outputs().items():
        target = ROOT / name
        if args.command == 'build':
            target.parent.mkdir(exist_ok=True)
            if target.is_symlink():
                raise ValueError('Refusing symlink output')
            target.write_bytes(raw)
        elif not target.exists() or target.read_bytes() != raw:
            raise ValueError('Stale adaptation download: ' + name)
    print('Two attributed adaptation downloads: ' + args.command + ' passed')


if __name__ == '__main__':
    main()
