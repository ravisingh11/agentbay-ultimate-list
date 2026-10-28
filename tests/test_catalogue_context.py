import json
import pathlib
import sys
import tempfile
import unittest
import urllib.error

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
import catalogue_context as context

REV='a'*40
def fixture():
    row={key:'' for key in context.catalog.FIELDS}
    row.update(id='skill-one',name='Example skill',description='Example metadata',type='Skill',repository_url='https://github.com/example/skills',categories=['Software development'],tags=[],use_cases=[],repository_archived=False,recommended=False,repository_status_checked_at=None,github_stars=None,github_stars_checked_at=None)
    payloads={'skills/catalog.json':json.dumps([row]).encode(),'data/preferred-providers.json':json.dumps({'providers':[{'name':'Example','github_owners':['example'],'homepage_url':'https://example.com'}]}).encode()}
    payloads['sync-manifest.json']=json.dumps({'files':{'skills/catalog.json':{'sha256':context.digest(payloads['skills/catalog.json']),'bytes':len(payloads['skills/catalog.json'])}},'inputs':{'data/preferred-providers.json':{'sha256':context.digest(payloads['data/preferred-providers.json'])}}}).encode()
    return payloads

class ContextTests(unittest.TestCase):
    def test_public_mode_pins_once_and_never_uses_credentials(self):
        payloads=fixture();calls=[]
        def http(url):
            calls.append(url)
            if url.endswith('/commits/main'):return json.dumps({'sha':REV}).encode()
            prefix='https://raw.githubusercontent.com/'+context.REPOSITORY+'/'+REV+'/'
            self.assertTrue(url.startswith(prefix));return payloads[url.removeprefix(prefix)]
        def forbidden(*args,**kwargs):raise AssertionError('Public mode invoked GitHub CLI')
        raw,source=context.load('public',http=http,github=forbidden)
        self.assertEqual(raw,payloads);self.assertEqual(source['source_revision'],REV);self.assertEqual(source['access_mode'],'public_https');self.assertEqual(len(calls),4)
        with tempfile.TemporaryDirectory() as d:
            output=pathlib.Path(d).resolve()/'snapshot';context.save(output,raw,source)
            self.assertEqual((output/'skills/catalog.json').read_bytes(),payloads['skills/catalog.json'])
            with self.assertRaises(ValueError):context.save(output,raw,source)
            self.assertEqual((output/'source.json').read_text(),json.dumps(source,indent=2)+'\n')

    def test_private_fallback_is_explicit_and_public_mode_never_falls_back(self):
        payloads=fixture();calls=[]
        def unavailable(url):raise urllib.error.HTTPError(url,404,'Not Found',{},None)
        def github(endpoint,raw=False):
            calls.append(endpoint)
            if endpoint.endswith('/commits/main'):return json.dumps({'sha':REV}).encode()
            self.assertTrue(raw);name=endpoint.split('/contents/',1)[1].split('?')[0];self.assertTrue(endpoint.endswith('?ref='+REV));return payloads[name]
        _,source=context.load('auto',http=unavailable,github=github);self.assertEqual(source['access_mode'],'authenticated_github_cli');self.assertEqual(len(calls),4)
        calls.clear()
        with self.assertRaises(ValueError):context.load('public',http=unavailable,github=github)
        self.assertFalse(calls)

    def test_pinned_public_mode_skips_api_and_tampering_does_not_trigger_authenticated_fallback(self):
        payloads=fixture();calls=[]
        def http(url):calls.append(url);return payloads[url.split('/'+REV+'/',1)[1]]
        def forbidden(*args,**kwargs):raise AssertionError('Invalid metadata triggered authentication')
        context.load('public',REV,http=http,github=forbidden);self.assertEqual(len(calls),3);self.assertTrue(all('api.github.com' not in x for x in calls))
        payloads['skills/catalog.json']+=b' '
        with self.assertRaisesRegex(ValueError,'checksum mismatch'):context.load('auto',REV,http=http,github=forbidden)

    def test_invalid_revision_and_symlink_output_are_rejected(self):
        with self.assertRaises(ValueError):context.load('public','main',http=lambda u:None)
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);(root/'outside').mkdir();(root/'link').symlink_to(root/'outside',target_is_directory=True)
            with self.assertRaises(ValueError):context.save(root/'link'/'snapshot',fixture(),{})
            self.assertEqual(list((root/'outside').iterdir()),[])
