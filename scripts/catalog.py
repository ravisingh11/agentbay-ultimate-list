#!/usr/bin/env python3
"""Maintain the AgentBay public list using only Python standard-library tools and curl."""
import argparse
import concurrent.futures
import csv
import datetime
import hashlib
import io
import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
ORIGIN = 'https://agentbay.io'
PREFERRED_PROVIDERS = json.loads((ROOT/'data/preferred-providers.json').read_text())
PATHS = ['catalog.json', 'legacy-catalog.json', 'catalog-enrichment.json',
         'repository-status.json', 'catalog-edits-snapshot.json', 'skill-repository-metadata.json', 'api/catalog', 'api/visibility', 'api/github-metadata']
# Maintained metadata for curated projects supplied by the upstream compatibility feed.
CURATED_PROJECT_METADATA = {
    'langgraph': {'name': 'LangGraph', 'type': 'Orchestration runtime',
        'url': 'https://docs.langchain.com/oss/python/langgraph/overview',
        'categories': ['Frameworks'], 'tags': ['Stateful workflows', 'Human approval', 'Python / JS', 'LangGraph']},
    'pydanticai': {'name': 'PydanticAI', 'type': 'Python agent framework',
        'url': 'https://ai.pydantic.dev/', 'tags': ['Python', 'Typed outputs', 'Developer tools']},
}
FIELDS = ['id', 'name', 'description', 'type', 'website_url', 'repository_url',
          'categories', 'tags', 'use_cases', 'license', 'license_scope',
          'listing_scope', 'repository_archived', 'repository_status_checked_at', 'agentbay_url',
          'github_stars', 'github_stars_checked_at', 'recommended', 'preferred_provider']



def preferred_provider(repository_url):
    policy = PREFERRED_PROVIDERS
    key = repo_key(repository_url)
    owner = key.split('/')[0].casefold() if key else ''
    return next((p['name'] for p in policy['providers'] if owner in p['github_owners']), '')

SUMMARY_POLICY = 'structured-factual-v2'
# These are locally authored descriptions of metadata topics, not publisher prose.
TOPIC_DEFINITIONS = [
    ('agent development|ai agents|ai agent|ai framework|development framework agent|frameworks|multi agent and orchestration|large language models llms', 'agent development', 'Explore agent-building workflows'),
    ('documents and knowledge|knowledge management|memory knowledge management|office efficiency', 'document and knowledge workflows', 'Organize document-oriented tasks'),
    ('research and search|research|research assistants|research and task specific harnesses', 'information research', 'Assist with information-discovery tasks'),
    ('software development|software testing|code assistants|developer tools|dev programming|development and testing|ide integrated development environment|coding agent products (ides, clis, full suites)|coding harness configs and sdks|libraries and sdks', 'software engineering', 'Assist with implementation and code-maintenance tasks'),
    ('security and privacy|security skills by trail of bits team|it ops security', 'security and privacy', 'Assist with security-focused reviews'),
    ('deployment and cloud', 'deployment and cloud operations', 'Organize application-deployment tasks'),
    ('data analysis|data science', 'data analysis', 'Explore and organize analytical work'),
    ('monitoring and operations|observability and eval ops', 'monitoring and operations', 'Work with operational monitoring tasks'),
    ('planning and project management|project management|task management', 'project planning', 'Support project-coordination tasks'),
    ('sales and marketing|marketing|marketing skills by corey haines', 'marketing and outreach', 'Organize marketing-related workflows'),
    ('audio and speech', 'audio and speech workflows', 'Support audio-oriented tasks'),
    ('authentication', 'authentication workflows', 'Work with authentication-related integrations'),
    ('customer support', 'customer-support workflows', 'Organize customer-support tasks'),
    ('design|design media', 'design workflows', 'Organize design-related work'),
    ('finance', 'financial workflows', 'Explore finance-related tasks'),
    ('social media', 'social-media workflows', 'Organize social-media tasks'),
    ('search optimization', 'search optimization', 'Explore search-visibility tasks'),
    ('image generation', 'image workflows', 'Work with image-oriented tasks'),
    ('browser automation|browser', 'browser workflows', 'Explore browser-oriented automation'),
    ('memory and context|agent memory|context engineering|memory and state|progressive disclosure harnesses', 'agent memory and context', 'Organize context-related agent workflows'),
    ('video creation', 'video workflows', 'Work with video-oriented tasks'),
    ('product management skills by pawel huryn|product manager skills by dean peters', 'product management', 'Support product-planning tasks'),
    ('productivity|productivity and collaboration|business ops', 'productivity and collaboration', 'Organize collaborative work'),
    ('content creation', 'content workflows', 'Support content-oriented tasks'),
    ('game / simulation', 'games and simulation', 'Explore game or simulation workflows'),
    ('engineering standards', 'engineering practices', 'Organize engineering-quality tasks'),
    ('evaluation and benchmarking harnesses|testing and evaluation', 'evaluation workflows', 'Organize evaluation-related work'),
    ('personal agent runtimes|virtual assistant|conversational / general agents', 'assistant workflows', 'Explore assistant-oriented tasks'),
    ('plugins, mcps, cli tools', 'tool integrations', 'Explore integrations with agent tools'),
    ('storage|vector databases', 'data storage and retrieval', 'Work with storage-oriented integrations'),
    ('automation|task automation|workflow automation', 'workflow automation', 'Organize repeatable task workflows'),
    ('n8n automation', 'n8n workflows', 'Explore n8n-oriented automation'),
    ('education', 'learning workflows', 'Organize learning-related tasks'),
    ('sandboxes', 'execution environments', 'Explore isolated execution workflows'),
    ('life service', 'everyday tasks', 'Explore workflows for everyday tasks'),
    ('specialized domains|professional|other|🏭 industry use cases', 'specialized workflows', 'Explore topic-specific workflows'),
    ('agno', 'Agno-related agent work', 'Explore agent patterns associated with Agno'),
    ('autogen', 'AutoGen-related agent work', 'Explore agent patterns associated with AutoGen'),
    ('langgraph', 'LangGraph-related agent work', 'Explore agent patterns associated with LangGraph'),
]
TAG_TOPIC_ALIASES = {
    'agno': 'Agno-related agent work', 'autogen': 'AutoGen-related agent work', 'langgraph': 'LangGraph-related agent work',
    'code review': 'software engineering', 'coding': 'software engineering', 'developer tools': 'software engineering',
    'programming': 'software engineering', 'ai coding': 'software engineering', 'software testing': 'software engineering',
    'research': 'information research', 'search': 'information research', 'writing': 'content workflows',
    'automation': 'workflow automation', 'browser automation': 'browser workflows', 'playwright': 'browser workflows',
    'memory': 'agent memory and context', 'context engineering': 'agent memory and context',
    'rag': 'data storage and retrieval', 'retrieval': 'data storage and retrieval',
    'security': 'security and privacy', 'authentication': 'authentication workflows',
    'marketing': 'marketing and outreach', 'design': 'design workflows', 'data analysis': 'data analysis',
    'mcp': 'MCP tool integration', 'mcp server': 'MCP tool integration', 'model context protocol': 'MCP tool integration',
}
TOPIC_ACTIONS = {topic: action for _, topic, action in TOPIC_DEFINITIONS}
TOPIC_ACTIONS['MCP tool integration'] = 'Explore integrations with MCP tools'
CATEGORY_TOPICS = {alias: topic for aliases, topic, _ in TOPIC_DEFINITIONS for alias in aliases.split('|')}
SUMMARY_INPUT_FIELDS = ['id', 'name', 'type', 'categories', 'tags']


