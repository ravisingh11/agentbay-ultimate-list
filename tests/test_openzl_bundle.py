import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import adapted_openzl

class OpenZLBundle(unittest.TestCase):
    def test_reviewed_archive_and_manifest_are_current(self):
        for path, raw in adapted_openzl.outputs().items():
            self.assertEqual((adapted_openzl.ROOT / path).read_bytes(), raw)
