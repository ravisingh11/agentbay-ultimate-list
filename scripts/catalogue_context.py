#!/usr/bin/env python3
"""Fetch a pinned AgentBay catalogue snapshot; never install or run a skill."""
import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import urllib.error
import urllib.request
import catalog

REPOSITORY='ravisingh11/agentbay-ultimate-list'
FILES=('skills/catalog.json','data/preferred-providers.json','sync-manifest.json')

def digest(raw):return hashlib.sha256(raw).hexdigest()

def public_get(url):
    request=urllib.request.Request(url,headers={'User-Agent':'AgentBay-Catalogue-Context','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(request,timeout=60) as response:
        if response.status!=200:raise ValueError('Repository request did not return HTTP 200')
        return response.read()

def github_get(endpoint,raw=False):
    command=['gh','api','--hostname','github.com']
    if raw:command+=['-H','Accept: application/vnd.github.raw+json']
    result=subprocess.run(command+[endpoint],capture_output=True,timeout=90)
    if result.returncode:raise ValueError('GitHub access failed. Confirm that gh is authenticated with repository access.')
    return result.stdout

def load(access,revision=None,*,http=public_get,github=github_get):
    if access not in ('auto','public','github'):raise ValueError('Unknown access mode')
    if revision is not None and not re.fullmatch(r'[0-9a-f]{40}',revision):raise ValueError('Use a full 40-character commit for --revision')
    mode='public' if access!='github' else 'github'
    def retrieve(mode):
        commit=revision
        if commit is None:
            endpoint='repos/'+REPOSITORY+'/commits/main'
            commit=json.loads(http('https://api.github.com/'+endpoint) if mode=='public' else github(endpoint))['sha']
            if not re.fullmatch(r'[0-9a-f]{40}',commit):raise ValueError('GitHub returned an invalid revision')
        payloads={}
        for name in FILES:
            payloads[name]=http('https://raw.githubusercontent.com/'+REPOSITORY+'/'+commit+'/'+name) if mode=='public' else github('repos/'+REPOSITORY+'/contents/'+name+'?ref='+commit,raw=True)
        return commit,payloads
    try:commit,payloads=retrieve(mode)
    except urllib.error.HTTPError as error:
        if access!='auto' or error.code not in (401,403,404):
            raise ValueError('Public repository access returned HTTP '+str(error.code)+'. Private repositories require authorized access; public API limits may require retrying or a known commit.') from None
        mode='github'
        try:commit,payloads=retrieve(mode)
        except FileNotFoundError:raise ValueError('Public access is unavailable and GitHub CLI is missing. Use an authorized checkout or install/sign in to gh for private access.') from None
    decoded={name:json.loads(raw) for name,raw in payloads.items()}
    manifest=decoded['sync-manifest.json']
    if not isinstance(manifest,dict) or not isinstance(manifest.get('files'),dict) or not isinstance(manifest.get('inputs'),dict):raise ValueError('Invalid snapshot manifest')
    for name in FILES[:2]:
        evidence=manifest.get('files',{}).get(name) or manifest.get('inputs',{}).get(name)
        if not isinstance(evidence,dict) or evidence.get('sha256')!=digest(payloads[name]) or ('bytes' in evidence and evidence['bytes']!=len(payloads[name])):raise ValueError('Snapshot checksum mismatch: '+name)
    skills=decoded['skills/catalog.json'];policy=decoded['data/preferred-providers.json']
    if not isinstance(policy,dict):raise ValueError('Invalid publisher registry')
    catalog.validate_rows(skills);catalog.validate_policy(policy)
    if not skills or not policy['providers'] or any(not catalog.is_skill(row) for row in skills):raise ValueError('Snapshot must contain skills and verified publisher metadata')
    source={'repository':'https://github.com/'+REPOSITORY,'source_revision':commit,'access_mode':'public_https' if mode=='public' else 'authenticated_github_cli','files':{name:{'sha256':digest(raw),'bytes':len(raw)} for name,raw in payloads.items()}}
    return payloads,source

def save(output,payloads,source):
    output=output.absolute()
    if any(p.is_symlink() for p in [output,*output.parents]):raise ValueError('Refusing a symlinked output path')
    if output.exists():raise ValueError('Choose a new output directory; existing files are preserved')
    if not output.parent.is_dir():raise ValueError('Output parent must already exist')
    output.mkdir()
    for name,raw in payloads.items():
        path=output/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    (output/'source.json').write_text(json.dumps(source,indent=2)+'\n')
    return output

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=pathlib.Path)
    parser.add_argument('--revision',help='Exact commit; default resolves main once')
    parser.add_argument('--access',choices=['auto','public','github'],default='auto',help='public never invokes GitHub CLI; github uses existing authorized gh access')
    args=parser.parse_args()
    try:
        payloads,source=load(args.access,args.revision);output=save(args.output,payloads,source)
    except ValueError as error:
        raise SystemExit('Context retrieval failed: '+str(error)+'. Existing snapshots were preserved.') from None
    except (OSError,KeyError,TypeError,subprocess.SubprocessError):
        raise SystemExit('Context retrieval failed; existing snapshots were preserved. Check network/GitHub access, revision and output path, then retry.') from None
    print(json.dumps({'output':str(output),**source},indent=2))

if __name__=='__main__':main()