def metadata_key(value):
    return re.sub(r'[\s_-]+', ' ', value.strip().casefold())


def metadata_topics(row):
    topics = []
    for category in row['categories']:
        topic = CATEGORY_TOPICS.get(metadata_key(category))
        if topic and topic not in topics:
            topics.append(topic)
    for tag in row['tags']:
        topic = TAG_TOPIC_ALIASES.get(metadata_key(tag))
        if topic and topic not in topics:
            topics.append(topic)
    return topics[:3]


def join_topics(topics):
    if len(topics) == 1:
        return topics[0]
    if len(topics) == 2:
        return ' and '.join(topics)
    return ', '.join(topics[:-1])+', and '+topics[-1]


def original_summary(row):
    # Do not use the source description or use-case prose, even as a fallback.
    label = {'Skill': 'an agent skill', 'Skill Repository': 'an agent-skill repository',
             'Skill Collection': 'an agent-skill collection', 'Agent Or Tool': 'an agent or tool',
             'Agent Example': 'an agent example', 'Framework': 'a framework', 'Tool': 'a tool',
             'Project': 'a project', 'Python agent framework': 'a Python agent framework'}.get(row['type'], 'a project')
    name = ' '.join(row['name'].split())
    topics = metadata_topics(row)
    description = f'{name} is listed as {label}.'
    if topics:
        description += ' Its catalogue topics include '+join_topics(topics)+'.'
    else:
        description += ' A specific capability summary has not been established from the available catalogue metadata.'
    use_cases = [TOPIC_ACTIONS[topic] for topic in topics]
    return description, use_cases, topics


