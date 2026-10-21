import json
import tempfile
import unittest
from pathlib import Path
from src.catalog import Catalog
from src.catalog.io import load, write, instance_items, instance_document


class CatalogTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cls = {'id': 'bird', 'name': 'Bird', 'revision': 1,
                    'groups': {'bird': [], 'robin': [{'group_id': 'bird'}],
                               'bird_001': [{'group_id': 'robin'}]},
                    'features': {'wings': {'description': 'Has flight wings.', 'values': [0, 0.5, 1]}},
                    'instances': [{'id': 'bird_001', 'revision': 1, 'class': 'bird'}]}
        self.write_class()
        self.write('tasks/fly/task.yaml', {'id': 'fly', 'name': 'Flying', 'revision': 1,
                                        'bindings': [{'class_id': 'bird'}]})
        self.write('tasks/fly/contexts.yaml', {'task_id': 'fly', 'contexts': {
            'dry': {'description': 'Dry conditions'}}})
        self.label = {'id': 'model-1', 'source': 'test_261021', 'kind': 'feature', 'class_id': 'bird',
                      'instance_id': 'bird_001', 'instance_revision': 1,
                      'feature_id': 'bird_f_001', 'feature_revision': 1,
                      'value': 1, 'layer': 'reference', 'status': 'proposed',
                      'provenance': {'method': 'model', 'agent': 'teacher'}}

    def tearDown(self):
        self.tmp.cleanup()

    def write_class(self):
        self.write('classes/bird/list.yaml', instance_document('bird', [
            {'id': i['id'], 'name': i.get('name', i['id'])} for i in self.cls['instances']]))
        self.write('classes/bird/class.yaml', {
            'id': 'bird', 'name': 'Bird', 'revision': 1,
            'instance_revisions': {i['id']: i['revision'] for i in self.cls['instances']}})
        self.write('classes/bird/features.yaml', {'class_id': 'bird', 'features': {
            f'bird_f_{n:03d}': {'name': fid, 'description': fid, **spec} for n, (fid, spec) in enumerate(self.cls['features'].items(), 1)}})
        write(self.root / 'labels/generated/test_261021/sources.json', {'id': 'test_261021', 'classes': {
            'bird': {'instances': {i['id']: {'state': {'fatigue': 'rested'}} for i in self.cls['instances']}}}})
        write(self.root / 'labels/generated/test_261021/groups/bird.json', self.cls['groups'])

    def write(self, relative, value):
        write(self.root / 'catalog' / relative, value)

    def test_list_has_requested_fields_and_metadata_remains_source_specific(self):
        items = load(self.root / 'catalog/classes/bird/list.yaml')
        self.assertEqual(items['class_id'], 'bird')
        self.assertEqual(set(items['instances']['bird_001']), {'name'})
        c = Catalog(self.root)
        self.assertNotIn('state', c.instances['bird', 'bird_001'])
        self.assertEqual(c.sources['test_261021']['classes']['bird']['instances']['bird_001']['state'],
                         {'fatigue': 'rested'})
        details = c.sources['test_261021']
        details['classes']['bird']['instances']['unknown'] = {}
        write(self.root / 'labels/generated/test_261021/sources.json', details)
        with self.assertRaises(ValueError):
            Catalog(self.root)

    def test_list_rejects_missing_fields_and_extra_fields(self):
        p = self.root / 'catalog/classes/bird/list.yaml'
        original = load(p)
        invalids = [
            {'class_id': 'other', 'instances': original['instances']},
            {'class_id': 'bird', 'instances': {'bird_001': {}}},
            {'class_id': 'bird', 'instances': {'bird_001': {'name': 'Bird', 'source': 'redundant'}}},
            {'class_id': 'bird', 'instances': {'bird_001': {'name': 'Bird', 'added_time': 'date'}}},
            {'class_id': 'bird', 'instances': []}]
        for document in invalids:
            write(p, document)
            with self.assertRaises(ValueError):
                Catalog(self.root)
        write(p, original)

    def test_yaml_duplicate_keys_rejected(self):
        p = self.root / 'catalog/classes/bird/class.yaml'
        p.write_text('id: bird\nid: mammal\nrevision: 1\n')
        with self.assertRaises(ValueError):
            Catalog(self.root)

    def test_fact_check_adds_history_without_overwriting(self):
        c = Catalog(self.root)
        first = c.append_label(self.label)
        checked = {**self.label, 'id': 'review-1', 'value': 0, 'status': 'fact_checked',
                   'supersedes': first['id'], 'provenance': {'method': 'human_review',
                   'agent': 'reviewer', 'checked_at': '2026-10-21', 'evidence': [{'path': 'evidence.txt'}]}}
        c.append_label(checked)
        loaded = Catalog(self.root)
        self.assertEqual(len(loaded.labels), 2)
        self.assertEqual(loaded.labels['model-1']['value'], 1)
        self.assertEqual(loaded.labels['review-1']['value'], 0)

    def test_fact_check_requires_evidence(self):
        with self.assertRaises(ValueError):
            Catalog(self.root).append_label({**self.label, 'status': 'fact_checked'})
        self.assertEqual(Catalog(self.root).stats()['labels'], 0)

    def test_duplicate_ids_and_out_of_range_values_rejected(self):
        c = Catalog(self.root)
        c.append_label(self.label)
        with self.assertRaises(ValueError):
            c.append_label(self.label)
        with self.assertRaises(ValueError):
            c.append_label({**self.label, 'id': 'invalid', 'value': 2})
        self.assertEqual(Catalog(self.root).stats()['labels'], 1)

    def test_multiple_groups_supported(self):
        self.cls['groups']['flightless_bird'] = [{'group_id': 'bird'}]
        self.cls['groups']['bird_001'].append({'group_id': 'flightless_bird'})
        self.write_class()
        c = Catalog(self.root)
        self.assertEqual(len(c.groups['test_261021', 'bird']['bird_001']), 2)

    def test_missing_groups_and_membership_cycles_rejected(self):
        self.cls['groups']['bird_001'] = [{'group_id': 'missing'}]
        self.write_class()
        with self.assertRaises(ValueError):
            Catalog(self.root)
        self.cls['groups']['bird_001'] = [{'group_id': 'robin'}]
        self.cls['groups']['a'] = [{'group_id': 'b'}]
        self.cls['groups']['b'] = [{'group_id': 'a'}]
        self.write_class()
        with self.assertRaises(ValueError):
            Catalog(self.root)

    def test_revision_changes_keep_old_history_but_require_new_labels_to_use_current(self):
        c = Catalog(self.root)
        c.append_label(self.label)
        self.cls['instances'][0]['revision'] = 2
        self.write_class()
        c = Catalog(self.root)
        self.assertEqual(c.labels['model-1']['instance_revision'], 1)
        with self.assertRaises(ValueError):
            c.append_label({**self.label, 'id': 'stale'})
        with self.assertRaises(ValueError):
            c.append_label({**self.label, 'id': 'bad-update', 'instance_revision': 2, 'supersedes': 'model-1'})
        c.append_label({**self.label, 'id': 'new-profile-label', 'instance_revision': 2})

    def test_judgment_validates_task_context_and_class(self):
        judgment = {k: v for k, v in self.label.items() if k not in ('feature_id', 'feature_revision')}
        judgment.update(kind='judgment', task_id='fly', task_revision=1,
                        context_id='dry', context_revision=1, value='true')
        c = Catalog(self.root)
        c.append_label(judgment)
        self.assertTrue((self.root / 'labels/generated/test_261021/tasks_per_context/fly.json').exists())
        with self.assertRaises(ValueError):
            c.append_label({**judgment, 'id': 'bad', 'context_id': 'missing'})

    def test_json_results_remain_arrays_and_sources_coexist(self):
        write(self.root / 'labels/generated/other_261021/sources.json', {'id': 'other_261021'})
        c = Catalog(self.root)
        c.append_label(self.label)
        c.append_label({**self.label, 'id': 'other-model', 'source': 'other_261021', 'value': 0})
        path = self.root / 'labels/generated/test_261021/features/bird.json'
        self.assertIsInstance(json.loads(path.read_text()), list)
        self.assertEqual(len(Catalog(self.root).labels), 2)
        view = c.feature_sources('bird')['instances']['bird_001']['bird_f_001']
        self.assertEqual(set(view), {'test_261021', 'other_261021'})

    def test_invalid_batch_does_not_write_partial_results(self):
        c = Catalog(self.root)
        with self.assertRaises(ValueError):
            c.append_labels([self.label, {**self.label, 'id': 'invalid', 'value': 2}])
        self.assertFalse((self.root / 'labels/generated/test_261021/features/bird.json').exists())

    def test_feature_id_key_and_name_are_separate_and_validated(self):
        c = Catalog(self.root)
        self.assertEqual(c.features['bird', 'bird_f_001']['name'], 'wings')
        path = self.root / 'catalog/classes/bird/features.yaml'
        definition = load(path)
        spec = definition['features'].pop('bird_f_001')
        definition['features']['bird_f_01'] = spec
        write(path, definition)
        with self.assertRaisesRegex(ValueError, 'class_f_001'):
            Catalog(self.root)
        definition['features'] = {'bird_f_001': {k:v for k,v in spec.items() if k != 'name'}}
        write(path, definition)
        with self.assertRaisesRegex(ValueError, 'requires a name'):
            Catalog(self.root)
        definition['features'] = {'bird_f_001': spec, 'bird_f_002': dict(spec)}
        write(path, definition)
        with self.assertRaisesRegex(ValueError, 'Duplicate feature names'):
            Catalog(self.root)

    def test_undefined_feature_encoding_blocks_values_without_assuming_a_scale(self):
        self.cls['features'] = {'wings': {'description': 'Has flight wings.'}}
        self.write_class()
        c = Catalog(self.root)
        for value in (0, 0.5, 1.0, True, None, 'unknown'):
            with self.assertRaisesRegex(ValueError, 'value schema is not configured'):
                c.append_label({**self.label, 'value': value})
        self.assertEqual(len(Catalog(self.root).labels), 0)
        self.cls['features']['wings']['values'] = ['present', 'absent', 'undetermined']
        self.write_class()
        Catalog(self.root).append_label({**self.label, 'value': 'present'})

    def test_boolean_unknown_and_numeric_traits_have_distinct_semantics(self):
        self.cls['features'] = {
            'wings': {'type': 'boolean', 'nullable': True},
            'mass': {'type': 'number', 'unit': 'g', 'minimum': 0, 'nullable': True}}
        self.write_class()
        c = Catalog(self.root)
        c.append_label({**self.label, 'id': 'known-true', 'value': True})
        c.append_label({**self.label, 'id': 'explicit-unknown', 'value': None})
        for value in (0, 0.5, 1, 'true'):
            with self.assertRaises(ValueError):
                c.append_label({**self.label, 'id': 'invalid', 'value': value})
        for value in (-1, True, float('nan')):
            with self.assertRaises(ValueError):
                c.append_label({**self.label, 'id': 'invalid-mass', 'feature_id': 'bird_f_002', 'value': value})
        c.append_label({**self.label, 'id': 'measured-mass', 'feature_id': 'bird_f_002', 'value': 12.5})
        self.assertEqual(len(Catalog(self.root).labels), 3)

    def test_unmigrated_classes_are_not_loaded_or_modified(self):
        path = self.root / 'catalog/classes/human/list.json'
        path.parent.mkdir(parents=True)
        path.write_text('[{"id":"human_001","name":"Legacy human"}]')
        before = path.read_bytes()
        c = Catalog(self.root)
        self.assertEqual(set(c.classes), {'bird'})
        self.assertEqual(path.read_bytes(), before)



if __name__ == '__main__':
    unittest.main()
