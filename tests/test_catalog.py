"""Regressions for additive maintenance and export ownership; no network or skills execute."""
import csv
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1]/'scripts/catalog.py'
spec = importlib.util.spec_from_file_location('catalog', SCRIPT)
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)


def row(rid='one', **changes):
    value = {field: '' for field in catalog.FIELDS}
    value.update(id=rid, name='Example', type='Skill',
                 website_url='https://github.com/example/project/blob/main/skills/example/SKILL.md',
                 repository_url='https://github.com/example/project', categories=['Software development'],
                 tags=[], use_cases=[], repository_archived=False,
                 repository_status_checked_at=None, github_stars=None, github_stars_checked_at=None,
                 recommended=False, listing_scope='direct_list')
    value.update(changes)
    return catalog.summarize_catalog([value])[0][0]


def curation(**changes):
    return {'schema_version':1,'additions':[],'corrections':[],'exclusions':[],**changes}


def evidence():
    return [{'url':'https://github.com/example/project','checked_at':'2026-01-01',
             'note':'Verified the public component source and category.'}]


class MaintenanceTests(unittest.TestCase):
    def test_import_augments_and_retains_absent_records(self):
        baseline = [row(),row('local',name='Local',repository_url='https://github.com/example/local')]
        incoming = [row(name='Updated'),row('new',name='New')]
        actual, delta = catalog.augment(baseline,incoming,{})
        self.assertEqual({r['id'] for r in actual},{'one','local','new'})
        self.assertEqual(next(r for r in actual if r['id']=='one')['name'],'Updated')
        self.assertEqual(delta['retained_absent_ids'],1)
        self.assertEqual(delta['removed_automatically'],0)

    def test_correction_survives_later_upstream_update(self):
        source = curation(corrections=[{'id':'one','fields':{'categories':['Browser automation']},'evidence':evidence()}])
        curated = catalog.apply_curation([row()],source)
        imported, _ = catalog.augment(curated,[row(categories=['Research and search'])],{})
        self.assertEqual(catalog.apply_curation(imported,source)[0]['categories'],['Browser automation'])

    def test_local_addition_is_idempotent_and_does_not_invent_statistics(self):
        rid = 'community:12345678-1234-1234-1234-123456789abc'
        fields = {key:row()[key] for key in ('name','type','website_url','repository_url','categories','tags')}
        source = curation(additions=[{'id':rid,'fields':fields,'evidence':evidence()}])
        actual = catalog.apply_curation([],source)
        self.assertIsNone(actual[0]['github_stars'])
        self.assertEqual(actual[0]['agentbay_url'],'')
        self.assertEqual(catalog.apply_curation(actual,source),actual)

    def test_local_addition_adopted_upstream_keeps_source_link_and_stable_id(self):
        rid = 'community:12345678-1234-1234-1234-123456789abc'
        fields = {key:row()[key] for key in ('name','type','website_url','repository_url','categories','tags')}
        source = curation(additions=[{'id':rid,'fields':fields,'evidence':evidence()}])
        baseline = catalog.apply_curation([],source)
        imported = row('site-id',agentbay_url='https://agentbay.io/?project=site-id#catalog',github_stars=10,
                       github_stars_checked_at='2026-01-01T00:00:00Z')
        rows, aliases = catalog.normalize(baseline+[imported],preferred_ids={rid})
        self.assertEqual(aliases,{'site-id':rid})
        self.assertEqual(rows[0]['agentbay_url'],imported['agentbay_url'])
        rows = catalog.apply_curation(rows,source)
        self.assertEqual(rows[0]['agentbay_url'],imported['agentbay_url'])
        updated, _ = catalog.augment(rows,[imported],aliases)
        curated = catalog.apply_curation(updated,source)
        self.assertEqual(curated[0]['id'],rid)
        self.assertEqual(curated[0]['github_stars'],10)

    def test_generated_fields_cannot_be_overridden(self):
        for field in ('description','recommended','id','preferred_provider'):
            with self.subTest(field=field),self.assertRaises(ValueError):
                catalog.apply_curation([row()],curation(corrections=[{'id':'one','fields':{field:'invented'},'evidence':evidence()}]))

    def test_unknown_correction_and_unverified_addition_fail(self):
        with self.assertRaises(ValueError):
            catalog.apply_curation([row()],curation(corrections=[{'id':'missing','fields':{'name':'Changed'},'evidence':evidence()}]))
        with self.assertRaises(ValueError):
            catalog.apply_curation([],curation(additions=[{'id':'community:invalid','fields':{'name':'No evidence'},'evidence':[]}]))

    def test_duplicate_components_merge_metadata_and_keep_id_mapping(self):
        rows, aliases = catalog.normalize([row('a',tags=['Python']),row('b',categories=['Research and search'])])
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['tags'],['Python'])
        self.assertEqual(rows[0]['categories'],['Software development','Research and search'])
        self.assertEqual(aliases,{'b':'a'})

    def test_distinct_component_paths_are_not_duplicates(self):
        other = row('b',website_url='https://github.com/example/project/blob/main/skills/other/SKILL.md')
        self.assertEqual(len(catalog.normalize([row(),other])[0]),2)

    def test_distinct_documentation_anchors_are_not_duplicates(self):
        one = row('a',website_url='https://example.com/skills#one')
        two = row('b',website_url='https://example.com/skills#two')
        self.assertEqual(len(catalog.normalize([one,two])[0]),2)

    def test_existing_retained_id_wins_over_new_duplicate(self):
        rows, aliases = catalog.normalize([row('existing'),row('aaa')],preferred_ids={'existing'})
        self.assertEqual(rows[0]['id'],'existing')
        self.assertEqual(aliases,{'aaa':'existing'})

    def test_upstream_duplicate_never_resurrects_old_id(self):
        existing = [row('retained')]
        incoming = [row('old',tags=['New tag']),row('retained')]
        actual, _ = catalog.augment(existing,incoming,{'old':'retained'})
        self.assertEqual([r['id'] for r in actual],['retained'])
        self.assertEqual(actual[0]['tags'],['New tag'])

    def test_exclusion_is_explicit_and_survives_import(self):
        source = curation(exclusions=[{'id':'one','reason':'Confirmed source is no longer public.','evidence':evidence()}])
        self.assertEqual(catalog.apply_curation([row()],source),[])

    def test_ownership_attribution_uses_registry_not_name(self):
        actual, _ = catalog.normalize([row(repository_url='https://github.com/microsoft/example')])
        self.assertEqual(actual[0]['preferred_provider'],'Microsoft')
        self.assertFalse(actual[0]['recommended'])
        text = catalog.listing_line(actual[0])
        self.assertIn('Microsoft · Official source',text)
        self.assertNotIn('Recommended',text)
        fork, _ = catalog.normalize([row(name='Microsoft example')])
        self.assertEqual(fork[0]['preferred_provider'],'')

    def test_original_summaries_do_not_copy_publisher_prose(self):
        value = row();value['description']='UNTRUSTED PUBLISHER TEXT';value['use_cases']=['Arbitrary copied claim']
        safe, _ = catalog.summarize_catalog([value])
        self.assertNotIn('UNTRUSTED',safe[0]['description'])
        self.assertNotIn('Arbitrary',str(safe[0]['use_cases']))

    def test_schema_rejects_unknown_fields_and_credential_urls(self):
        unknown = {**row(),'private_note':'Not public'}
        with self.assertRaises(ValueError):catalog.validate_rows([unknown])
        with self.assertRaises(ValueError):catalog.validate_rows([row(website_url='https://token:secret@example.com/')])
        with self.assertRaises(ValueError):catalog.validate_rows([row(),row()])

    def test_subset_csv_retains_complete_records_including_arrays(self):
        rows = [row(name='A comma, and "quote"'),row('project',type='Framework')]
        outputs, metadata = catalog.split_exports(rows)
        self.assertEqual(json.loads(outputs['skills/catalog.json']),[rows[0]])
        self.assertEqual(json.loads(outputs['projects/catalog.json']),[rows[1]])
        cells = list(csv.DictReader(io.StringIO(outputs['skills/catalog.csv'].decode())))[0]
        self.assertEqual(cells['name'],rows[0]['name'])
        self.assertEqual(json.loads(cells['categories']),rows[0]['categories'])
        self.assertEqual(metadata['skills']['entry_count'],1)

    def test_empty_subsets_have_valid_downloads_and_navigation(self):
        outputs, metadata = catalog.split_exports([])
        self.assertEqual(json.loads(outputs['skills/catalog.json']),[])
        self.assertEqual(metadata['projects']['entry_count'],0)
        browse = catalog.render_browse([],{})
        self.assertIn('skills/README.md',browse)
        self.assertIn('projects/README.md',browse)

    def test_write_refuses_symlink_before_changing_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            external = root/'outside';external.mkdir()
            (root/'skills').symlink_to(external,target_is_directory=True)
            with self.assertRaises(ValueError):
                catalog.write_outputs({'README.md':b'new','skills/README.md':b'new'},{},root)
            self.assertFalse((root/'README.md').exists())

    def test_write_preserves_unowned_generated_name(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory);(root/'skills').mkdir()
            target = root/'skills/README.md';target.write_text('human authored')
            with self.assertRaises(ValueError):catalog.write_outputs({'skills/README.md':b'new'},{},root)
            self.assertEqual(target.read_text(),'human authored')

    def test_temporary_conflict_stops_before_any_output_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory);(root/'.catalog.json.tmp').write_text('preserve')
            with self.assertRaises(ValueError):
                catalog.write_outputs({'README.md':b'new','catalog.json':b'[]'},{},root)
            self.assertFalse((root/'README.md').exists())

    def test_obsolete_manual_page_is_not_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory);(root/'skills').mkdir()
            target = root/'skills/old.md';target.write_text('human authored')
            with self.assertRaises(ValueError):
                catalog.write_outputs({}, {'generated_markdown_files':['skills/old.md'],'files':{'skills/old.md':{}}},root)
            self.assertTrue(target.exists())

    def test_modified_owned_page_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            target = root/'README.md';target.write_text('local edits')
            previous = {'files':{'README.md':{'sha256':catalog.sha(b'original')}}}
            with self.assertRaises(ValueError):
                catalog.write_outputs({'README.md':b'regenerated'},previous,root)
            self.assertEqual(target.read_text(),'local edits')

    def test_empty_upstream_cannot_replace_catalogue(self):
        with self.assertRaises(ValueError):
            catalog.build({'catalog.json':[]})

    def test_regeneration_produces_identical_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory);(root/'data').mkdir()
            (root/catalog.CURATION).write_bytes(catalog.json_bytes(curation()))
            (root/catalog.POLICY).write_bytes(catalog.json_bytes(catalog.PREFERRED_PROVIDERS))
            rows, aliases = catalog.normalize([row()])
            first, manifest = catalog.build_outputs(rows,aliases,{},root)
            second, _ = catalog.build_outputs(rows,aliases,manifest,root)
            self.assertEqual(first,second)


if __name__ == '__main__':
    unittest.main()
