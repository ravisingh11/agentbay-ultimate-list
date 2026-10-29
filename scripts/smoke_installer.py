#!/usr/bin/env python3
"""Optional, real Codex install/use test in a disposable Docker container."""
import argparse
import datetime
import json
import os
import pathlib
import re
import shutil
import subprocess
import uuid
import zipfile

import installer
import example_bundle

ROOT=pathlib.Path(__file__).resolve().parent.parent
DEFAULT_IMAGE='agentbay-installer-smoke:codex-0.163.0'
DOCKERFILE='''FROM node:22-bookworm
RUN npm install --global @openai/codex@0.163.0 && npm cache clean --force
WORKDIR /work
'''
NATIVE_LIST=r'''
const fs=require('node:fs');const {spawn}=require('node:child_process');
const child=spawn('codex',['app-server','--stdio'],{stdio:['pipe','pipe','pipe']});
let buffer='';const timer=setTimeout(()=>{child.kill();process.exit(2)},60000);
child.stdout.on('data',chunk=>{buffer+=chunk;let i;while((i=buffer.indexOf('\n'))>=0){
 const line=buffer.slice(0,i);buffer=buffer.slice(i+1);let message;try{message=JSON.parse(line)}catch{continue}
 if(message.id===1){if(message.error)throw Error(JSON.stringify(message.error));
 child.stdin.write(JSON.stringify({method:'initialized'})+'\n');
 child.stdin.write(JSON.stringify({id:2,method:'skills/list',params:{cwds:[process.argv[2]||'/work'],forceReload:true}})+'\n')}
 if(message.id===2){clearTimeout(timer);fs.writeFileSync(process.argv[1],JSON.stringify(message,null,2));
 child.kill();process.exit(message.error?1:0)}
}});
child.stdin.write(JSON.stringify({id:1,method:'initialize',params:{clientInfo:{name:'agentbay-first-use',version:'1'},capabilities:{experimentalApi:true}}})+'\n');
'''
WORKER_RUNTIME=r'''
const fs=require('node:fs'),{spawn}=require('node:child_process');
(async()=>{
 const phase=process.argv[1], log=fs.openSync('/evidence/runtime-'+phase+'.log','w');
 const child=spawn('npm',['run','dev'],{cwd:'/work',detached:true,
   env:{...process.env,WRANGLER_SEND_METRICS:'false'},stdio:['ignore',log,log]});
 try{
  let started=false;
  for(let i=0;i<240;i++){
   if(child.exitCode!==null)throw Error('Local Worker exited during startup; inspect runtime log');
   try{if((await fetch('http://127.0.0.1:8787/missing')).status===404){started=true;break}}catch{}
   await new Promise(r=>setTimeout(r,250));
  }
  if(!started)throw Error('Local Worker did not start; inspect runtime log');
  const unnamed=await fetch('http://127.0.0.1:8787/hello');
  const named=await fetch('http://127.0.0.1:8787/hello?name=Ada');
  const missing=await fetch('http://127.0.0.1:8787/missing');
  const result={unnamed_status:unnamed.status,named_status:named.status,
    named_body:await named.json(),missing_status:missing.status};
  if(phase==='after')result.unnamed_body=await unnamed.json();
  fs.writeFileSync('/evidence/runtime-'+phase+'.json',JSON.stringify(result,null,2));
  if(result.unnamed_status!==(phase==='before'?500:200)||result.named_status!==200||
     result.named_body.message!=='Hello, ADA!'||result.missing_status!==404||
     (phase==='after'&&result.unnamed_body.message!=='Hello, WORLD!'))throw Error('Unexpected local Worker behavior');
  console.log(JSON.stringify(result));
 }finally{
  try{process.kill(-child.pid,'SIGTERM')}catch{}
  fs.closeSync(log);
 }
})().catch(e=>{console.error(e.message);process.exitCode=1});
'''


