import pathlib
import sys
import unittest

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from smoke_installer import observed_file_read


class SmokeEvidenceTests(unittest.TestCase):
    def test_completed_read_survives_a_later_compound_command_failure(self):
        body='{"providers": [{"name": "Example"}]}'
        item={'command':'cat /snapshot/data/preferred-providers.json; missing-python script.py','exit_code':127,'aggregated_output':body+'\nmissing-python: command not found'}
        self.assertTrue(observed_file_read([item],'data/preferred-providers.json',body))
        self.assertFalse(observed_file_read([{**item,'aggregated_output':'cat: file missing'}],'data/preferred-providers.json',body))
        self.assertFalse(observed_file_read([{'command':'rg --files data/preferred-providers.json','exit_code':0}],'data/preferred-providers.json',body))
        self.assertFalse(observed_file_read([item],'data/other.json',body))
