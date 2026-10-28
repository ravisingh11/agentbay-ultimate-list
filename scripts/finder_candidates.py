#!/usr/bin/env python3
"""Propose public, pinned finder entries for review; never execute skill content."""
import base64
import datetime
import hashlib
import json
import re
import subprocess
import uuid
from urllib.parse import unquote, urlsplit

MAX_ADDITIONS = 50
REPOSITORY = re.compile(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z')
SHA = re.compile(r'[0-9a-f]{40}\Z')
EXCLUDED = {'test','tests','testdata','test-data','test_data','fixtures','template','templates','node_modules','vendor'}
NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, 'https://agentbay.io/verified-skill')


def component(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname != 'github.com' or parsed.username or parsed.password or parsed.query or parsed.fragment:
        return None
    parts = unquote(parsed.path).strip('/').split('/')
    if len(parts) < 5 or parts[2] not in ('blob', 'tree') or any(p in ('', '.', '..') for p in parts):
        return None
    return '/'.join(parts[:2]).casefold(), '/'.join(parts[4:])


def api(endpoint):
    result = subprocess.run(['gh', 'api', endpoint], capture_output=True, timeout=90)
    if result.returncode:
        raise ValueError('GitHub inspection failed; accepted data was not changed')
    return json.loads(result.stdout)


def inspect(skill, get=api):
    repo, commit, path, blob = (skill[k] for k in ('repository', 'commit', 'path', 'blob'))
    if not REPOSITORY.fullmatch(repo) or not SHA.fullmatch(commit) or not SHA.fullmatch(blob):
        raise ValueError('Invalid finder identity')
    if not (path == 'SKILL.md' or path.endswith('/SKILL.md')) or path.startswith('/') or any(p in ('', '.', '..') or p.casefold() in EXCLUDED for p in path.split('/')):
        raise ValueError('Unsafe finder source path')
    metadata = get('repos/' + repo)
    if metadata.get('full_name', '').casefold() != repo.casefold() or any(metadata.get(k) is not False for k in ('private', 'archived', 'disabled')):
        raise ValueError('Repository is unavailable, moved or inactive')
    # Resolve the path at the recorded commit, rather than trusting an unrelated blob.
    from urllib.parse import quote
    file = get('repos/' + repo + '/contents/' + quote(path, safe='/') + '?ref=' + commit)
    if file.get('type') != 'file' or file.get('sha') != blob or file.get('encoding') != 'base64' or file.get('size', 250001) > 250000:
        raise ValueError('Pinned skill file could not be verified')
    raw = base64.b64decode(file['content'], validate=False)
    if len(raw) != file.get('size') or hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() != blob:
        raise ValueError('Pinned skill bytes differ')
    text = raw.decode('utf-8')
    front = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', text, re.S)
    if not front or not re.search(r'^name:\s*[\'"]?' + re.escape(skill['name']) + r'[\'"]?\s*$', front[1], re.M):
        raise ValueError('Skill name does not match its pinned instructions')
    return metadata


def propose(index, rows, curation, providers, verify=inspect, now=None, limit=MAX_ADDITIONS):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    owners = {owner for p in providers['providers'] for owner in p['github_owners']}
    if not isinstance(index.get('skills'), list) or not index['skills'] or not isinstance(index.get('repositories'), dict):
        raise ValueError('Incomplete finder snapshot')
    known = {component(row['website_url']) for row in rows}
    known |= {component(entry['fields']['website_url']) for entry in curation['additions']}
    # Explicit exclusions cannot be reintroduced under a different generated ID.
    excluded = {component(e['url']) for entry in curation['exclusions'] for e in entry['evidence']}
    ids = {r['id'] for r in rows} | {e['id'] for group in ('additions', 'exclusions') for e in curation[group]}
    represented_blobs = {s.get('blob') for s in index['skills'] if component('https://github.com/' + s.get('repository', '') + '/blob/' + s.get('commit', '') + '/' + s.get('path', '')) in (known | excluded)}
    seen, seen_blobs, additions, duplicates, deferred = set(), set(), [], 0, 0
    for skill in sorted(index['skills'], key=lambda s: (s.get('repository', ''), s.get('path', ''))):
        repo, path = skill.get('repository', ''), skill.get('path', '')
        commit, blob, name = skill.get('commit', ''), skill.get('blob', ''), skill.get('name', '')
        if not REPOSITORY.fullmatch(repo) or not SHA.fullmatch(commit) or not SHA.fullmatch(blob) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name):
            raise ValueError('Malformed finder entry')
        source = 'https://github.com/' + repo + '/blob/' + commit + '/' + path
        key = component(source)
        if key is None or not path.endswith('SKILL.md') or any(p.casefold() in EXCLUDED for p in path.split('/')):
            raise ValueError('Unsafe finder path')
        if key in known or key in excluded or key in seen or blob in seen_blobs or blob in represented_blobs:
            duplicates += 1
            continue
        seen.add(key)
        seen_blobs.add(blob)
        if len(additions) >= limit:
            deferred += 1
            continue
        meta = verify(skill)
        official = repo.split('/')[0].casefold() in owners
        stars, forks = meta.get('stargazers_count'), meta.get('forks_count')
        if type(stars) is not int or type(forks) is not int or min(stars, forks) < 0:
            raise ValueError('Repository counts are unavailable')
        if not official and stars < 5000 and forks < 2000:
            deferred += 1
            continue
        rid = 'community:' + str(uuid.uuid5(NAMESPACE, key[0] + '/' + key[1]))
        if rid in ids:
            duplicates += 1
            continue
        stamp = now.isoformat()
        license = (meta.get('license') or {}).get('spdx_id')
        additions.append({'id': rid, 'fields': {'name': name, 'type': 'Skill',
            'website_url': source, 'repository_url': 'https://github.com/' + repo,
            'categories': ['Uncategorized'], 'tags': [],
            'license': license if license and license != 'NOASSERTION' else '',
            'license_scope': 'Repository license; skill-specific terms need review' if license and license != 'NOASSERTION' else '',
            'repository_archived': False, 'repository_status_checked_at': stamp,
            'github_stars': stars, 'github_stars_checked_at': stamp},
            'evidence': [{'url': source, 'checked_at': stamp, 'note': 'Verified public active repository, pinned path, Git blob and instruction name. Category and skill-specific licensing require maintainer review.'},
                         {'url': 'https://github.com/' + repo, 'checked_at': stamp, 'note': 'Inspected current repository identity, activity, counts and repository license metadata.'}]})
        ids.add(rid)
    return additions, {'proposed_additions': len(additions), 'duplicates_or_exclusions': duplicates,
                       'deferred': deferred, 'automatic_removals': 0, 'limit': limit}