def run(command,log=None,timeout=900):
    result=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
    if log:log.write_text(result.stdout+('\nSTDERR\n'+result.stderr if result.stderr else ''))
    if result.returncode:
        raise RuntimeError('Command failed ('+str(result.returncode)+'): '+command[0]+'; '+('inspect '+str(log) if log else result.stderr[-2000:]))
    return result.stdout


def native_skills(path):
    payload=json.loads(path.read_text())
    if payload.get('error'):raise ValueError('Codex native discovery failed')
    data=payload['result']['data']
    if len(data)!=1 or data[0].get('errors'):raise ValueError('Codex returned discovery errors')
    return data[0]['skills']


def observed_file_read(items, relative, expected_text):
    for item in items:
        command=str(item.get('command',''))
        if relative not in command:
            continue
        reader=re.search(r'\b(cat|sed|head|jq|read_text|read_bytes|readFile(?:Sync)?|open)\b',command)
        if reader and item.get('exit_code')==0:
            return True
        # A compound command can print the entire file and then fail in a later
        # component. Confirm its output rather than treating that as a failed read.
        if reader and expected_text.strip() and expected_text.strip() in item.get('aggregated_output',''):
            return True
    return False


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=pathlib.Path)
    parser.add_argument('--codex-auth-file',type=pathlib.Path)
    parser.add_argument('--install-only',action='store_true',help='Credential-free candidate installation and native discovery check for CI')
    parser.add_argument('--discovery-only',action='store_true',help='Test the natural AgentBay request without authorizing installation or edits')
    parser.add_argument('--scenario',choices=['html','cloudflare'],default='html',help='Representative task for the authenticated full run')
    parser.add_argument('--image',default=DEFAULT_IMAGE,help='Prepared Docker image; use a digest to repeat an exact environment')
    args=parser.parse_args()
    if args.discovery_only and (args.install_only or args.scenario!='html'):
        parser.error('--discovery-only uses the HTML fixture and cannot be combined with --install-only')
    output=args.output.resolve()
    if output.exists():parser.error('Choose a new output directory to preserve previous evidence')
    configured=os.environ.get('CODEX_HOME')
    auth=args.codex_auth_file or ((pathlib.Path(configured) if configured else pathlib.Path.home()/'.codex')/'auth.json')
    if not args.install_only and not auth.is_file():parser.error('Codex auth.json is unavailable; sign in normally or pass --codex-auth-file')
    output.mkdir(parents=True)
    work=output/'project';work.mkdir()
    artifact=output/'published';artifact.mkdir()
    evidence=output/'evidence';evidence.mkdir()
    baseline=output/'public-baseline';baseline.mkdir()
    (output/'Dockerfile').write_text(DOCKERFILE)
    if args.scenario=='html':
        fixture=ROOT/'docs/examples/first-use.html'
        shutil.copyfile(fixture,work/'first-use.html')
        fixture_hash=installer.digest(fixture.read_bytes())
    else:
        bundle_info=example_bundle.check()
        with zipfile.ZipFile(ROOT/example_bundle.ARCHIVE) as archive:
            for relative in list(example_bundle.SOURCES)+['source-manifest.json']:
                target=work/relative
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(archive.read(example_bundle.PREFIX+'/'+relative))
        fixture_hash={p.relative_to(work).as_posix():installer.digest(p.read_bytes()) for p in work.rglob('*') if p.is_file()}
    raw,revision=installer.source()
    released=installer.stage(artifact,raw,revision)
    ui_relative=installer.RELATIVE.parent/'agents/openai.yaml'
    ui_raw=(ROOT/ui_relative).read_bytes()
    ui_target=artifact/ui_relative;ui_target.parent.mkdir(parents=True);ui_target.write_bytes(ui_raw)
    catalogue=output/'catalogue-snapshot';catalogue.mkdir()
    catalogue_revision=run(['git','-C',str(ROOT),'rev-parse','HEAD']).strip()
    context={'repository':'https://github.com/ravisingh11/agentbay-ultimate-list',
             'source_revision':catalogue_revision,'files':{}}
    for relative in ('skills/catalog.json','data/preferred-providers.json','sync-manifest.json'):
        payload=subprocess.check_output(['git','-C',str(ROOT),'show',catalogue_revision+':'+relative])
        target=catalogue/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(payload)
        context['files'][relative]={'sha256':installer.digest(payload),'bytes':len(payload)}
    (catalogue/'source.json').write_text(json.dumps(context,indent=2)+'\n')
    # Validate the public endpoint separately from this unreleased candidate.
    public=None if args.install_only else installer.fetch(installer.PUBLIC_URL)
    public_info=None if public is None else installer.validate(public)
    (evidence/'published-baseline.json').write_text(json.dumps(public_info,indent=2)+'\n')
    if subprocess.run(['docker','image','inspect',args.image],capture_output=True).returncode:
        run(['docker','build','--pull','-t',args.image,str(output)],evidence/'image-build.log')
    image=json.loads(run(['docker','image','inspect',args.image]))[0]
    name='agentbay-first-use-'+uuid.uuid4().hex[:10]
    mounts=['--mount','type=bind,src='+str(work)+',dst=/work',
            '--mount','type=bind,src='+str(artifact)+',dst=/published,readonly',
            '--mount','type=bind,src='+str(catalogue)+',dst=/agentbay-catalogue,readonly',
            '--mount','type=bind,src='+str(evidence)+',dst=/evidence',
            '--mount','type=bind,src='+str(baseline)+',dst=/public-baseline']
    if not args.install_only:
        mounts+=['--mount','type=bind,src='+str(auth.resolve())+',dst=/root/.codex/auth.json,readonly']
    receipt={'candidate':released,'public_download':public_info,'image_id':image['Id'],
             'catalogue_context':context,
             'scenario':args.scenario,'fixture_sha256':fixture_hash,
             'container_name':name,'install_only':args.install_only,'tested_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':{},'passed':False}
    receipt['discovery_only']=args.discovery_only
    if args.scenario=='cloudflare':receipt['example_download']=bundle_info
    def require(condition, label):
        receipt['checks'][label]=bool(condition)
        if not condition:raise ValueError('Acceptance check failed: '+label)
    try:
        run(['docker','run','--detach','--name',name,'--env','WRANGLER_SEND_METRICS=false',*mounts,args.image,'sleep','infinity'])
        def execute(*command,log=None,timeout=900):
            return run(['docker','exec',name,*command],evidence/log if log else None,timeout)
        receipt['node_version']=execute('node','--version').strip()
        receipt['codex_version']=execute('codex','--version').strip()
        execute('git','init','--quiet','/work')
        execute('git','init','--quiet','/public-baseline')
        execute('node','-e',NATIVE_LIST,'/evidence/native-before.json')
        before=native_skills(evidence/'native-before.json')
        require(not any(s['name'] in (installer.NAME,'web-design-guidelines') for s in before),'clean_skill_baseline')
        print('Clean Codex discovery baseline confirmed.',flush=True)
        if not args.install_only:
            # Exercise the actual published URL independently of the candidate artifact.
            run(['docker','exec','--workdir','/public-baseline',name,'npx','--yes','skills@'+installer.CLI_VERSION,
                 'add',installer.PUBLIC_URL,'--agent','codex','--yes'],evidence/'public-install.log')
            require((baseline/'.agents/skills'/installer.NAME/'SKILL.md').read_bytes()==public,'public_download_installed_unchanged')
            execute('node','-e',NATIVE_LIST,'/evidence/native-public.json','/public-baseline')
            require(any(s['name']==installer.NAME and s.get('enabled') for s in native_skills(evidence/'native-public.json')),'public_download_discovered')
            print('Published website download installed and discovered by Codex.',flush=True)
        repository_url='https://github.com/ravisingh11/agentbay-ultimate-list/tree/main/skills/'+installer.NAME
        readme=(ROOT/'README.md').read_text()
        command=re.search(r'^npx(?: --yes)? skills@[^\n]+ add '+re.escape(repository_url)+r' --skill '+installer.NAME+r' --agent codex(?: --yes)?$',readme,re.M)
        if not command:raise ValueError('README quick-start command was not found')
        import shlex
        # Test the candidate repository folder without needing private GitHub credentials in CI.
        arguments=shlex.split(command[0].replace(repository_url,'/published/'+installer.RELATIVE.parent.as_posix()))
        if arguments[1]=='--yes':arguments.pop(1)
        if arguments[-1]=='--yes':arguments.pop()
        require(arguments[1]=='skills@'+installer.CLI_VERSION,'readme_uses_supported_cli_version')
        arguments.insert(1,'--yes');arguments.append('--yes')
        execute(*arguments,log='candidate-install.log')
        require((work/'.agents/skills'/installer.NAME/'SKILL.md').read_bytes()==raw,'candidate_installed_unchanged')
        require((work/'.agents/skills'/installer.NAME/'agents/openai.yaml').read_bytes()==ui_raw,'native_ui_metadata_installed_unchanged')
        receipt['ui_metadata_sha256']=installer.digest(ui_raw)
        execute('npx','--yes','skills@'+installer.CLI_VERSION,'list','--agent','codex',log='installer-list.log')
        execute('node','-e',NATIVE_LIST,'/evidence/native-installed.json')
        installed=native_skills(evidence/'native-installed.json')
        require(sum(s['name']==installer.NAME and s.get('enabled') for s in installed)==1,'candidate_discovered_once')
        entry=next(s for s in installed if s['name']==installer.NAME)
        require(entry.get('interface',{}).get('displayName')=='AgentBay','native_agentbay_display_name')
        require(entry.get('scope')=='repo' and entry.get('path')=='/work/.agents/skills/'+installer.NAME+'/SKILL.md','candidate_discovered_at_project_path')
        print('README repository-folder install matched candidate bytes; native discovery passed.',flush=True)
        receipt['skills_cli_version']=execute('npx','--yes','skills@'+installer.CLI_VERSION,'--version').strip()
        if args.install_only:
            receipt['passed']=True
            return
        if args.scenario=='cloudflare':
            execute('env','WRANGLER_SEND_METRICS=false','npm','ci','--no-audit','--no-fund',log='worker-install.log')
            receipt['wrangler_version']=execute('env','WRANGLER_SEND_METRICS=false','npx','--no-install','wrangler','--version').strip()
            baseline_test=subprocess.run(['docker','exec',name,'npm','test'],capture_output=True,text=True,timeout=120)
            (evidence/'tests-before.log').write_text(baseline_test.stdout+baseline_test.stderr)
            require(baseline_test.returncode!=0 and 'toUpperCase' in baseline_test.stdout+baseline_test.stderr,'fixture_fails_before_fix')
            execute('node','-e',WORKER_RUNTIME,'before',log='runtime-before-check.log',timeout=120)
            require(json.loads((evidence/'runtime-before.json').read_text())['unnamed_status']==500,'local_runtime_reproduces_failure')
            require(execute('node','-p',"['CLOUDFLARE_API_TOKEN','CLOUDFLARE_API_KEY','CF_API_TOKEN','CF_API_KEY'].every(k=>!process.env[k])").strip()=='true','no_cloudflare_credentials_supplied')
            guide=(ROOT/'docs/cloudflare-first-use.md').read_text()
            prompt=next(line[2:] for line in guide.splitlines() if line.startswith('> Find a skill for '))
        elif args.discovery_only:
            guide=(ROOT/'docs/using-skills.md').read_text()
            prompt=next(line[2:] for line in guide.splitlines() if line.startswith('> Find a skill for [my task]'))
            prompt=prompt.replace('[my task]','reviewing HTML accessibility')
        else:
            guide=(ROOT/'docs/using-skills.md').read_text()
            prompt=next(line[2:] for line in guide.splitlines() if line.startswith('> $agentbay-skill-installer Read .agents/skills/agentbay-skill-installer/SKILL.md.'))
        prompt+=' For this isolated run, use the read-only AgentBay repository snapshot at /agentbay-catalogue; its source revision and file hashes are in /agentbay-catalogue/source.json. Do not change GitHub authentication.'
        receipt['prompt']=prompt
        print('Running the worked example through Codex; this may take a few minutes.',flush=True)
        command=['docker','exec',name,'codex','exec','--ephemeral','--json',
                 '--dangerously-bypass-approvals-and-sandbox','--cd','/work',
                 '--output-last-message','/evidence/review.md',prompt]
        result=subprocess.run(command,capture_output=True,text=True,timeout=900)
        (evidence/'codex-events.jsonl').write_text(result.stdout)
        (evidence/'codex-stderr.log').write_text(result.stderr)
        require(result.returncode==0,'codex_task_completed')
        events=[]
        for line in result.stdout.splitlines():
            try:events.append(json.loads(line))
            except json.JSONDecodeError:continue
        completed=[e.get('item',{}) for e in events if e.get('type')=='item.completed' and e.get('item',{}).get('type')=='command_execution']
        commands=[item for item in completed if item.get('exit_code')==0]
        read_commands=[str(c.get('command','')) for c in commands if re.search(r'\b(cat|sed|head|jq|read_text|read_bytes|readFile(?:Sync)?|open)\b',str(c.get('command','')))]
        require(any('.agents/skills/'+installer.NAME+'/SKILL.md' in c for c in read_commands),'installed_installer_instructions_read')
        require(any('skills/catalog.json' in str(c.get('command','')) for c in commands),'repository_catalogue_searched')
        registry='data/preferred-providers.json'
        require(observed_file_read(completed,registry,(catalogue/registry).read_text()),'repository_publisher_registry_read')
        locks=json.loads((work/'skills-lock.json').read_text())
        children={k:v for k,v in locks.get('skills',{}).items() if k!=installer.NAME}
        if args.discovery_only:
            require(not children,'discovery_request_did_not_install_task_skills')
            require(installer.digest((work/'first-use.html').read_bytes())==fixture_hash,'discovery_request_did_not_edit_application')
            execute('node','-e',NATIVE_LIST,'/evidence/native-after.json')
            after=native_skills(evidence/'native-after.json')
            before=native_skills(evidence/'native-installed.json')
            require({s['name'] for s in after}=={s['name'] for s in before},'discovery_request_did_not_add_global_or_project_skills')
            require(bool((evidence/'review.md').read_text().strip()),'discovery_report_returned')
            receipt['passed']=True
            print('Natural AgentBay discovery passed without task installation or edits.',flush=True)
            return
        require(len(children)==1,'one_task_skill_installed')
        child_name,lock=next(iter(children.items()))
        child=work/'.agents/skills'/child_name/'SKILL.md'
        require(child.is_file(),'upstream_skill_installed')
        require(observed_file_read(completed,'.agents/skills/'+child_name+'/SKILL.md',child.read_text()),'installed_upstream_instructions_read')
        receipt['upstream_skill_sha256']=installer.digest(child.read_bytes())
        receipt['upstream_lock']=lock;receipt['selected_skill']=child_name
        owners={o for p in json.loads((catalogue/'data/preferred-providers.json').read_text())['providers'] for o in p['github_owners']}
        require(lock.get('sourceType')=='github' and lock.get('source','').split('/')[0].lower() in owners and
                lock.get('skillPath','').endswith('/SKILL.md') and
                bool(re.fullmatch(r'[0-9a-f]{40}',lock.get('ref',''))),'verified_official_upstream_selected')
        upstream_url='https://raw.githubusercontent.com/'+lock['source']+'/'+lock['ref']+'/'+lock['skillPath']
        require(installer.fetch(upstream_url)==child.read_bytes(),'upstream_skill_matches_pinned_source')
        if args.scenario=='cloudflare':
            require(lock['source'].split('/')[0].lower()=='cloudflare','cloudflare_publisher_selected')
            companions={}
            from urllib.parse import urljoin
            for href in re.findall(r'\]\(([^\s)]+)\)',child.read_text()):
                relative=href.split('#',1)[0]
                if not relative or '://' in relative or relative.startswith(('mailto:','/')):continue
                companion=(child.parent/relative).resolve()
                require(companion.is_relative_to(child.parent.resolve()) and companion.is_file(),'companion_file_present_'+relative)
                require(companion.read_bytes()==installer.fetch(urljoin(upstream_url,relative)),'companion_file_matches_'+relative)
                companions[relative]=installer.digest(companion.read_bytes())
            receipt['companion_files']=companions
        review=(evidence/'review.md').read_text()
        matching_rows=[r for r in json.loads((catalogue/'skills/catalog.json').read_text())
                       if r['repository_url'].rstrip('/').lower()=='https://github.com/'+lock['source'].lower() and r['id'] in review]
        require(bool(matching_rows),'selected_catalogue_listing_reported')
        require(catalogue_revision in review,'catalogue_revision_reported')
        receipt['selected_listing_ids']=[r['id'] for r in matching_rows]
        if args.scenario=='html':
            expected={'input':11,'button':12,'image':14}
            for label,line in expected.items():
                require(bool(re.search(r'first-use\.html(?::|#L)'+str(line)+r'\b',review)),label+'_location_reported')
            require('label' in review.lower() and ('alt' in review.lower() or 'alternative text' in review.lower()),'expected_defects_described')
            require(installer.digest((work/'first-use.html').read_bytes())==fixture_hash,'fixture_unchanged')
        else:
            require(any(re.search(r'\bnpm(?: run)? test\b',c.get('command','')) for c in commands),'agent_ran_passing_tests')
            execute('npm','test',log='tests-after.log')
            execute('env','WRANGLER_SEND_METRICS=false','npm','run','check',log='worker-dry-run.log')
            execute('node','-e',WORKER_RUNTIME,'after',log='runtime-after-check.log',timeout=120)
            require(json.loads((evidence/'runtime-after.json').read_text())['unnamed_status']==200,'local_runtime_fixed')
            for relative,digest in fixture_hash.items():
                if relative=='src/index.js':continue
                require(installer.digest((work/relative).read_bytes())==digest,'fixture_preserved_'+relative)
            require(installer.digest((work/'src/index.js').read_bytes())!=fixture_hash['src/index.js'],'worker_source_changed')
            receipt['runtime_before']=json.loads((evidence/'runtime-before.json').read_text())
            receipt['runtime_after']=json.loads((evidence/'runtime-after.json').read_text())
        execute('node','-e',NATIVE_LIST,'/evidence/native-after.json')
        after=native_skills(evidence/'native-after.json')
        require(all(any(s['name']==n and s.get('enabled') for s in after) for n in (installer.NAME,child_name)),'both_skills_discovered_after_use')
        task_entries=[s for s in after if s['name']==child_name and s.get('enabled')]
        require(len(task_entries)==1 and task_entries[0].get('scope')=='repo' and task_entries[0].get('path')=='/work/.agents/skills/'+child_name+'/SKILL.md','task_skill_discovered_only_in_project')
        receipt['passed']=True
        print('Install, native discovery and '+args.scenario+' task passed.',flush=True)
    except Exception as error:
        receipt['error']=str(error)
        raise
    finally:
        subprocess.run(['docker','rm','--force',name],capture_output=True)
        (evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print('Evidence: '+str(evidence),flush=True)


if __name__=='__main__':
    main()
