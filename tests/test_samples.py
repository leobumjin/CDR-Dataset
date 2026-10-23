import json
import shutil
import tempfile
import unittest
from pathlib import Path

from src.catalog.files import FORMAT, FileCatalog
from src.catalog.io import load, write
from src.catalog.sample_sources import SourceRun, checksums, write_run
from src.catalog.releases import assemble, read_releases, read_snapshot
from src.catalog.web_assets import export_catalog, export_release_samples
from src.labels.prepare_samples import generate as random_samples
from src.labels.prepare_labels import prepare, parse_output, prompt

ROOT = Path(__file__).resolve().parents[1]


class SampleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT / 'catalog', self.root / 'catalog')
        self.catalog = FileCatalog(self.root)
        self.sample = {'bird': {'sample_1': {'bird_f_001': 2.7, 'bird_f_002': True}}}
        self.metadata = {'status': 'complete', 'provenance': {'method': 'constructed'}}

    def source(self, sid='samples', samples=None, **meta):
        return write_run(self.root, sid, {**self.metadata, **meta}, self.sample if samples is None else samples)

    def test_release_assembly_preserves_version_scripts(self):
        self.source()
        directory = self.root / 'releases/v1'
        (directory / 'scripts').mkdir(parents=True)
        code = directory / 'scripts/prepare_samples.py'
        code.write_text('# versioned generator\n')
        assemble(self.root, 'v1', 'samples', catalog_commit='test-commit')
        self.assertEqual(code.read_text(), '# versioned generator\n')
        self.assertIn('v1', read_releases(self.root))
        with self.assertRaisesRegex(ValueError, 'already exists'):
            assemble(self.root, 'v1', 'samples', catalog_commit='test-commit')

    def test_catalog_versions_are_explicit_and_frozen(self):
        shutil.copytree(self.root / 'catalog/v1', self.root / 'catalog/v2')
        path = self.root / 'catalog/v2/classes/bird.yaml'
        doc = load(path)
        doc['features']['bird_f_001']['description'] = 'Version two definition'
        write(path, doc)
        self.assertNotEqual(FileCatalog(self.root).features['bird', 'bird_f_001']['description'],
                            FileCatalog(self.root, catalog_version='v2').features['bird', 'bird_f_001']['description'])
        random_samples(self.root, source_id='version2', classes=['bird'], count=2, catalog_version='v2')
        source = SourceRun(self.root, 'version2')
        self.assertEqual(source.meta['catalog_version'], 'v2')
        self.assertTrue((source.directory / 'catalog/classes/bird.yaml').is_file())
        self.assertFalse((source.directory / 'catalog/v1').exists())
        with self.assertRaisesRegex(ValueError, 'does not match'):
            prepare(self.root, 'version2', catalog_version='v1')
        shutil.rmtree(self.root / 'catalog/v2')
        _, jobs = prepare(self.root, 'version2', catalog_version='v2')
        self.assertTrue(jobs)
        with self.assertRaisesRegex(ValueError, 'not found'):
            FileCatalog(self.root, catalog_version='v2')

    def test_definitions_require_no_instance_list_or_source_data(self):
        self.assertEqual(self.catalog.stats(), {'classes': 10, 'features': 70, 'tasks': 4, 'contexts': 25})
        self.assertFalse(list((self.root / 'catalog').rglob('list.yaml')))
        self.assertFalse(hasattr(self.catalog, 'instances'))

    def test_catalog_rejects_old_name_grounding(self):
        p = self.root / 'catalog/v1/classes/bird.yaml'
        write(p, {**load(p), 'grounding': 'R'})
        with self.assertRaisesRegex(ValueError, 'not named objects'):
            FileCatalog(self.root)

    def test_features_remain_semantic_not_value_schemas(self):
        p = self.root / 'catalog/v1/classes/bird.yaml'
        doc = load(p)
        doc['features']['bird_f_001']['values'] = [0, 1]
        write(p, doc)
        with self.assertRaisesRegex(ValueError, 'source metadata'):
            FileCatalog(self.root)

    def test_duplicate_feature_names_fail(self):
        p = self.root / 'catalog/v1/classes/bird.yaml'
        doc = load(p)
        doc['features']['bird_f_002']['name'] = doc['features']['bird_f_001']['name']
        write(p, doc)
        with self.assertRaisesRegex(ValueError, 'Duplicate feature names'):
            FileCatalog(self.root)

    def test_unbound_contexts_fail(self):
        p = self.root / 'catalog/v1/tasks/fly.yaml'
        doc = load(p)
        doc['contexts']['extra'] = {'description': 'Extra'}
        # fly has a single binding and deliberately applies all its contexts.
        write(p, doc)
        p = self.root / 'catalog/v1/tasks/fly.yaml'
        task = load(p)
        task['bindings'][0]['contexts'] = ['dry_20m']
        write(p, task)
        with self.assertRaisesRegex(ValueError, 'Unbound'):
            FileCatalog(self.root)

    def test_json_values_have_no_assumed_numeric_scale(self):
        for value in (0, 0.2, 17, True, 'present', {'mass': 2.7}, ['a', 'b']):
            self.catalog.validate_samples('bird', {'sample_1': {'bird_f_001': value}})

    def test_missing_nonfinite_unknown_and_named_fields_fail(self):
        for features in ({}, {'bird_f_001': None}, {'bird_f_001': float('nan')},
                         {'unknown': 0}, {'name': 'Sparrow'}):
            with self.subTest(features=features), self.assertRaises(ValueError):
                self.catalog.validate_samples('bird', {'sample_1': features})

    def test_source_is_immutable(self):
        self.source()
        before = checksums(self.root / 'labels/generated/samples')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.source()
        self.assertEqual(before, checksums(self.root / 'labels/generated/samples'))

    def test_invalid_source_leaves_no_output(self):
        with self.assertRaises(ValueError):
            self.source(samples={'bird': {'a': {'missing': 1}}})
        self.assertFalse((self.root / 'labels/generated/samples').exists())

    def test_encoding_is_local_and_type_sensitive(self):
        with self.assertRaisesRegex(ValueError, 'outside source encoding'):
            self.source(feature_encoding={'values': [0, 0.5, 1]})
        self.source(feature_encoding={'values': [2.7, True]})
        self.assertEqual(SourceRun(self.root, 'samples').samples, self.sample)

    def test_legacy_sources_are_not_reinterpreted(self):
        write(self.root / 'labels/generated/old/sources.json', {'id': 'old', 'provider': 'random'})
        FileCatalog(self.root)
        with self.assertRaisesRegex(ValueError, 'explicit migration'):
            SourceRun(self.root, 'old')

    def test_sample_ids_are_source_scoped_but_unambiguous(self):
        self.source('first')
        self.source('second', {'bird': {'sample_1': {'bird_f_001': 99}}})
        self.assertNotEqual(SourceRun(self.root, 'first').samples, SourceRun(self.root, 'second').samples)
        with self.assertRaisesRegex(ValueError, 'unique'):
            self.source('duplicate', {'bird': {'same': {'bird_f_001': 1}}, 'plant': {'same': {'plant_f_001': 1}}})

    def test_explicit_sample_reference_and_hashes(self):
        parent = self.source()
        meta = {**self.metadata, 'sample_source': 'samples', 'sample_source_sha256': checksums(parent.directory),
                'label_provenance': {'method': 'ai_generated', 'review_status': 'unverified'}}
        run = write_run(self.root, 'labels', meta, {}, {'fly': {'sample_1': {'dry_20m': {'yes': 1, 'no': 0, 'unknown': 0}}}})
        self.assertEqual(run.samples, self.sample)
        write(parent.directory / 'samples/bird.json', {'sample_1': {'bird_f_001': 42}})
        with self.assertRaisesRegex(ValueError, 'checksum'):
            SourceRun(self.root, 'labels')

    def test_task_labels_must_reference_bound_samples_and_contexts(self):
        for tid, labels in [('fly', {'missing': {'dry_20m': {'yes': 1, 'no': 0, 'unknown': 0}}}),
                            ('fly', {'sample_1': {'unknown': {'yes': 1, 'no': 0, 'unknown': 0}}}),
                            ('fly', {'sample_1': {'dry_20m': None}}),
                            ('guilt', {'sample_1': {'ordinary_situation': {'yes': 1, 'no': 0, 'unknown': 0}}})]:
            with self.subTest(tid=tid, labels=labels), self.assertRaises(ValueError):
                self.catalog.validate_task_labels(tid, labels, self.sample)

    def test_random_samples_reproducible_and_labels_optional(self):
        random_samples(self.root, source_id='first', classes=['bird'], count=3, seed=5)
        random_samples(self.root, source_id='second', classes=['bird'], count=3, seed=5)
        a, b = SourceRun(self.root, 'first'), SourceRun(self.root, 'second')
        self.assertEqual(a.samples, b.samples)
        self.assertFalse(a.tasks)
        self.assertEqual(b.stats()['task_labels'], 0)
        self.assertNotIn('name', json.dumps(a.samples))

    def test_sampler_uses_feature_opinion_objects(self):
        from src.catalog.opinions import validate_feature_opinion
        random_samples(self.root, source_id='opinions', classes=['bird'], count=5)
        run = SourceRun(self.root, 'opinions')
        self.assertEqual(run.feature_encoding['sampling'], 'balanced_regions')
        for features in run.samples['bird'].values():
            for value in features.values():
                validate_feature_opinion(value)
                self.assertTrue(all(mass == round(mass, 2) for mass in value.values()))
        fixed = {'belief': 0.7, 'disbelief': 0.2, 'uncertain': 0.1}
        random_samples(self.root, source_id='fixed', classes=['bird'], count=2, feature_values=[fixed])
        self.assertTrue(all(v == fixed for row in SourceRun(self.root, 'fixed').samples['bird'].values() for v in row.values()))
        for bad in [0.5, {'belief': 1, 'disbelief': 1, 'uncertain': 0},
                    {'belief': True, 'disbelief': 0, 'uncertain': 0},
                    {'belief': 0, 'disbelief': 0},
                    {'belief': float('nan'), 'disbelief': 0, 'uncertain': 1}]:
            with self.subTest(value=bad), self.assertRaises(ValueError):
                random_samples(self.root, source_id='invalid', feature_values=[bad])
        self.assertFalse((self.root / 'labels/generated/invalid').exists())

    def test_feature_rounding_preserves_total_for_rounding_up_and_down(self):
        from releases.v1.scripts.prepare_samples import round_opinion
        from src.catalog.opinions import validate_feature_opinion
        for value in (
            {'belief': 0.03991316534681377, 'disbelief': 0.10418248548143272,
             'uncertain': 0.8559043491717535},
            {'belief': 1 / 3, 'disbelief': 1 / 3, 'uncertain': 1 / 3},
            {'belief': 0.336, 'disbelief': 0.336, 'uncertain': 0.328},
        ):
            rounded = round_opinion(value)
            validate_feature_opinion(rounded)
            self.assertTrue(all(mass == round(mass, 2) for mass in rounded.values()))
        random_samples(self.root, source_id='rounded_fixed', classes=['bird'], count=1,
                       feature_values=[value])
        run = SourceRun(self.root, 'rounded_fixed')
        self.assertEqual(run.feature_encoding['decimal_places'], 2)
        self.assertTrue(all(v == rounded for row in run.samples['bird'].values() for v in row.values()))

    def test_confidence_regions_have_equal_probability_and_recorded_constraints(self):
        from releases.v1.scripts.prepare_samples import FEATURE_REGIONS, in_region
        random_samples(self.root, source_id='regions', classes=['bird'], count=1000, seed=13)
        run = SourceRun(self.root, 'regions')
        counts = dict.fromkeys(FEATURE_REGIONS, 0)
        for features in run.samples['bird'].values():
            for value in features.values():
                regions = [key for key in FEATURE_REGIONS if in_region(value, key)]
                self.assertEqual(len(regions), 1)
                counts[regions[0]] += 1
        config = run.meta['sampling_config']
        self.assertEqual(config['region_counts'], counts)
        self.assertEqual(config['regions'], FEATURE_REGIONS)
        self.assertEqual(config['region_probabilities'], dict.fromkeys(FEATURE_REGIONS, 0.25))
        total = sum(counts.values())
        for count in counts.values():
            self.assertLess(abs(count / total - 0.25), 0.025)

    def test_uniform_simplex_baseline_is_still_available(self):
        from releases.v1.scripts.prepare_samples import FEATURE_REGIONS, in_region
        random_samples(self.root, source_id='baseline', classes=['bird'], count=100,
                       sampling='uniform_simplex')
        run = SourceRun(self.root, 'baseline')
        self.assertEqual(run.feature_encoding['sampling'], 'uniform_simplex')
        self.assertNotIn('region_probabilities', run.meta['sampling_config'])
        self.assertTrue(any(not any(in_region(v, key) for key in FEATURE_REGIONS)
                            for row in run.samples['bird'].values() for v in row.values()))

    def test_total_count_default_remainders_and_small_runs(self):
        random_samples(self.root, source_id='default')
        run = SourceRun(self.root, 'default')
        self.assertEqual(run.stats()['samples'], 5000)
        self.assertEqual({len(rows) for rows in run.samples.values()}, {500})
        for count in (3, 13):
            source = f'total_{count}'
            random_samples(self.root, source_id=source, count=count)
            result = SourceRun(self.root, source)
            counts = result.meta['selection']['class_counts']
            self.assertEqual(result.stats()['samples'], count)
            self.assertEqual(sum(counts.values()), count)
            self.assertLessEqual(max(counts.values()) - min(counts.values()), 1)
            random_samples(self.root, source_id=source + '_repeat', count=count)
            self.assertEqual(result.samples, SourceRun(self.root, source + '_repeat').samples)

    def test_sampler_covers_all_defined_features(self):
        random_samples(self.root, source_id='samples_all', count=10, seed=7)
        run = SourceRun(self.root, 'samples_all')
        self.assertEqual(run.stats()['samples'], 10)
        self.assertEqual(run.stats()['feature_values'], 70)
        self.assertFalse(run.tasks)
        self.assertNotIn('label_provenance', run.meta)

    def test_inference_never_receives_object_identity_or_provenance(self):
        self.source(provenance={'method': 'imported', 'original_name': 'Secret sparrow'})
        meta, jobs = prepare(self.root, 'samples', tasks=['fly'], contexts=['dry_20m'])
        self.assertEqual(len(jobs), 1)
        payload = jobs[0]['input']
        self.assertEqual(payload['features'], self.sample['bird']['sample_1'])
        self.assertNotIn('name', payload)
        self.assertNotIn('sample_id', payload)
        self.assertNotIn('Secret sparrow', prompt(jobs[0]))
        self.assertNotIn('sample_1', prompt(jobs[0]))
        self.assertEqual(meta['sample_source'], 'samples')

    def test_inference_uses_frozen_source_definitions(self):
        self.source()
        before = prepare(self.root, 'samples', tasks=['fly'])[1][0]['input']['feature_definitions']
        p = self.root / 'catalog/v1/classes/bird.yaml'
        doc = load(p)
        doc['features']['bird_f_001']['description'] = 'A later meaning'
        write(p, doc)
        after = prepare(self.root, 'samples', tasks=['fly'])[1][0]['input']['feature_definitions']
        self.assertEqual(before, after)

    def test_verified_label_claim_requires_evidence(self):
        with self.assertRaisesRegex(ValueError, 'evidence references'):
            write_run(self.root, 'invalid_verified', {**self.metadata,
                'label_provenance': {'method': 'human', 'review_status': 'verified'}},
                self.sample, {'fly': {'sample_1': {'dry_20m': {'yes': 1, 'no': 0, 'unknown': 0}}}})

    def test_opinion_response_and_unknown_mass(self):
        raw = '{"a":{"uncertainty_percent":100,"belief_ratio":0,"disbelief_ratio":0}}'
        self.assertEqual(parse_output('```json\n' + raw + '\n```', ['a']),
                         {'a': {'yes': 0, 'no': 0, 'unknown': 1}})
        invalid = ['{"a":{"value":{"yes":1,"yes":0,"no":0,"unknown":1},"reason":"basis"}}', '{}', '{"a":{"value":true,"reason":"basis"}}',
                   '{"a":{"value":null,"reason":"no evidence"}}',
                   '{"a":{"value":{"yes":0.6,"no":0.6,"unknown":0},"reason":"basis"}}',
                   '{"a":{"value":{"yes":1,"no":0,"unknown":0},"reason":""}}']
        for body in invalid:
            with self.subTest(body=body), self.assertRaises(ValueError):
                parse_output(body, ['a'])

    def test_opinion_requires_exact_components_bounds_and_sum(self):
        from src.catalog.opinions import validate_opinion
        for opinion in ({'yes': 0.7, 'no': 0.2, 'unknown': 0.1},
                        {'yes': 0, 'no': 0, 'unknown': 1}):
            validate_opinion(opinion)
        invalid = [{'yes': 1, 'no': 0}, {'yes': 1, 'no': 0, 'unknown': 0, 'extra': 0},
                   {'yes': True, 'no': 0, 'unknown': 0}, {'yes': -0.1, 'no': 0.5, 'unknown': 0.6},
                   {'yes': float('nan'), 'no': 0, 'unknown': 0},
                   {'yes': 0.4, 'no': 0.4, 'unknown': 0.4},
                   {'yes': '0.5', 'no': 0.5, 'unknown': 0}]
        for opinion in invalid:
            with self.subTest(opinion=opinion), self.assertRaises(ValueError):
                validate_opinion(opinion)

    def test_release_without_task_labels_and_no_family(self):
        self.source()
        meta = assemble(self.root, 'v2', 'samples', catalog_commit='commit')
        self.assertNotIn('type', meta)
        samples, tasks = read_snapshot(self.root, meta)
        self.assertEqual(samples, self.sample)
        self.assertFalse(tasks)
        with self.assertRaisesRegex(ValueError, 'already exists'):
            assemble(self.root, 'v2', 'samples', catalog_commit='commit')

    def test_release_optional_ai_labels_and_frozen_definitions(self):
        run = self.source()
        labels_meta = {**self.metadata, 'sample_source': run.id, 'sample_source_sha256': checksums(run.directory),
                       'label_provenance': {'method': 'ai_generated', 'review_status': 'unverified'}}
        write_run(self.root, 'ai', labels_meta, {}, {'fly': {'sample_1': {'dry_20m': {'yes': 1, 'no': 0, 'unknown': 0}}}})
        meta = assemble(self.root, 'v2', 'samples', label_sources=['ai'], catalog_commit='commit')
        self.assertEqual(read_snapshot(self.root, meta)[1]['fly']['sample_1']['dry_20m'], {'yes': 1, 'no': 0, 'unknown': 0})
        # Subsequent live definition changes do not reinterpret the frozen release.
        p = self.root / 'catalog/v1/classes/bird.yaml'
        doc = load(p)
        doc['features']['bird_f_001']['description'] = 'Changed later'
        write(p, doc)
        export_release_samples(self.root)
        exported = load(self.root / 'docs/assets/release_samples.json')['sources']['v2']
        bird = next(c for c in exported['definitions']['classes'] if c['id'] == 'bird')
        self.assertNotEqual(bird['features'][0]['description'], 'Changed later')
        self.assertEqual(exported['label_provenance']['ai']['method'], 'ai_generated')

    def test_release_tampering_is_detected(self):
        self.source()
        assemble(self.root, 'v2', 'samples', catalog_commit='commit')
        write(self.root / 'releases/v2/samples/bird.json', {'sample_1': {'bird_f_001': 9}})
        with self.assertRaisesRegex(ValueError, 'artifact checksum'):
            read_releases(self.root)

    def test_release_rejects_overlapping_labels(self):
        run = self.source()
        meta = {**self.metadata, 'sample_source': run.id, 'sample_source_sha256': checksums(run.directory),
                'label_provenance': {'method': 'ai_generated', 'review_status': 'unverified'}}
        for sid in ('one', 'two'):
            write_run(self.root, sid, meta, {}, {'fly': {'sample_1': {'dry_20m': {'yes': 1, 'no': 0, 'unknown': 0}}}})
        with self.assertRaisesRegex(ValueError, 'Overlapping'):
            assemble(self.root, 'v2', 'samples', label_sources=['one', 'two'], catalog_commit='commit')
        self.assertFalse((self.root / 'releases/v2').exists())

    def test_web_exports_definitions_and_releases_not_runs(self):
        self.source()
        export_catalog(self.root)
        export_release_samples(self.root)
        catalog = load(self.root / 'docs/assets/catalog.json')
        self.assertFalse(any('instances' in c or 'grounding' in c for c in catalog['classes']))
        self.assertEqual(load(self.root / 'docs/assets/release_samples.json')['sources'], {})
        assemble(self.root, 'v2', 'samples', catalog_commit='commit')
        export_release_samples(self.root)
        self.assertEqual(load(self.root / 'docs/assets/release_samples.json')['sources']['v2']['samples'], self.sample)

    def test_strict_io_rejects_duplicate_keys(self):
        p = self.root / 'duplicate.json'
        p.write_text('{"a":1,"a":2}')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            load(p)
        p = self.root / 'duplicate.yaml'
        p.write_text('a: 1\na: 2\n')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            load(p)
