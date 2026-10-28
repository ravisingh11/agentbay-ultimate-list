"""Integrity and publication contracts for the first-party installer."""
import importlib.util
import json
import pathlib
import subprocess
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('installer',ROOT/'scripts/installer.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
VALID=b'---\nname: agentbay-skill-installer\ndescription: Install a selected skill.\n---\n\nUse the selected skill.\n'


class InstallerTests(unittest.TestCase):
    def test_maintained_source_has_valid_frontmatter(self):
        result=installer.validate((ROOT/installer.RELATIVE).read_bytes())
        self.assertEqual(result['name'],'agentbay-skill-installer')
        self.assertGreater(result['bytes'],0)

    def test_stage_and_verify_identical_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            output=pathlib.Path(directory)
            metadata=installer.stage(output,VALID,'working-tree')
            raw=(output/installer.RELATIVE).read_bytes()
            self.assertEqual(raw,VALID)
            self.assertTrue(metadata['candidate_only'])
            self.assertEqual(installer.verify(raw,metadata,VALID,'working-tree')['sha256'],installer.digest(VALID))
            installer.stage(output,VALID,'working-tree')
            self.assertEqual(json.loads((output/installer.RELATIVE.parent/'release.json').read_bytes()),metadata)

    def test_changed_download_fails_integrity_check(self):
        with self.assertRaises(ValueError):
            installer.verify(VALID+b'changed',installer.manifest(VALID,'working-tree'))

    def test_changed_provenance_or_selected_revision_fails(self):
        for field,value in [('source_repository','https://example.com/unrelated'),('candidate_only',False),('source_revision','not-a-commit')]:
            with self.subTest(field=field),self.assertRaises(ValueError):
                installer.verify(VALID,{**installer.manifest(VALID,'working-tree'),field:value})
        with self.assertRaises(ValueError):
            installer.verify(VALID,installer.manifest(VALID,'a'*40),revision='b'*40)

    def test_stage_refuses_linked_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);outside=root/'outside';outside.mkdir()
            output=root/'public';output.mkdir();(output/'skills').symlink_to(outside,target_is_directory=True)
            with self.assertRaises(ValueError):installer.stage(output,VALID,'working-tree')
            self.assertEqual(list(outside.iterdir()),[])

    def test_stage_cannot_overwrite_the_maintained_source(self):
        original=(ROOT/installer.RELATIVE).read_bytes()
        with self.assertRaises(ValueError):installer.stage(ROOT,VALID,'working-tree')
        self.assertEqual((ROOT/installer.RELATIVE).read_bytes(),original)

    def test_source_revision_uses_committed_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);path=root/installer.RELATIVE;path.parent.mkdir(parents=True);path.write_bytes(VALID)
            subprocess.run(['git','init','--quiet',str(root)],check=True)
            subprocess.run(['git','add','.'],cwd=root,check=True)
            subprocess.run(['git','-c','user.name=Installer Test','-c','user.email=installer-test@example.invalid','commit','--quiet','-m','fixture'],cwd=root,check=True)
            path.write_bytes(VALID+b'uncommitted')
            raw,revision=installer.source('HEAD',root)
            self.assertEqual(raw,VALID)
            self.assertRegex(revision,r'^[0-9a-f]{40}$')

    def test_wrong_name_or_missing_metadata_is_rejected(self):
        for raw in [b'# Just markdown',VALID.replace(b'agentbay-skill-installer',b'another-skill'),VALID.replace(b'description:',b'no-description:')]:
            with self.subTest(raw=raw),self.assertRaises(ValueError):installer.validate(raw)


if __name__=='__main__':unittest.main()
