"""Behavior checks use entirely synthetic logs in a disposable directory."""
import hashlib,json,os,pathlib,re,shutil,subprocess,tempfile,unittest
ROOT=pathlib.Path(os.environ.get('AGENTBAY_ADAPTATION_ROOT',str(pathlib.Path(__file__).resolve().parents[1])));LINK=ROOT/'skills/agentbay-fboss-link-log-analysis';QSFP=ROOT/'skills/agentbay-fboss-qsfp-log-analysis'
SCRIPTS=[LINK/'scripts/analyze_link_log.sh',LINK/'scripts/analyze_qsfp_service_log.sh',QSFP/'scripts/analyze_qsfp_log.sh']
LINK_FAIL='''[ RUN      ] cold_boot.AgentExample.linkUp
I1031 10:00:00.000000 1 AgentEnsemble.cpp:1] starting synthetic example
example.cpp:42: Failure
C++ exception with description "Transceivers:[6,10] don't have expected TransceiverStateMachineState" thrown in SetUp().
[  FAILED  ] cold_boot.AgentExample.linkUp (100 ms)
I1031 10:20:00.000000 1 AgentEnsemble.cpp:2] example teardown
'''
LINK_PASS='''[ RUN      ] AgentExample.init
I1031 10:00:00.000000 1 Agent.cpp:1] synthetic progress
[       OK ] AgentExample.init (1 ms)
[  PASSED  ] 1 test.
'''
QSFP_FAIL='''[ RUN      ] cold_boot.OpticsExample.program
I1031 10:00:00.000000 1 HwTest.cpp:1] synthetic test
example.cpp:42: Failure
Value of: programmed
  Actual: false
Expected: true
[  FAILED  ] cold_boot.OpticsExample.program (123 ms)
'''
QSFP_PASS='''[ RUN      ] cold_boot.OpticsExample.init
I1031 10:00:00.000000 1 HwTest.cpp:1] synthetic progress
[       OK ] cold_boot.OpticsExample.init (1 ms)
[  PASSED  ] 1 test.
'''
SERVICE='''I1031 10:00:00.000000 1 QsfpServer.cpp:1] QSFP Service PHY SDK Version: synthetic
W1031 10:14:00.000000 1 TransceiverStateMachine.h:2] [SM]Transceiver:6 programTransceiver failed: Unsupported Application
W1031 10:14:30.000000 1 TransceiverStateMachine.h:2] [SM]Transceiver:99 programTransceiver failed: Unsupported Application
I1031 10:20:00.000000 1 TransceiverStateMachine.h:3] [SM]Transceiver:6 State changed from DISCOVERED to INACTIVE
'''
class AdaptationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='agentbay-adaptation-test-');self.addCleanup(self.temp.cleanup);self.work=pathlib.Path(self.temp.name);self.traps=self.work/'deny-network';self.traps.mkdir();self.denied=self.work/'unexpected-external-command'
  for name in ['ssh','scp','curl','wget','git','sudo','systemctl','nc','sftp']:
   p=self.traps/name;p.write_text('#!/bin/sh\nprintf unexpected > "$ADAPTATION_DENIED"\nexit 99\n');p.chmod(0o755)
  self.env={**os.environ,'PATH':str(self.traps)+':/usr/bin:/bin','ADAPTATION_DENIED':str(self.denied)}
 def run_script(self,script,text=None,name='input.log',args=(),stdin=False,expected=0):
  if text is not None:
   log=self.work/name;log.write_text(text);before=log.read_bytes();source='-' if stdin else name
  else:log=None;source=name
  command=['/bin/bash',str(script),source,*args];r=subprocess.run(command,input=text if stdin else None,text=True,capture_output=True,cwd=self.work,env=self.env,timeout=10)
  self.assertEqual(r.returncode,expected,r.stdout+'\n'+r.stderr);self.assertFalse(self.denied.exists(),'Unexpected network/device command')
  if log:self.assertEqual(log.read_bytes(),before,'Parser modified its input')
  return r.stdout+r.stderr
 def test_01_link_assertion_and_qsfp_handoff(self):
  text=self.run_script(SCRIPTS[0],LINK_FAIL);self.assertIn('G2 transceiver-state gate',text);self.assertIn('phase: SetUp',text);self.assertIn('QSFP_SERVICE_LOG_NEEDED:  YES',text);self.assertIn('6,10',text)
 def test_02_link_pass_is_not_job_pass(self):
  text=self.run_script(SCRIPTS[0],LINK_PASS);self.assertIn('Passed markers observed',text);self.assertIn('do not establish complete binary or job success',text);self.assertNotIn('binary PASSED',text)
 def test_03_link_abort_without_failed_marker(self):
  log='I1031 10:00:00.000000 1 Agent.cpp:1] start\nF1031 10:00:01.000000 1 Agent.cpp:2] Check failed: synthetic\n*** Aborted at 1 ***\n';text=self.run_script(SCRIPTS[0],log);self.assertIn('Fatal CHECK',text);self.assertIn('synthetic',text)
 def test_04_link_truncated_scope(self):
  text=self.run_script(SCRIPTS[0],'I1031 10:00:00.000000 1 Agent.cpp:1] progress only\n');self.assertIn('none (killed/aborted before gtest summary, or truncated log)',text)
 def test_05_qsfp_assertion(self):
  text=self.run_script(SCRIPTS[2],QSFP_FAIL);self.assertIn('[gtest-assert] line 3',text);self.assertIn('cold_boot.OpticsExample.program',text);self.assertIn('Actual: false',text)
 def test_06_qsfp_known_bad_is_failure_context(self):
  text=self.run_script(SCRIPTS[2],QSFP_FAIL.replace('(123 ms)','(123 ms) [KNOWN BAD: synthetic-policy]'));self.assertIn('KNOWN BAD',text);self.assertIn('Failing gtest(s)',text)
 def test_07_qsfp_pass_does_not_infer_timeout(self):
  text=self.run_script(SCRIPTS[2],QSFP_PASS);self.assertIn('Passed test markers observed',text);self.assertNotIn('Likely a TIMEOUT/HANG',text)
 def test_08_qsfp_retry_is_not_terminal(self):
  text=self.run_script(SCRIPTS[2],'W1031 10:00:00.000000 1 Transceiver.cpp:1] programTransceiver failed: synthetic transient\n');self.assertIn('retry/context',text);self.assertIn('does not establish a terminal failure',text)
 def test_09_qsfp_incomplete_is_uncertain(self):
  text=self.run_script(SCRIPTS[2],'I1031 10:00:00.000000 1 HwTest.cpp:1] progress only\n');self.assertIn('outcome and cause remain unconfirmed',text);self.assertNotIn('Likely a TIMEOUT/HANG',text)
 def test_10_qsfp_failure_without_cause(self):
  text=self.run_script(SCRIPTS[2],'[  FAILED  ] cold_boot.Example.check (123 ms)\n');self.assertIn('cause is unconfirmed',text)
 def test_11_service_focus_and_matching_time(self):
  text=self.run_script(SCRIPTS[1],SERVICE,args=('--tcvr','6','--from','1031 10:00:00','--to','1031 10:20:00','--at','1031 10:15:00'));self.assertIn('focus x1 [6]',text);self.assertIn('other-tcvr x1',text);self.assertIn('final=INACTIVE',text)
 def test_12_service_wrong_log_rejected(self):
  text=self.run_script(SCRIPTS[1],SERVICE,args=('--at','1031 11:00:00'),expected=3);self.assertIn('WRONG LOG',text);self.assertNotIn('QSFP_SERVICE LOG ANALYSIS',text)
 def test_13_service_failure_outside_selected_window_rejected(self):
  text=self.run_script(SCRIPTS[1],SERVICE,args=('--from','1031 10:10:00','--to','1031 10:20:00','--at','1031 10:05:00'),expected=3);self.assertIn('unsuitable evidence',text)
 def test_14_service_empty_window_rejected(self):
  self.run_script(SCRIPTS[1],SERVICE,args=('--from','1031 12:00:00','--to','1031 12:10:00'),expected=3)
 def test_15_missing_files_rejected(self):
  for script in SCRIPTS:
   with self.subTest(script=script.name):self.run_script(script,name='not-present.log',expected=2)
 def test_16_directories_rejected(self):
  for script in SCRIPTS:
   with self.subTest(script=script.name):self.run_script(script,name='.',expected=2)
 def test_17_empty_files_rejected(self):
  for script in SCRIPTS:
   with self.subTest(script=script.name):self.run_script(script,'',expected=1)
 def test_18_unrecognized_files_rejected(self):
  for script in SCRIPTS:
   with self.subTest(script=script.name):self.run_script(script,'not a test or service log\n',expected=1)
 def test_19_stdin_support(self):
  for script,text in zip(SCRIPTS,[LINK_FAIL,SERVICE,QSFP_FAIL]):
   with self.subTest(script=script.name):self.run_script(script,text,stdin=True)
 def test_20_assignment_like_filenames(self):
  for script,text in zip(SCRIPTS,[LINK_FAIL,SERVICE,QSFP_FAIL]):
   with self.subTest(script=script.name):self.run_script(script,text,name='awk=value.log')
 def test_21_option_like_filenames(self):
  for script,text in zip(SCRIPTS,[LINK_FAIL,SERVICE,QSFP_FAIL]):
   with self.subTest(script=script.name):self.run_script(script,text,name='-f-log')
 def test_22_spaces_in_filename(self):
  for script,text in zip(SCRIPTS,[LINK_FAIL,SERVICE,QSFP_FAIL]):
   with self.subTest(script=script.name):self.run_script(script,text,name='two words.log')
 def test_23_log_text_never_executes(self):
  sentinel=self.work/'payload-executed';payload='W1031 10:00:00.000000 1 Example.cpp:1] $(touch '+str(sentinel)+'); `touch '+str(sentinel)+'`; curl https://example.invalid\n'
  for script,text in zip(SCRIPTS,[LINK_FAIL,SERVICE,QSFP_FAIL]):
   with self.subTest(script=script.name):self.run_script(script,payload+text);self.assertFalse(sentinel.exists())
 def test_24_service_missing_option_value(self):
  self.run_script(SCRIPTS[1],SERVICE,args=('--tcvr',),expected=2)
 def test_25_service_extra_argument_rejected(self):
  self.run_script(SCRIPTS[1],SERVICE,args=('unexpected',),expected=2)
 def test_26_script_syntax(self):
  for script in SCRIPTS:
   with self.subTest(script=script.name):subprocess.run(['/bin/bash','-n',str(script)],check=True,capture_output=True)
 def test_27_standalone_packages(self):
  for root in [LINK,QSFP]:
   with self.subTest(package=root.name):
    isolated=self.work/root.name;shutil.copytree(root,isolated);script=next((isolated/'scripts').glob('*.sh'));log=SERVICE if script.name=='analyze_qsfp_service_log.sh' else (LINK_FAIL if root==LINK else QSFP_FAIL);self.run_script(script,log)
 def test_28_local_markdown_links_resolve_within_package(self):
  for root in [LINK,QSFP]:
   for file in root.rglob('*.md'):
    for target in re.findall(r'\]\(([^)]+)\)',file.read_text()):
     if '://' in target or target.startswith('#'):continue
     resolved=(file.parent/target.split('#')[0]).resolve();self.assertTrue(resolved.is_relative_to(root.resolve()),str(file)+' escapes package');self.assertTrue(resolved.exists(),str(file)+' missing '+target)
 def test_29_provenance_output_hashes_match(self):
  for root in [LINK,QSFP]:
   for record in json.loads((root/'provenance.json').read_text())['inputs']:
    self.assertEqual(hashlib.sha256((root/record['destination']).read_bytes()).hexdigest(),record['adapted_sha256'])
 def test_30_service_invalid_focus_rejected(self):
  for value in ['nonsense','6,abc','-1','6,,10']:
   with self.subTest(value=value):self.run_script(SCRIPTS[1],SERVICE,args=('--tcvr',value),expected=2)
 def test_31_service_malformed_times_rejected(self):
  for value in ['yesterday','1031 99:00:00','1031 10:90:00','1312 10:00:00']:
   with self.subTest(value=value):self.run_script(SCRIPTS[1],SERVICE,args=('--at',value),expected=2)
 def test_32_service_inverted_window_rejected(self):
  self.run_script(SCRIPTS[1],SERVICE,args=('--from','1031 10:20:00','--to','1031 10:00:00'),expected=2)
 def test_33_passed_test_then_later_crash_is_not_binary_success(self):
  log=LINK_PASS+'[ RUN      ] AgentExample.second\nF1031 10:01:00.000000 1 Agent.cpp:2] Check failed: synthetic later failure\n*** Aborted at 1 ***\n'
  text=self.run_script(SCRIPTS[0],log);self.assertIn('Failure/crash evidence is also present',text);self.assertNotIn('binary PASSED',text);self.assertIn('Fatal CHECK',text)
 def test_34_missing_transceiver_gate_requests_supplied_service_log(self):
  log=LINK_FAIL.replace("Transceivers:[6,10] don't have expected TransceiverStateMachineState",'TransceiverInfo was never populated.')
  text=self.run_script(SCRIPTS[0],log);self.assertIn('qsfp_service returned no present transceiver',text);self.assertIn('QSFP_SERVICE_LOG_NEEDED:  YES',text)
 def external_abort_log(self,done):
  return '[ RUN      ] AgentExample.test\nI1031 10:00:00.000000 1 Example.cpp:1] Checking link status on eth1/1\n'+('I1031 10:01:00.000000 1 Example.cpp:2] Multi Switch Link Test setup ready\n' if done else '')+'I1031 10:02:00.000000 1 Example.cpp:3] activity\n*** Aborted at 1 ***\n*** Signal 6 (SIGABRT) received by PID 123 (pthread TID 123) (maybe from PID 456, sent by kill()) ***\n'
 def test_35_completed_setup_not_blamed_for_body_abort(self):
  text=self.run_script(SCRIPTS[0],self.external_abort_log(True));self.assertIn('SetUp completion was observed before this abort',text);self.assertNotIn('SetUp was still polling',text);self.assertNotIn('A wait was observed without a later SetUp completion',text)
 def test_36_fatal_retry_wording_keeps_terminal_evidence(self):
  text=self.run_script(SCRIPTS[2],'F1031 10:00:00.000000 1 Example.cpp:1] Check failed: programTransceiver failed: synthetic\n');self.assertIn('[CHECK/FATAL]',text);self.assertNotIn('[retry/context — WARN, not the verdict] line',text)
 def test_37_warning_vendor_reason_stays_retry_context(self):
  text=self.run_script(SCRIPTS[2],'W1031 10:00:00.000000 1 Example.cpp:1] programTransceiver failed: BcmError synthetic\n');self.assertIn('[retry/context',text);self.assertIn('does not establish a terminal failure',text);self.assertNotIn('[exception]',text)
 def test_38_unfinished_gate_remains_hypothesis(self):
  text=self.run_script(SCRIPTS[0],self.external_abort_log(False));self.assertIn('A wait was observed without a later SetUp completion',text);self.assertIn('neither link convergence nor the underlying cause is confirmed',text);self.assertNotIn('Root cause =',text)
 def test_39_retry_plus_failed_marker_preserves_failed_result(self):
  log='[ RUN      ] Example.test\nW1031 10:00:00.000000 1 Example.cpp:1] programTransceiver failed: retry reason\n[  FAILED  ] Example.test (100 ms)\n'
  text=self.run_script(SCRIPTS[2],log);self.assertIn('A failed-test marker was observed',text);self.assertNotIn('does not establish a terminal failure',text)
if __name__=='__main__':unittest.main(verbosity=2)
