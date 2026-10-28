#!/usr/bin/env python3
"""Validate, stage and verify the first-party installer skill. No third-party packages."""
import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
NAME = 'agentbay-skill-installer'
RELATIVE = pathlib.Path('skills')/NAME/'SKILL.md'
PUBLIC_URL = 'https://agentbay.io/'+RELATIVE.as_posix()
CLI_VERSION = '1.7.4'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def validate(raw):
    text = raw.decode('utf-8')
    if not text.startswith('---\n') or '\n---\n' not in text[4:]:
        raise ValueError('Skill requires YAML frontmatter')
    frontmatter, body = text[4:].split('\n---\n', 1)
    names = re.findall(r'^name: (.+)$', frontmatter, re.M)
    descriptions = re.findall(r'^description: (.+)$', frontmatter, re.M)
    if names != [NAME] or len(descriptions) != 1 or not descriptions[0].strip() or not body.strip():
        raise ValueError('Invalid installer name, description or body')
    return {'name': NAME, 'sha256': digest(raw), 'bytes': len(raw)}


def source(revision=None, root=ROOT):
    if revision:
        commit = subprocess.check_output(['git','rev-parse','--verify',revision+'^{commit}'],cwd=root,text=True).strip()
        raw = subprocess.check_output(['git','show',commit+':'+RELATIVE.as_posix()],cwd=root)
    else:
        commit = 'working-tree'
        raw = (root/RELATIVE).read_bytes()
    validate(raw)
    return raw, commit


def manifest(raw, revision):
    return {'schema_version':1, **validate(raw),
            'source_repository':'https://github.com/ravisingh11/agentbay-ultimate-list',
            'source_path':RELATIVE.as_posix(), 'source_revision':revision,
            'candidate_only':revision=='working-tree',
            'skills_cli_version':CLI_VERSION, 'minimum_node_version':'22.20.0'}


def verify(raw, metadata, expected=None, revision=None):
    actual = validate(raw)
    if metadata.get('schema_version') != 1 or any(metadata.get(k) != actual[k] for k in actual):
        raise ValueError('Skill and release metadata differ')
    recorded_revision=metadata.get('source_revision')
    if not isinstance(recorded_revision,str) or not (recorded_revision=='working-tree' or re.fullmatch(r'[0-9a-f]{40}',recorded_revision)):
        raise ValueError('Invalid recorded source revision')
    if metadata != manifest(raw,recorded_revision):
        raise ValueError('Unexpected installer provenance or compatibility metadata')
    if expected is not None and raw != expected:
        raise ValueError('Published skill differs from the selected source revision')
    if revision is not None and metadata.get('source_revision') != revision:
        raise ValueError('Release metadata names a different source revision')
    return actual


def safe_target(output, path):
    target = output/path
    for part in [target]+list(target.parents):
        if part.is_symlink():
            raise ValueError('Refusing to stage through symlink: '+str(part))
    if target.resolve() == (ROOT/RELATIVE).resolve():
        raise ValueError('Publication output must not overwrite the maintained source')
    return target


def stage(output, raw, revision):
    output=output.resolve()
    metadata = manifest(raw, revision)
    paths = {RELATIVE:raw, RELATIVE.parent/'release.json':(json.dumps(metadata,indent=2)+'\n').encode()}
    for path in paths:
        target = safe_target(output,path)
        if target.name=='SKILL.md' and target.exists():
            validate(target.read_bytes())
        if target.exists() and target.name=='release.json':
            previous = json.loads(target.read_bytes())
            if previous.get('name') != NAME:
                raise ValueError('Preserving an unrelated release file')
        temporary = target.with_name('.'+target.name+'.tmp')
        if temporary.exists() or temporary.is_symlink():
            raise ValueError('Preserving an existing temporary output: '+str(temporary))
    for path, payload in paths.items():
        target = output/path
        target.parent.mkdir(parents=True,exist_ok=True)
        temporary = target.with_name('.'+target.name+'.tmp')
        with temporary.open('xb') as stream:stream.write(payload)
        temporary.replace(target)
    verify((output/RELATIVE).read_bytes(), json.loads((output/RELATIVE.parent/'release.json').read_bytes()),raw,revision)
    return metadata


def fetch(url):
    with urllib.request.urlopen(url,timeout=30) as response:
        if response.status != 200:raise ValueError('Publication did not return HTTP 200')
        return response.read()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['check','stage','verify'])
    parser.add_argument('--output',type=pathlib.Path,help='Staged website public root')
    parser.add_argument('--revision',help='Approved source commit or ref; required for publication')
    parser.add_argument('--candidate',action='store_true',help='Use working-tree source for isolated testing, not publication')
    parser.add_argument('--url',help='Published SKILL.md URL; verify also reads adjacent release.json')
    args=parser.parse_args()
    if args.revision and args.candidate:parser.error('Choose a revision or a working-tree candidate')
    if args.command=='check':
        if args.output or args.url or args.revision or args.candidate:parser.error('check validates the maintained working-tree skill')
        print(json.dumps(validate((ROOT/RELATIVE).read_bytes()),indent=2));return
    if not args.revision and not args.candidate:parser.error('Choose --revision or --candidate explicitly')
    raw,revision=source(args.revision)
    if args.command=='stage':
        if not args.output or args.url:parser.error('stage requires --output and does not fetch a URL')
        result=stage(args.output,raw,revision)
    else:
        if bool(args.output)==bool(args.url):parser.error('verify requires exactly one of --output or --url')
        if args.url:
            actual=fetch(args.url)
            metadata=json.loads(fetch(args.url.rsplit('/',1)[0]+'/release.json'))
        else:
            actual=(args.output/RELATIVE).read_bytes()
            metadata=json.loads((args.output/RELATIVE.parent/'release.json').read_bytes())
        result=verify(actual,metadata,raw,revision)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