def summarize_catalog(rows):
    rewritten, records = [], {}
    for row in rows:
        description, use_cases, topics = original_summary(row)
        item = {**row, 'description': description, 'use_cases': use_cases}
        public_text = json.dumps({k: item[k] for k in ['name','type','categories','tags','description','use_cases']}, ensure_ascii=False)
        if re.search(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', public_text, re.I) or re.search(r'\+\d[\d ()-]{8,}\d\b', public_text):
            raise ValueError('Contact details in retained metadata require source review: '+row['id'])
        rewritten.append(item)
        fingerprint = lambda value: hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        records[row['id']] = {'input_sha256': fingerprint({k: row[k] for k in SUMMARY_INPUT_FIELDS}),
                              'description_sha256': fingerprint(description), 'use_cases_sha256': fingerprint(use_cases),
                              'topics': topics, 'capability_topic_unresolved': not bool(topics)}
    provenance = {'schema_version': 1, 'policy': SUMMARY_POLICY,
                  'method': 'Locally authored templates and controlled topic vocabulary applied to structured catalogue metadata',
                  'input_fields': SUMMARY_INPUT_FIELDS, 'excluded_inputs': ['source description', 'source use-case prose'],
                  'source_links': 'Public website_url and repository_url fields in catalog.json',
                  'limitations': 'Metadata-based summaries; no new capability, compatibility, security, or maintenance audit. Not a legal clearance certificate.',
                  'entry_count': len(rewritten), 'records': records}
    return rewritten, provenance


def fetch_bytes(path):
    # curl handles the site's TLS/edge configuration consistently across platforms.
    result = subprocess.run(['curl', '--fail', '--compressed', '--silent', '--show-error',
                             '--location', '--retry', '3', '--retry-all-errors', '--max-time', '60', ORIGIN+'/'+path],
                            capture_output=True, check=True)
    return result.stdout


def fetch(path):
    try:
        raw = fetch_bytes(path)
    except subprocess.CalledProcessError:
        if path == 'api/catalog':
            return path, None
        raise
    return path, (json.loads(raw), hashlib.sha256(raw).hexdigest())


def repo_key(url):
    match = re.match(r'^https://github\.com/([^/]+/[^/#?]+)', url or '', re.I)
    return re.sub(r'\.git$', '', match[1]) if match else None


def date(value):
    try:
        return datetime.datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
    except (ValueError, AttributeError):
        return float('-inf')


def archive_status(item, statuses, metadata):
    key = repo_key(item.get('repository'))
    stored = statuses.get((key or '').lower())
    current = metadata.get(key)
    if not (current and current.get('status') == 'ok' and
            (not current.get('repository') or (repo_key(current['repository']) or '').lower() == (key or '').lower())):
        current = None
    if current and isinstance(current.get('archived'), bool) and (not stored or date(current.get('checkedAt')) >= date(stored.get('checkedAt'))):
        return current['archived'], current.get('checkedAt')
    if stored:
        return stored.get('archived') is True, stored.get('checkedAt')
    return bool(current and current.get('archived') is True), current.get('checkedAt') if current else None


def enrich(item, extra):
    result = dict(item)
    for key, value in extra.get(item['id'], {}).items():
        if not result.get(key):
            result[key] = value
    return result


def build(data):
    base = data['catalog.json']
    if not isinstance(base, list) or not base or len({a['id'] for a in base}) != len(base):
        raise ValueError('Upstream catalog must contain unique nonempty records')
    statuses = data['repository-status.json']['repositories']
    metadata = data['api/github-metadata']['repositories']
    visibility = {a['id']: a['hidden'] for a in data['api/visibility']['items']}
    extra = data['catalog-enrichment.json']
    items = {a['id']: a for a in base}
    # Retain supported curated projects when they are absent from the primary feed.
    for item in data['legacy-catalog.json']:
        if item.get('slug') in CURATED_PROJECT_METADATA and not any(a.get('slug') == item['slug'] for a in base):
            items[item['id']] = {**enrich(item, extra), **CURATED_PROJECT_METADATA[item['slug']], 'listingScope': 'direct_list'}
    for edit in data['api/catalog']['items']:
        items[edit['id']] = enrich({**items.get(edit['id'], {}), **edit}, extra)
    metadata_by_key = {key.casefold(): value for key, value in metadata.items()}
    for key, value in data.get('skill-repository-metadata.json', {}).get('repositories', {}).items():
        if value.get('status') == 'ok' and date(value.get('checkedAt')) > date(metadata_by_key.get(key.casefold(), {}).get('checkedAt')):
            metadata_by_key[key.casefold()] = value
    selected = []
    excluded = {'hidden': 0, 'archived': 0, 'saved_only': 0, 'no_repository': 0}
    for item in items.values():
        if visibility.get(item['id'], False):
            excluded['hidden'] += 1
            continue
        if item.get('legacySavedOnly'):
            excluded['saved_only'] += 1
            continue
        archived, checked_at = archive_status(item, statuses, metadata)
        if archived:
            excluded['archived'] += 1
            continue
        # Guard the curated export without silently changing site membership.
        if not repo_key(item.get('repository')):
            excluded['no_repository'] += 1
            continue
        github = metadata_by_key.get((repo_key(item.get('repository')) or '').casefold(), {})
        stars = github.get('stars') if github.get('status') == 'ok' else None
        if not isinstance(stars, int) or isinstance(stars, bool) or stars < 0:
            stars = None
        selected.append({
            'id': item['id'], 'name': item['name'], 'description': '',
            'type': item.get('type', ''), 'website_url': item.get('url') or '',
            'repository_url': item['repository'], 'categories': item.get('categories') or [],
            'tags': item.get('tags') or [], 'use_cases': [],
            'license': item.get('license') or '', 'license_scope': item.get('licenseScope') or '',
            'listing_scope': item.get('listingScope') or 'direct_list',
            'repository_archived': False, 'repository_status_checked_at': checked_at,
            'agentbay_url': ORIGIN+'/?project='+item['id']+'#catalog',
            'github_stars': stars, 'github_stars_checked_at': github.get('checkedAt') if stars is not None else None,
            'recommended': False, 'preferred_provider': preferred_provider(item['repository']),
        })
    selected.sort(key=lambda a: (a['name'].casefold(), a['id']))
    return summarize_catalog(selected)[0], excluded


def md(value):
    import html
    value = html.escape(' '.join(str(value or '').split()), quote=False)
    return re.sub(r'([\\`*_{}\[\]|])', r'\\\1', value)


def link_url(value):
    from urllib.parse import quote, urlsplit
    if urlsplit(value).scheme.lower() not in ('http', 'https'):
        raise ValueError('Unsupported public link: '+value)
    return quote(value, safe=":/?#[]@!$&'()*+,;=%~_-.{}")


def is_skill(row):
    return row['type'].strip().casefold().startswith('skill')


def category_groups(rows):
    from collections import Counter, defaultdict
    # Preserve source categories; case-only variants share one browse heading.
    names = defaultdict(Counter)
    for row in rows:
        category = next((v.strip() for v in row['categories'] if v.strip()), 'Uncategorized')
        names[category.casefold()][category] += 1
    labels = {k: sorted(v, key=lambda label: (-v[label], label))[0] for k, v in names.items()}
    groups = defaultdict(list)
    for row in rows:
        category = next((v.strip() for v in row['categories'] if v.strip()), 'Uncategorized')
        groups[labels[category.casefold()]].append(row)
    return [(name, sorted(items, key=lambda a: (a['name'].casefold(), a['id'])))
            for name, items in sorted(groups.items(), key=lambda pair: (pair[0]=='Uncategorized', pair[0].casefold()))]


def category_slug(label):
    import unicodedata
    ascii_label = unicodedata.normalize('NFKD', label).encode('ascii', 'ignore').decode().lower()
    # Hash suffixes keep distinct categories from colliding after punctuation removal.
    return (re.sub(r'[^a-z0-9]+', '-', ascii_label).strip('-') or 'category')+'-'+hashlib.sha256(label.casefold().encode()).hexdigest()[:6]


def listing_line(row):
    links = []
    if row['website_url']:
        links.append('[Website](<'+link_url(row['website_url'])+'>)')
    else:
        links.append('Website not listed')
    links.append('[GitHub](<'+link_url(row['repository_url'])+'>)')
    description = ' '.join(row['description'].split())
    if len(description) > 180:
        description = description[:177].rsplit(' ', 1)[0]+'…'
    labels = ['**License: '+md(row['license'] or 'Unknown')+'**']
    stars = row.get('github_stars')
    labels.append('**★ '+f'{stars:,}'+'**'+(' (as of '+row['github_stars_checked_at'][:10]+')' if row.get('github_stars_checked_at') else '') if stars is not None else 'Stars: not recorded')
    if row.get('preferred_provider'):
        labels.append('**'+md(row['preferred_provider'])+' · Official source**')
    return '- **'+md(row['name'])+'** — '+' · '.join(links)+' · '+' · '.join(labels)+((' — '+md(description)) if description else '')


def csv_cell(value):
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return str(value).lower()
    return '' if value is None else str(value)


def encode_exports(rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator='\n')
    writer.writeheader()
    for row in rows:
        writer.writerow({key: csv_cell(row[key]) for key in FIELDS})
    return {'json': (json.dumps(rows, ensure_ascii=False, indent=2)+'\n').encode(),
            'csv': stream.getvalue().encode()}


def split_exports(rows):
    groups = {'skills': [row for row in rows if is_skill(row)],
              'projects': [row for row in rows if not is_skill(row)]}
    all_ids = {row['id'] for row in rows}
    skill_ids = {row['id'] for row in groups['skills']}
    project_ids = {row['id'] for row in groups['projects']}
    if (len(all_ids) != len(rows) or skill_ids & project_ids or
            skill_ids | project_ids != all_ids or
            len(groups['skills']) + len(groups['projects']) != len(rows)):
        raise ValueError('Split exports must partition the combined catalogue exactly')
    outputs, metadata = {}, {}
    for group, items in groups.items():
        encoded = encode_exports(items)
        paths = {extension: f'{group}/catalog.{extension}' for extension in ('json','csv')}
        outputs.update({paths[extension]: raw for extension, raw in encoded.items()})
        metadata[group] = {'entry_count': len(items), **paths}
    return outputs, metadata


GENERATED = '<!-- Generated by scripts/catalog.py; edit the maintained sources and regenerate. -->'
PAGE_SIZE = 200
CURATION = 'data/curation.json'
POLICY = 'data/preferred-providers.json'
EDITABLE = {'name', 'type', 'website_url', 'repository_url', 'categories', 'tags',
            'license', 'license_scope', 'repository_archived', 'repository_status_checked_at',
            'github_stars', 'github_stars_checked_at'}


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_rows(rows):
    from urllib.parse import urlsplit
    if not isinstance(rows, list):
        raise ValueError('Catalog must be a JSON array')
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != set(FIELDS):
            raise ValueError('Catalog record fields differ from the documented schema')
        rid = row['id']
        if not isinstance(rid, str) or not rid or len(rid) > 100 or rid in seen:
            raise ValueError('Empty, invalid or duplicate catalog ID: '+str(rid))
        seen.add(rid)
        for field in ('name', 'type', 'description', 'website_url', 'repository_url', 'license',
                      'license_scope', 'listing_scope', 'agentbay_url', 'preferred_provider'):
            if not isinstance(row[field], str):
                raise ValueError('Expected text in '+rid+' '+field)
        if not row['name'].strip() or not row['type'].strip() or not repo_key(row['repository_url']):
            raise ValueError('Name, type and public GitHub repository are required: '+rid)
        for field in ('categories', 'tags', 'use_cases'):
            if not isinstance(row[field], list) or any(not isinstance(v, str) or not v.strip() for v in row[field]):
                raise ValueError('Expected nonempty text array members: '+rid+' '+field)
        for field in ('repository_archived', 'recommended'):
            if not isinstance(row[field], bool):
                raise ValueError('Expected boolean: '+rid+' '+field)
        for field in ('repository_status_checked_at', 'github_stars_checked_at'):
            value = row[field]
            if value is not None and (not isinstance(value, str) or date(value) == float('-inf')):
                raise ValueError('Expected ISO timestamp or null: '+rid+' '+field)
        stars = row['github_stars']
        if stars is not None and (not isinstance(stars, int) or isinstance(stars, bool) or stars < 0):
            raise ValueError('Expected nonnegative star count or null: '+rid)
        for field in ('website_url', 'repository_url', 'agentbay_url'):
            if row[field]:
                url = urlsplit(row[field])
                if url.scheme not in ('http', 'https') or not url.netloc or url.username or url.password:
                    raise ValueError('Expected public HTTP(S) URL without credentials: '+rid+' '+field)
        serialized = json.dumps(row, ensure_ascii=False)
        if re.search(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|(?:AKIA|ASIA)[A-Z0-9]{16})\b|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY', serialized):
            raise ValueError('Credential-like content requires review: '+rid)


def validate_policy(policy):
    providers, owners = set(), set()
    if not isinstance(policy.get('providers'), list):
        raise ValueError('Missing preferred-provider registry')
    for provider in policy['providers']:
        if provider['name'] in providers or not provider['github_owners']:
            raise ValueError('Duplicate provider or empty official-owner list')
        providers.add(provider['name']); link_url(provider['homepage_url'])
        for owner in provider['github_owners']:
            if not re.fullmatch(r'[a-z0-9-]+', owner) or owner in owners:
                raise ValueError('Duplicate or noncanonical GitHub owner: '+owner)
            owners.add(owner)


def checked_evidence(entry):
    evidence = entry.get('evidence')
    if not isinstance(evidence, list) or not evidence:
        raise ValueError('A curation change requires public evidence')
    for item in evidence:
        if set(item) != {'url', 'checked_at', 'note'} or not item['note'].strip():
            raise ValueError('Evidence needs url, checked_at and note')
        link_url(item['url'])
        # Date-only observations are allowed; timestamps must include their timezone.
        checked = datetime.datetime.fromisoformat(item['checked_at'].replace('Z', '+00:00'))
        if 'T' in item['checked_at'] and checked.tzinfo is None:
            raise ValueError('Evidence timestamps require a timezone')
        if checked.date() > datetime.datetime.now(datetime.timezone.utc).date():
            raise ValueError('Evidence check date is in the future')


def apply_curation(rows, source):
    if source.get('schema_version') != 1 or set(source) != {'schema_version', 'additions', 'corrections', 'exclusions'}:
        raise ValueError('Unsupported curation schema')
    result = {row['id']: dict(row) for row in rows}
    for kind in ('additions', 'corrections', 'exclusions'):
        if not isinstance(source[kind], list):
            raise ValueError('Curation changes must be arrays')
        ids = set()
        for entry in source[kind]:
            checked_evidence(entry)
            rid = entry.get('id')
            if not isinstance(rid, str) or not rid or rid in ids:
                raise ValueError('Missing or repeated curation ID: '+str(rid))
            ids.add(rid)
            if kind == 'exclusions':
                if set(entry) != {'id', 'reason', 'evidence'} or len(entry['reason'].strip()) < 10:
                    raise ValueError('Exclusions require a specific reviewable reason')
                result.pop(rid, None)
                continue
            values = entry.get('fields')
            if set(entry) != {'id', 'fields', 'evidence'} or not isinstance(values, dict) or not values or set(values)-EDITABLE:
                raise ValueError('Unsupported curation fields for '+rid)
            if kind == 'corrections' and rid not in result:
                raise ValueError('Correction refers to an unknown ID: '+rid)
            if kind == 'additions':
                if not re.fullmatch(r'community:[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}', rid):
                    raise ValueError('Community additions need a community: UUID identifier')
                if not {'name','type','repository_url','website_url','categories','tags'} <= set(values):
                    raise ValueError('Community addition lacks required fields: '+rid)
                if rid in result and repo_key(result[rid]['repository_url']).casefold() != repo_key(values['repository_url']).casefold():
                    raise ValueError('Community ID conflicts with another repository: '+rid)
                base = {field: '' for field in FIELDS}
                base.update({'id': rid, 'categories': [], 'tags': [], 'use_cases': [],
                             'repository_archived': False, 'repository_status_checked_at': None,
                             'github_stars': None, 'github_stars_checked_at': None,
                             'recommended': False, 'listing_scope': 'community'})
                result[rid] = {**base, **result.get(rid, {}), **values}
            else:
                result[rid] = {**result[rid], **values}
    return list(result.values())


def component_key(row):
    # Only collapse the same named component at the same source. Distinct paths,
    # types and repositories remain separate even when their names are identical.
    from urllib.parse import urlsplit, unquote
    url = urlsplit(row['website_url'])
    path = unquote(url.path).rstrip('/')
    if url.hostname and url.hostname.casefold() == 'github.com':
        parts = path.strip('/').split('/')
        if len(parts) >= 2:
            parts[:2] = [p.casefold() for p in parts[:2]]
            path = '/'.join(parts)
    return (repo_key(row['repository_url']).casefold(), (url.hostname or '').casefold(),
            path, url.query, url.fragment, row['name'].casefold().strip(), row['type'].casefold().strip())


def normalize(rows, aliases=None, preferred_ids=None):
    from collections import defaultdict
    validate_rows(rows)
    groups = defaultdict(list)
    aliases = dict(aliases or {})
    preferred_ids = set(preferred_ids or [])
    for row in rows:
        groups[component_key(row)].append(dict(row))
    result = []
    for members in groups.values():
        members.sort(key=lambda row: (row['id'] not in preferred_ids, row['listing_scope'] != 'direct_list', row['id']))
        retained = members[0]
        for other in members[1:]:
            aliases[other['id']] = retained['id']
            for field in ('categories','tags'):
                retained[field] = list(dict.fromkeys(retained[field]+other[field]))
            for field in ('license','license_scope','agentbay_url'):
                if not retained[field]:
                    retained[field] = other[field]
        retained['preferred_provider'] = preferred_provider(retained['repository_url'])
        retained['recommended'] = False
        result.append(retained)
    for key in list(aliases):
        target, visited = aliases[key], {key}
        while target in aliases:
            if target in visited:
                raise ValueError('Cyclic catalog alias: '+key)
            visited.add(target); target = aliases[target]
        aliases[key] = target
    result = summarize_catalog(result)[0]
    result.sort(key=lambda row: (row['name'].casefold(), row['id']))
    validate_rows(result)
    return result, dict(sorted(aliases.items()))


def augment(existing, incoming, aliases):
    by_id = {row['id']: dict(row) for row in existing}
    incoming_ids, added, updated = set(), 0, 0
    grouped = {}
    for row in incoming:
        rid = aliases.get(row['id'], row['id'])
        grouped.setdefault(rid, []).append(row)
    for rid, members in grouped.items():
        incoming_ids.add(rid)
        source = next((r for r in members if r['id'] == rid), members[0])
        row = {**source, 'id': rid}
        for field in ('categories', 'tags'):
            row[field] = list(dict.fromkeys(v for r in [row]+members for v in r[field]))
        added += rid not in by_id
        updated += rid in by_id and by_id[rid] != row
        by_id[rid] = row
    return list(by_id.values()), {'incoming_entries': len(incoming), 'added_ids': added,
            'updated_ids': updated, 'retained_absent_ids': len(set(by_id)-incoming_ids),
            'removed_automatically': 0}


def render_browse(rows, manifest):
    outputs = {}
    counts = {}
    for group, title in [('skills', 'Skills'), ('projects', 'Projects and tools')]:
        members = [row for row in rows if is_skill(row) == (group == 'skills')]
        counts[group] = len(members)
        index = [GENERATED, '', '# AgentBay '+title.lower(), '',
                 f'**{len(members):,} listings.** [Home](../README.md) · [JSON](catalog.json) · [CSV](catalog.csv)', '',
                 'Each listing appears once under its primary category. Categories, tags and complete records remain in the downloads. Stars are cached repository counts with observation dates. Official source denotes verified publisher ownership. It is not a quality or security review.', '',
                 '| Category | Listings | Browse |', '| --- | ---: | --- |']
        if group == 'skills':
            index[6:6] = ['[Get AgentBay Skill Installer](../docs/using-skills.md) · [Read its SKILL.md](agentbay-skill-installer/SKILL.md)', '']
        for label, items in category_groups(members):
            pages = [items[i:i+PAGE_SIZE] for i in range(0, len(items), PAGE_SIZE)]
            paths = [f'{group}/{category_slug(label)}'+(f'-{i+1}' if len(pages)>1 else '')+'.md' for i in range(len(pages))]
            index.append(f'| {md(label)} | {len(items):,} | '+' · '.join(f'[Page {i+1}]({path.split("/",1)[1]})' for i,path in enumerate(paths))+' |')
            for i, (path, page) in enumerate(zip(paths, pages)):
                nav = f'[{title} index](README.md) · [Home](../README.md)'
                if i: nav += ' · [← Previous]('+paths[i-1].split('/',1)[1]+')'
                if i+1 < len(pages): nav += ' · [Next →]('+paths[i+1].split('/',1)[1]+')'
                lines = [GENERATED, '', '# '+md(label), '', nav, '', f'{len(items):,} listings · Page {i+1} of {len(pages)}', '']
                lines += [listing_line(row) for row in page]
                outputs[path] = ('\n'.join(lines+['',nav,''])).encode()
        outputs[group+'/README.md'] = ('\n'.join(index+['','[MIT License](../LICENSE) · [License scope](../LICENSING.md)',''])).encode()
    provider_lines = [GENERATED, '', '# Preferred providers', '', '[Home](../README.md) · [Maintained owner registry](../data/preferred-providers.json)', '',
        PREFERRED_PROVIDERS['meaning'], '',
        'Counts below are listings in this repository, including repository-level entries. AgentBay’s website finder counts verified individual SKILL.md files in its eligible source pool; those counts have a different scope.', '',
        '| Provider | Catalogue listings |', '| --- | ---: |']
    for p in PREFERRED_PROVIDERS['providers']:
        provider_lines.append('| ['+md(p['name'])+']('+link_url(p['homepage_url'])+') | '+f'{sum(r["preferred_provider"]==p["name"] for r in rows):,}'+' |')
    outputs['docs/providers.md'] = ('\n'.join(provider_lines+[''])).encode()
    root = [GENERATED, '', '# AgentBay Ultimate List', '',
        '[![AgentBay: Your task. The right skill.](assets/agentbay-repository.svg)](https://agentbay.io/)', '',
        '**Start with a task. Find the skill. Get to work.**', '',
        '[![MIT license](https://img.shields.io/badge/License-MIT-527715?style=flat-square)](LICENSE) [![Skill finder](https://img.shields.io/badge/AgentBay.io-Find_a_skill-202820?style=flat-square)](https://agentbay.io/) [![Guardrails](https://img.shields.io/badge/Guardrails-See_the_checks-6f42c1?style=flat-square)](docs/guardrails.md)', '',
        '[Find a skill at AgentBay.io](https://agentbay.io/) · [Install AgentBay](#quick-start) · [Read the skill](skills/agentbay-skill-installer/SKILL.md) · [Browse the list](skills/README.md)', '',
        '## Why I built AgentBay', '',
        'I created AgentBay around one question: **What is the right skill for the task in front of me?**', '',
        'You might be fixing a Cloudflare Worker, reviewing a pull request or turning a document into a spreadsheet. Somewhere, a team has already put useful knowledge into a skill. Finding it, understanding where it came from and getting your agent to use it should be straightforward.', '',
        'That is what I want [AgentBay.io](https://agentbay.io/) and this repository to make easier: a practical reference that connects the work you need to do with instructions your agent can actually use. Browse on the site, explore the sources here, or bring AgentBay into your agent and ask in plain language.', '',
        '## What could you use it for?', '',
        '| Your task | Ask your agent | A useful next step |',
        '| --- | --- | --- |',
        '| Fix a Cloudflare Worker | Find a skill for debugging my Cloudflare Worker with AgentBay. | [Follow the local fix-and-test walkthrough](docs/cloudflare-first-use.md). |',
        '| Review a landing page | Find a skill for reviewing my landing page’s accessibility with AgentBay. | [Try the HTML review example](docs/using-skills.md#first-worked-example). |',
        '| Review a pull request | Find a skill for reviewing this pull request with AgentBay. | Match a review workflow to your project and inspect the diff. |',
        '| Turn a PDF into a spreadsheet | Find a skill for extracting PDF tables into a spreadsheet with AgentBay. | Check extraction requirements and the spreadsheet output you need. |',
        '| Diagnose a failing test | Find a skill for diagnosing this failing test with AgentBay. | Choose a workflow that fits your test runner, reproduce the failure and check the fix. |',
        '| Create a slide deck | Find a skill for turning this brief into a slide deck with AgentBay. | Match a presentation workflow and check its export format. |', '',
        'These prompts start discovery. After choosing a skill, ask AgentBay to install it, check prerequisites and use it. The linked walkthroughs show concrete examples and checks.', '',
        '## Where I start: credible sources, visible momentum', '',
        'My starting point is official sources from companies such as **Anthropic, OpenAI, Google, Microsoft, AWS and Cloudflare**, alongside GitHub projects with visible adoption and maintenance. Established teams often bring documented processes, review practices and continuity that are useful reasons to look at their work first.', '',
        'Here is what matters when choosing a skill:', '',
        '- **A source you can trace.** Our [preferred-provider registry](docs/providers.md) identifies verified publisher ownership and links back to official sources.',
        '- **A repository worth investigating.** Stars and forks can point to community momentum; recent commits, releases and issue responses help you judge whether that attention comes with ongoing maintenance. Follow the repository link and look at the evidence.',
        '- **A fit for the job.** AgentBay reads the publisher’s actual skill instructions and checks prerequisites before using a selected skill. The name alone is not enough.', '',
        'These are useful signals, not a security certification. Official ownership does not establish that every skill was audited; popularity does not establish task fit. Independent maintainers can produce excellent work too.', '',
        f'**Explore {len(rows):,} listings: {counts["skills"]:,} skills and {counts["projects"]:,} projects and tools across {len({repo_key(r["repository_url"]).casefold() for r in rows}):,} GitHub repositories.**', '',
        '## Quick start', '',
        'AgentBay matches your task to skills using this repository’s curated catalogue, then reads the selected publisher’s actual instructions. Install AgentBay once; request other skills as you need them. You do not need to check out the whole repository.', '',
        '**1. Install for your app.** For Codex desktop, CLI or IDE extension, run this in your project’s terminal:', '',
        '```sh', 'npx --yes skills@1.7.4 add https://github.com/ravisingh11/agentbay-ultimate-list/tree/main/skills/agentbay-skill-installer --skill agentbay-skill-installer --agent codex --yes', '```', '',
        '> [!NOTE]', '> Requires Node.js 22.20+, Git and internet access. This repository is public; installation and catalogue downloads do not require a GitHub account. Your agent still needs network access to read sources.', '',
        '**Claude Code:** change `--agent codex` to `--agent claude-code`. **Claude desktop:** [download the skill ZIP](https://github.com/ravisingh11/agentbay-ultimate-list/raw/refs/heads/main/downloads/agentbay-skill-installer.zip) and upload it in Customize → Skills. [Steps for each app](docs/install.md) · [Optional installer script](install.sh).', '',
        '**2. Open the skill.** [Read the maintained SKILL.md](skills/agentbay-skill-installer/SKILL.md). In Codex, open the same project, start a fresh chat and check its Skills view or `/skills` selector. The project copy is `.agents/skills/agentbay-skill-installer/SKILL.md`.', '',
        '**3. Describe your task.**', '',
        '> Find a skill for [my task] with AgentBay.', '',
        'After choosing a result, ask: “Install this skill in my project, check its prerequisites, then use it for the task.” If AgentBay is not selected automatically, choose it in your app’s skill selector. Expect a source link, a readiness check and a verified task result. Installation does not grant cloud or account permissions.', '',
        '[Try the Cloudflare Worker walkthrough](docs/cloudflare-first-use.md) · [Review an HTML example](docs/using-skills.md#first-worked-example) · [Updates, removal and version pinning](docs/using-skills.md) · [Verification and app test status](docs/installer-validation.md).', '',
        '## Explore', '',
        '- [Skills by category](skills/README.md)',
        '- [Projects and tools by category](projects/README.md)',
        '- [Preferred providers](docs/providers.md) · [How to install and use a skill](docs/using-skills.md)',
        '- [Search the live AgentBay finder](https://agentbay.io/) · [Browse AgentBay’s full catalog](https://agentbay.io/catalog)', '',
        '## Download', '', '| List | JSON | CSV |', '| --- | --- | --- |',
        '| All listings | [catalog.json](catalog.json) | [catalog.csv](catalog.csv) |',
        '| Skills | [JSON](skills/catalog.json) | [CSV](skills/catalog.csv) |',
        '| Projects and tools | [JSON](projects/catalog.json) | [CSV](projects/catalog.csv) |', '',
        'All six exports share one schema. Skills and projects are disjoint subsets of the combined list. A repository can contain several distinct skills. [Data fields and examples](docs/data.md).', '',
        '## A living reference, maintained by AgentBay', '',
        'This list is **sourced and maintained by [AgentBay](https://agentbay.io/)**. Imports bring in new listings and supported metadata; reviewed contributions add context and corrections that survive later imports. An entry disappearing from a website import does not automatically erase it here. [How curation works](docs/maintenance.md).', '',
        'The website and repository serve different ways of exploring the same ecosystem. This repository publishes the broader catalogue, reusable downloads and installer skill. **Recommendations and curation on AgentBay.io are not synchronized back into this repository.** Website rankings, favorites, notes, accounts and personal collections stay on the site. Maintainers may separately import new listings and supported factual metadata; repository corrections and exclusions go through review. The list augments the site rather than mirroring its current recommendations.', '',
        'Listing summaries are generated from catalogue metadata; the linked publisher instructions remain the source to read before use. Stars and status checks are dated observations. [Data details](docs/data.md) · [Source and update evidence](sync-manifest.json).', '',
        'Maintainers can prepare [reviewed refresh proposals](docs/maintenance.md#reviewed-refresh-proposals-and-new-providers) and contributors can [suggest an official provider](https://github.com/ravisingh11/agentbay-ultimate-list/issues/new?template=add-provider.yml). Provider attribution requires verified ownership and actual skill sources; discovery alone does not approve a listing.', '',
        '## Contribute', '',
        'Found a useful skill, a broken link or a better way to describe a task? Help make the next person’s search easier. [CONTRIBUTING.md](CONTRIBUTING.md) explains how to suggest a well-sourced change. [Contributors](CONTRIBUTORS.md) · [Report a security or privacy concern](SECURITY.md).', '',
        '## 🛡️ How we look after the list', '',
        '> [!NOTE]',
        '> **We use [AI Software Toolkit](https://github.com/ravisingh11/ai-software-toolkit) to manage the checks and review workflow around catalogue data commits.** Its Proof checks validate proposed changes, while catalogue checks keep the generated README, browsing pages and JSON/CSV downloads consistent. Changes go through pull requests and maintainer review; the toolkit does not automatically approve, merge or publish them.', '',
        'Public evidence, stable IDs, reproducible downloads and owner review keep contributions traceable. [See the guardrails](docs/guardrails.md) for the configured checks, shared engineering skills, recorded results and current enforcement limits.', '',
        '## License', '',
        'The catalogue, original documentation and maintenance tooling are available under the [MIT License](LICENSE). Listed software, skill instructions and publisher materials retain their own licenses. [License scope and third-party notices](LICENSING.md).', '']
    outputs['README.md'] = ('\n'.join(root)).encode()
    if any(len(raw) >= 450*1024 for raw in outputs.values()):
        raise ValueError('Generated browse page exceeds the rendering limit')
    return outputs


def generated_path(name):
    p = pathlib.PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts:
        return False
    return name in {'README.md','catalog.json','catalog.csv','skills/catalog.json','skills/catalog.csv',
                    'projects/catalog.json','projects/catalog.csv','provenance/descriptions.json',
                    'provenance/aliases.json','docs/providers.md'} or (
                    len(p.parts)==2 and p.parts[0] in ('skills','projects') and p.suffix=='.md')


def build_outputs(rows, aliases, manifest, root=ROOT):
    rows, normalized_aliases = normalize(rows, aliases)
    if normalized_aliases != aliases:
        raise ValueError('Normalize aliases before generating outputs')
    encoded = encode_exports(rows)
    outputs = {'catalog.json': encoded['json'], 'catalog.csv': encoded['csv']}
    derived, groups = split_exports(rows)
    outputs.update(derived)
    outputs.update(render_browse(rows, manifest))
    outputs['provenance/descriptions.json'] = json_bytes(summarize_catalog(rows)[1])
    outputs['provenance/aliases.json'] = json_bytes({'schema_version': 1,
        'rule': 'Same repository, source URL, name and type; category/tag metadata retained on the surviving ID.',
        'aliases': aliases})
    result = {key: manifest[key] for key in ('upstream', 'last_refresh') if key in manifest}
    result.update({'schema_version': 7, 'source': ORIGIN, 'maintainer': 'AgentBay',
        'update_policy': 'Add and update upstream entries, preserve reviewed local changes and absent records; removals require curation.',
        'entry_count': len(rows), 'unique_repository_count': len({repo_key(r['repository_url']).casefold() for r in rows}),
        'catalogue_license': {'spdx_id':'MIT','path':'LICENSE','scope_notice':'LICENSING.md'},
        'inputs': {name: {'sha256': sha((root/name).read_bytes())} for name in (CURATION,POLICY)},
        'description_policy': {'version':SUMMARY_POLICY,'provenance':'provenance/descriptions.json','source_prose_reused':False},
        'preferred_providers': {'source':POLICY,'provider_count':len(PREFERRED_PROVIDERS['providers'])},
        'derived_exports': groups, 'duplicate_id_aliases':len(aliases),
        'generated_markdown_files':sorted(n for n in outputs if n.endswith('.md')),
        'files': {n:{'sha256':sha(raw),'bytes':len(raw)} for n,raw in sorted(outputs.items())}})
    outputs['sync-manifest.json'] = json_bytes(result)
    return outputs, result


def assert_safe_target(root, name):
    target = root/name
    for path in [target]+list(target.parents):
        if path == root.parent: break
        if path.is_symlink():
            raise ValueError('Refusing to write through symlink: '+name)
    return target


def write_outputs(outputs, previous, root=ROOT):
    generated = {name for name in outputs if name.endswith('.md')}
    obsolete = set(previous.get('generated_markdown_files', []))-generated
    for name in set(outputs)|obsolete:
        if name != 'sync-manifest.json' and not generated_path(name):
            raise ValueError('Unexpected generated path: '+name)
        target = assert_safe_target(root, name)
        if name in obsolete and target.exists() and not target.read_text().startswith(('<!-- Generated by sync.py', GENERATED)):
            raise ValueError('Preserving unowned obsolete page: '+name)
        if target.exists() and name not in previous.get('files', {}) and name not in ('sync-manifest.json','README.md'):
            raise ValueError('Preserving unowned output: '+name)
        if target.exists() and name in previous.get('files', {}) and sha(target.read_bytes()) != previous['files'][name]['sha256']:
            raise ValueError('Generated file was edited directly; preserve edits in maintained inputs: '+name)
        if name in outputs:
            temporary = target.with_name('.'+target.name+'.tmp')
            if temporary.exists() or temporary.is_symlink():
                raise ValueError('Temporary output already exists: '+str(temporary))
    # All inputs, paths and payloads have been validated before the first write.
    # Each file replacement is atomic; a partial filesystem failure is detected by --check.
    for name, raw in outputs.items():
        target = root/name
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name('.'+target.name+'.tmp')
        if temporary.exists() or temporary.is_symlink():
            raise ValueError('Temporary output already exists: '+str(temporary))
        with temporary.open('xb') as stream: stream.write(raw)
        temporary.replace(target)
    for name in obsolete:
        (root/name).unlink(missing_ok=True)


def check(root=ROOT):
    manifest = read_json(root/'sync-manifest.json')
    rows = read_json(root/'catalog.json')
    validate_rows(rows); validate_policy(PREFERRED_PROVIDERS)
    for name, evidence in manifest['files'].items():
        if not generated_path(name): raise ValueError('Unsafe manifest path: '+name)
        target = assert_safe_target(root, name)
        raw = target.read_bytes()
        if sha(raw) != evidence['sha256'] or len(raw) != evidence['bytes']:
            raise ValueError('Output differs from manifest; run render: '+name)
    aliases = read_json(root/'provenance/aliases.json')['aliases']
    curated = apply_curation(rows, read_json(root/CURATION))
    normalized, final_aliases = normalize(curated, aliases, {r['id'] for r in rows})
    if normalized != rows or final_aliases != aliases:
        raise ValueError('Curation and generated catalog differ; run render')
    available_ids = {r['id'] for r in rows} | {e['id'] for e in read_json(root/CURATION)['exclusions']}
    if any(target not in available_ids for target in aliases.values()):
        raise ValueError('Alias target is absent from catalog and has no reviewed exclusion')
    expected, _ = build_outputs(rows, aliases, manifest, root)
    for name, raw in expected.items():
        if (root/name).read_bytes() != raw:
            raise ValueError('Generated output is stale: '+name)
    # Local Markdown links and fragments are checked without sending thousands
    # of unnecessary requests to listed third-party projects.
    for path in root.rglob('*.md'):
        if '.git' in path.parts: continue
        for href in re.findall(r'\]\(<?([^\s>)]+)>?\)', path.read_text()):
            if '://' in href or href.startswith(('mailto:', '#')): continue
            relative = href.split('#',1)[0]
            if relative and not (path.parent/relative).exists():
                raise ValueError('Broken local Markdown link: '+str(path.relative_to(root))+' → '+href)
    return {'entries':len(rows),'aliases':len(aliases),'generated_files':len(expected),'result':'passed'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['render','check','refresh'])
    parser.add_argument('--site-source', type=pathlib.Path, help='Optional local AgentBay public directory for byte-parity verification')
    parser.add_argument('--snapshot', action='store_true', help='Use published static curation snapshots instead of live APIs; records that limitation')
    args = parser.parse_args()
    if args.command != 'refresh' and (args.snapshot or args.site_source):
        parser.error('--snapshot and --site-source apply only to refresh')
    validate_policy(PREFERRED_PROVIDERS)
    if args.command == 'check':
        print(json.dumps(check(), indent=2)); return
    previous = read_json(ROOT/'sync-manifest.json')
    current = read_json(ROOT/'catalog.json'); validate_rows(current)
    baseline_ids = {row['id'] for row in current}
    # Protect the maintained baseline against accidental hand edits before render.
    for name in ('catalog.json','catalog.csv'):
        if sha((ROOT/name).read_bytes()) != previous['files'][name]['sha256']:
            raise ValueError('Baseline export was edited directly; use '+CURATION+': '+name)
    alias_path = ROOT/'provenance/aliases.json'
    aliases = read_json(alias_path)['aliases'] if alias_path.exists() else {}
    manifest = dict(previous)
    if 'upstream' not in manifest:
        manifest['upstream'] = {'url':ORIGIN,'imported_at':previous.get('synced_at'),
            'mode':previous.get('verification',{}).get('mode','legacy_import'),
            'source_sha256':previous.get('source_sha256',{}),
            'selected_entries':len(current),'excluded':previous.get('excluded_entries',{})}
    if args.command == 'refresh':
        if args.snapshot:
            paths = [p for p in PATHS if not p.startswith('api/')]+['catalog-visibility-snapshot.json','github-metadata.json']
        else:
            paths = PATHS
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            responses = dict(pool.map(fetch, paths))
        if args.snapshot:
            responses['api/catalog'] = ({'items':responses['catalog-edits-snapshot.json'][0]},None)
            responses['api/visibility'] = (responses['catalog-visibility-snapshot.json'][0],None)
            responses['api/github-metadata'] = (responses['github-metadata.json'][0],None)
        elif any(value is None for value in responses.values()):
            raise ValueError('Live APIs unavailable; retry or explicitly choose --snapshot')
        if args.site_source:
            for path, (_, digest) in responses.items():
                if not path.startswith('api/') and sha((args.site_source/path).read_bytes()) != digest:
                    raise ValueError('Local/deployed public data differ: '+path)
        incoming, excluded = build({p:v[0] for p,v in responses.items()})
        if not incoming: raise ValueError('Empty upstream result; preserving current catalog')
        validate_rows(incoming)
        current, delta = augment(current, incoming, aliases)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        manifest['upstream'] = {'url':ORIGIN,'imported_at':now,
            'mode':'packaged_snapshot' if args.snapshot else 'live_api',
            'source_sha256':{p:v[1] for p,v in responses.items() if v[1]},
            'selected_entries':len(incoming),'excluded':excluded}
        manifest['last_refresh'] = {'at':now,**delta}
    current = apply_curation(current, read_json(ROOT/CURATION))
    current, aliases = normalize(current, aliases, baseline_ids)
    outputs, manifest = build_outputs(current, aliases, manifest)
    write_outputs(outputs, previous)
    print(json.dumps({'entries':len(current),'duplicate_id_aliases':len(aliases),'mode':args.command},indent=2))


if __name__ == '__main__':
    main()
