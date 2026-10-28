"""The first-use download contains exactly the maintained example and its license."""
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('example_bundle', ROOT/'scripts/example_bundle.py')
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)


def fixture(root):
    for name, relative in bundle.SOURCES.items():
        path = root/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(('maintained '+name+'\n').encode())


class ExampleBundleTests(unittest.TestCase):
    def test_reproducible_download_preserves_sources_and_excludes_extra_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve()
            fixture(root)
            (root/'docs/examples/cloudflare-worker/.env').write_text('private local settings')
            bundle.build(root)
            first = (root/bundle.ARCHIVE).read_bytes()
            bundle.build(root)
            self.assertEqual((root/bundle.ARCHIVE).read_bytes(), first)
            with zipfile.ZipFile(io.BytesIO(first)) as archive:
                expected = {bundle.PREFIX+'/'+name for name in bundle.SOURCES} | {bundle.PREFIX+'/source-manifest.json'}
                self.assertEqual(set(archive.namelist()), expected)
                manifest = json.loads(archive.read(bundle.PREFIX+'/source-manifest.json'))
                for name, relative in bundle.SOURCES.items():
                    raw = archive.read(bundle.PREFIX+'/'+name)
                    self.assertEqual(raw, (root/relative).read_bytes())
                    self.assertEqual(manifest['files'][name]['sha256'], bundle.digest(raw))
            self.assertEqual((root/bundle.CHECKSUM).read_bytes(), bundle.checksum(first))

    def test_source_change_requires_rebuilding_download_and_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve()
            fixture(root)
            bundle.build(root)
            old = (root/bundle.ARCHIVE).read_bytes()
            (root/bundle.SOURCES['src/index.js']).write_text('changed maintained source')
            with self.assertRaises(ValueError):
                bundle.check(root)
            bundle.build(root)
            self.assertNotEqual((root/bundle.ARCHIVE).read_bytes(), old)
            bundle.check(root)

    def test_symlinked_source_and_destination_are_refused(self):
        for mode in ('source', 'destination'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory).resolve()
                fixture(root)
                outside = root/'outside'
                outside.write_text('preserve this file')
                path = root/(bundle.SOURCES['src/index.js'] if mode == 'source' else bundle.ARCHIVE)
                path.unlink(missing_ok=True)
                path.symlink_to(outside)
                with self.assertRaises(ValueError):
                    bundle.build(root)
                self.assertEqual(outside.read_text(), 'preserve this file')

    def test_unowned_archive_or_modified_checksum_is_preserved(self):
        for mode in ('archive', 'checksum'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory).resolve()
                fixture(root)
                bundle.build(root)
                path = root/(bundle.ARCHIVE if mode == 'archive' else bundle.CHECKSUM)
                path.write_bytes(b'manual file')
                before = {p: p.read_bytes() for p in (root/bundle.ARCHIVE, root/bundle.CHECKSUM)}
                with self.assertRaises(ValueError):
                    bundle.build(root)
                self.assertEqual({p: p.read_bytes() for p in before}, before)


if __name__ == '__main__':
    unittest.main()
