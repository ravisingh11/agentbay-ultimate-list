import io
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import skill_bundle as bundle

def fixture(root):
    source=root/bundle.installer.RELATIVE
    source.parent.mkdir(parents=True)
    source.write_bytes((ROOT/bundle.installer.RELATIVE).read_bytes())
    return source

class SkillBundleTests(unittest.TestCase):
    def test_zip_contains_only_exact_source_and_is_deterministic(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d).resolve();source=fixture(root)
            (source.parent/'.env').write_text('do not package local settings')
            bundle.build(root);first=(root/bundle.ARCHIVE).read_bytes();bundle.build(root)
            self.assertEqual(first,(root/bundle.ARCHIVE).read_bytes())
            with zipfile.ZipFile(io.BytesIO(first)) as archive:
                self.assertEqual(archive.namelist(),[bundle.ENTRY])
                self.assertEqual(archive.read(bundle.ENTRY),source.read_bytes())
            source.write_bytes(source.read_bytes()+b'\nA maintained change.\n')
            with self.assertRaises(ValueError):bundle.check(root)
            bundle.build(root);bundle.check(root)

    def test_desktop_description_limit_preserves_the_previous_download(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d).resolve();source=fixture(root);bundle.build(root)
            original=(root/bundle.ARCHIVE).read_bytes()
            text=source.read_text();description=next(line for line in text.splitlines() if line.startswith('description: '))
            source.write_text(text.replace(description,'description: '+'x'*201,1))
            with self.assertRaisesRegex(ValueError,'200 characters'):bundle.build(root)
            self.assertEqual((root/bundle.ARCHIVE).read_bytes(),original)

    def test_symlinks_and_unowned_outputs_are_preserved(self):
        for mode in ('source','destination','checksum','archive'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as d:
                root=pathlib.Path(d).resolve();source=fixture(root)
                outside=root/'outside';outside.write_bytes(b'preserve me')
                if mode=='source':source.unlink();source.symlink_to(outside)
                elif mode=='destination':
                    target=root/bundle.ARCHIVE;target.parent.mkdir();target.symlink_to(outside)
                else:
                    bundle.build(root)
                    if mode=='checksum':(root/bundle.CHECKSUM).write_bytes(b'manual checksum')
                    else:
                        with zipfile.ZipFile(root/bundle.ARCHIVE,'w') as archive:archive.writestr('unowned','keep')
                before={str(p):p.read_bytes() for p in (root/bundle.ARCHIVE,root/bundle.CHECKSUM) if p.exists()}
                with self.assertRaises(ValueError):bundle.build(root)
                self.assertEqual(outside.read_bytes(),b'preserve me')
                self.assertEqual(before,{str(p):p.read_bytes() for p in (root/bundle.ARCHIVE,root/bundle.CHECKSUM) if p.exists()})

class InstallerScriptTests(unittest.TestCase):
    def run_script(self,root,agent,failed=False,old_node=False):
        tools=root/'bin';tools.mkdir(exist_ok=True)
        npx=tools/'npx'
        npx.write_text('#!'+sys.executable+'\n'+'''import pathlib,sys,json
root=pathlib.Path.cwd()
with (root/'calls.jsonl').open('a') as out:out.write(json.dumps(sys.argv[1:])+'\\n')
if '''+str(failed)+''':sys.exit(1)
args=sys.argv[1:];agents=args[args.index('--agent')+1:args.index('--yes',2)]
canonical=root/'.agents/skills/agentbay-skill-installer';canonical.mkdir(parents=True)
(canonical/'SKILL.md').write_text('installed instructions')
if 'claude-code' in agents:
    binding=root/'.claude/skills/agentbay-skill-installer';binding.parent.mkdir(parents=True);binding.symlink_to(canonical,target_is_directory=True)
''')
        npx.chmod(0o755)
        if old_node:
            (tools/'node').write_text('#!/bin/sh\nexit 1\n');(tools/'node').chmod(0o755)
        env=os.environ.copy();env['PATH']=str(tools)+os.pathsep+env['PATH'];env.pop('AGENTBAY_REF',None)
        return subprocess.run(['bash',str(ROOT/'install.sh'),agent],cwd=root,env=env,text=True,capture_output=True)

    def test_both_agents_share_one_package_and_repeat_preserves_files(self):
        with tempfile.TemporaryDirectory(prefix='agentbay project ') as d:
            root=pathlib.Path(d);result=self.run_script(root,'both')
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue((root/'.claude/skills/agentbay-skill-installer').is_symlink())
            self.assertEqual((root/'.agents/skills/agentbay-skill-installer/SKILL.md').read_text(),'installed instructions')
            result=self.run_script(root,'both');self.assertNotEqual(result.returncode,0)
            self.assertEqual(len((root/'calls.jsonl').read_text().splitlines()),1)

    def test_failure_or_old_node_never_reports_success(self):
        for mode in ('network','node'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as d:
                root=pathlib.Path(d);result=self.run_script(root,'codex',failed=mode=='network',old_node=mode=='node')
                self.assertNotEqual(result.returncode,0);self.assertNotIn('files installed',result.stdout)
                self.assertFalse((root/'.agents').exists())

    def test_invalid_agent_and_dangling_destination_are_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);result=self.run_script(root,'claude-desktop')
            self.assertEqual(result.returncode,2);self.assertFalse((root/'calls.jsonl').exists())
            path=root/'.agents/skills/agentbay-skill-installer';path.parent.mkdir(parents=True);path.symlink_to(root/'missing')
            result=self.run_script(root,'codex');self.assertNotEqual(result.returncode,0)
            self.assertTrue(path.is_symlink());self.assertFalse((root/'calls.jsonl').exists())
