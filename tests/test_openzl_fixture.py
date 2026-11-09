import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PACKAGE = Path(os.environ.get('OPENZL_ADAPTATION_PACKAGE', str(
    Path(__file__).resolve().parents[1] / 'skills/agentbay-openzl-benchmark-scenarios')))
HELPER = PACKAGE / 'scripts/prepare_data.py'


class FixtureBehavior(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='agentbay-openzl-package-test-')
        self.parent = Path(self.temp.name).resolve() / 'parent with spaces'
        self.parent.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def run_helper(self, *args):
        return subprocess.run([sys.executable, str(HELPER), '--parent', str(self.parent), *args],
                              capture_output=True, text=True, timeout=15)

    def generated(self, *args):
        r = self.run_helper(*args)
        self.assertEqual(r.returncode, 0, r.stderr)
        directory = Path(r.stdout.strip())
        self.assertEqual(directory.parent, self.parent)
        return directory, json.loads((directory / 'dataset.json').read_text()), (directory / 'input.bin').read_bytes()

    def test_manifest_and_little_endian_elements(self):
        directory, manifest, raw = self.generated('--bytes', '4096', '--element-width', '4', '--seed', '17')
        self.assertEqual(len(raw), 4096)
        self.assertEqual(raw[:8], b'\x11\0\0\0\x12\0\0\0')
        self.assertEqual(manifest['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(manifest['elements'], 1024)
        self.assertTrue(manifest['synthetic'])
        self.assertEqual(manifest['input'], 'input.bin')
        self.assertEqual(directory.stat().st_mode & 0o777, 0o700)

    def test_runs_are_unique_and_preserve_previous_data(self):
        keep = self.parent / 'existing.bin'
        keep.write_bytes(b'preserve this caller-owned file')
        first, _, before = self.generated('--bytes', '64')
        second, _, after = self.generated('--bytes', '64')
        self.assertNotEqual(first, second)
        self.assertEqual(before, after)
        self.assertEqual((first / 'input.bin').read_bytes(), before)
        self.assertEqual(keep.read_bytes(), b'preserve this caller-owned file')

    def test_zeroes_and_eight_byte_alignment(self):
        _, manifest, raw = self.generated('--bytes', '64', '--element-width', '8', '--pattern', 'zeroes')
        self.assertEqual(raw, bytes(64))
        self.assertEqual(manifest['elements'], 8)

    def test_one_byte_ramp_wraps_without_overflow(self):
        _, _, raw = self.generated('--bytes', '512', '--element-width', '1', '--seed', '255')
        self.assertEqual(raw[:3], b'\xff\0\x01')
        self.assertEqual(raw[:256], raw[256:])

    def test_two_byte_element_layout(self):
        _, _, raw = self.generated('--bytes', '8', '--element-width', '2', '--seed', '256')
        self.assertEqual(raw, b'\0\x01\x01\x01\x02\x01\x03\x01')

    def test_seed_changes_data(self):
        _, _, one = self.generated('--bytes', '64', '--seed', '17')
        _, _, two = self.generated('--bytes', '64', '--seed', '18')
        self.assertNotEqual(one, two)

    def test_maximum_seed_is_representable(self):
        _, manifest, raw = self.generated('--bytes', '32', '--seed', str(2**64-1))
        self.assertEqual(manifest['seed'], 2**64-1)
        self.assertEqual(len(raw), 32)

    def test_maximum_size_is_exact(self):
        _, manifest, raw = self.generated('--bytes', str(16*1024*1024), '--pattern', 'zeroes')
        self.assertEqual(len(raw), 16*1024*1024)
        self.assertEqual(manifest['sha256'], hashlib.sha256(raw).hexdigest())

    def reject_without_creating_run(self, *args):
        before = sorted(self.parent.iterdir())
        r = self.run_helper(*args)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(sorted(self.parent.iterdir()), before)

    def test_unaligned_size_rejected(self):
        self.reject_without_creating_run('--bytes', '3', '--element-width', '4')

    def test_zero_and_negative_size_rejected(self):
        for size in ['0', '-4']:
            with self.subTest(size=size):
                self.reject_without_creating_run('--bytes', size)

    def test_oversized_data_rejected(self):
        self.reject_without_creating_run('--bytes', str(16*1024*1024+4))

    def test_invalid_width_rejected(self):
        self.reject_without_creating_run('--element-width', '3')

    def test_out_of_range_seed_rejected(self):
        for seed in ['-1', str(2**64)]:
            with self.subTest(seed=seed):
                self.reject_without_creating_run('--seed', seed)

    def test_missing_parent_rejected_without_creating_it(self):
        missing = self.parent / 'missing'
        r = subprocess.run([sys.executable, str(HELPER), '--parent', str(missing)],
                           capture_output=True, text=True, timeout=15)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(missing.exists())

    def test_file_parent_rejected_and_preserved(self):
        file = self.parent / 'not a directory'
        file.write_bytes(b'keep')
        r = subprocess.run([sys.executable, str(HELPER), '--parent', str(file)],
                           capture_output=True, text=True, timeout=15)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(file.read_bytes(), b'keep')


if __name__ == '__main__':
    unittest.main()
