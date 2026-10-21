import tempfile
import unittest
from pathlib import Path
from src.catalog import Catalog
from src.catalog.io import load, write, instance_items, instance_document
from src.catalog.cub_birds import parse_classes, collect


class CubBirdTest(unittest.TestCase):
    def text(self):
        return ''.join(f'{i} {i:03d}.Fixture_Bird_{i}\n' for i in range(1, 201))

    def test_parser_preserves_original_id_and_normalizes_only_display_name(self):
        rows = parse_classes(self.text())
        self.assertEqual(rows[1], {'class_id': 1, 'original_name': '001.Fixture_Bird_1', 'name': 'Fixture Bird 1'})
        with self.assertRaises(ValueError):
            parse_classes(self.text().replace('200 200.', '199 199.'))
        with self.assertRaises(ValueError):
            parse_classes('1 001.One_Bird\n')

    def test_conflicting_source_runs_do_not_silently_choose_the_latest(self):
        from src.catalog.sources import source_binding
        sources = {
            'run_a': {'provider': 'cub_200_2011', 'class_mapping': {'bird_0001': {'name': 'A'}}},
            'run_b': {'provider': 'cub_200_2011', 'class_mapping': {'bird_0001': {'name': 'B'}}}}
        with self.assertRaisesRegex(ValueError, 'Conflicting source bindings'):
            source_binding(sources, 'cub_200_2011', 'bird_0001')

    def test_missing_binding_recovery_requires_pinned_input_and_matching_names(self):
        import hashlib
        import shutil
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / 'catalog/classes/bird/class.yaml', {'id': 'bird', 'revision': 1,
                'collection': {'source': 'cub_200_2011', 'indices': [1, 100], 'script': 'fixture'}})
            write(root / 'catalog/classes/bird/features.yaml', {'class_id': 'bird', 'features': {}})
            write(root / 'catalog/classes/bird/list.yaml', {'class_id': 'bird', 'instances': {}})
            path = root / 'classes.txt'
            path.write_text(self.text())
            collect(root, classes_file=path, source_id='initial')
            shutil.rmtree(root / 'labels/generated/initial')
            with self.assertRaisesRegex(ValueError, 'Cannot restore missing binding'):
                collect(root, classes_file=path, source_id='unpinned')
            checksum = hashlib.sha256(path.read_bytes()).hexdigest()
            with patch('src.catalog.cub_birds.EXPECTED_SHA256', checksum):
                collect(root, classes_file=path, source_id='recovered')
            self.assertEqual(len(Catalog(root).instances), 100)

    def test_collection_preserves_source_and_repeated_run_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / 'catalog/classes/bird/class.yaml', {'id': 'bird', 'name': 'Bird', 'revision': 1,
                'collection': {'source': 'cub_200_2011', 'indices': [1, 100], 'script': 'shells/catalog/classes_bird_cub.sh'}})
            write(root / 'catalog/classes/bird/features.yaml', {'class_id': 'bird', 'features': {}})
            write(root / 'catalog/classes/bird/list.yaml', {'class_id': 'bird', 'instances': {}})
            path = root / 'classes.txt';path.write_text(self.text())
            collect(root, classes_file=path, source_id='fixture_cub')
            initial = instance_items(load(root / 'catalog/classes/bird/list.yaml'), 'bird')
            self.assertEqual(len(initial), 100)
            self.assertEqual(initial[0]['id'], 'bird_0001')
            self.assertEqual(initial[-1]['id'], 'bird_0100')
            catalog = Catalog(root)
            self.assertEqual(catalog.sources['fixture_cub']['class_mapping']['bird_0001']['class_id'], 1)
            self.assertIsNone(catalog.sources['fixture_cub']['input']['url'])
            self.assertEqual(len(catalog.labels), 0)
            collect(root, classes_file=path, source_id='fixture_cub_refresh')
            current = instance_items(load(root / 'catalog/classes/bird/list.yaml'), 'bird')
            self.assertEqual([(i['id'], i['name']) for i in initial], [(i['id'], i['name']) for i in current])
            self.assertTrue(all(set(i) == {'id', 'name'} for i in current))
            self.assertIn('added_time', Catalog(root).sources['fixture_cub_refresh'])
            with self.assertRaises(ValueError):
                collect(root, classes_file=path, source_id='fixture_cub_refresh')
            bad = path.read_text().replace('001.Fixture_Bird_1\n', '001.Different_Bird\n')
            path.write_text(bad)
            with self.assertRaisesRegex(ValueError, 'different meaning'):
                collect(root, classes_file=path, source_id='bad_refresh')
            self.assertEqual(instance_items(load(root / 'catalog/classes/bird/list.yaml'), 'bird'), current)


if __name__ == '__main__':
    unittest.main()
