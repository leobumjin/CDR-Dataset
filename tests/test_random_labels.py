import shutil
import tempfile
import unittest
from pathlib import Path
from src.catalog import Catalog
from src.catalog.io import load, write
from src.labels.random_label import generate

ROOT = Path(__file__).resolve().parents[1]


class RandomLabelsTest(unittest.TestCase):
    def test_complete_reproducible_templates_and_encoding_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / 'catalog', root / 'catalog')
            from src.catalog.cub_birds import parse_classes
            rows = parse_classes((ROOT / 'data/sources/cub_200_2011/classes.txt').read_text())
            write(root / 'labels/generated/cub_fixture/sources.json', {
                'id': 'cub_fixture', 'provider': 'cub_200_2011',
                'class_mapping': {f'bird_{i+100:04}': row for i, row in rows.items()}})
            first = generate(root, source_id='random_test_a', seed=42)
            second = generate(root, source_id='random_test_b', seed=42)
            self.assertEqual(first['files'], second['files'])
            default_selection = load(root / 'labels/generated/random_test_a/sources.json')['selection']
            self.assertEqual(default_selection['instance_range'], [1, 100])
            self.assertEqual(default_selection['feature_range'], [1, 7])
            self.assertEqual(set(default_selection['contexts']), {'fly', 'run', 'guilt', 'survive'})
            self.assertNotIn('bird_0101', load(root / 'labels/generated/random_test_a/features/bird.json'))

            self.assertEqual(sum(n for p,n in first['files'].items() if p.startswith('features/')), 3500)
            self.assertEqual(sum(n for p,n in first['files'].items() if p.startswith('tasks_per_context/')), 2500)
            for path in first['files']:
                a = load(root / 'labels/generated/random_test_a' / path)
                b = load(root / 'labels/generated/random_test_b' / path)
                self.assertEqual(a, b)
            catalog = Catalog(root)
            record = next(r for r in catalog.labels.values() if r['source'] == 'random_test_a' and r['kind'] == 'feature')
            with self.assertRaisesRegex(ValueError, 'not configured'):
                catalog.validate_label({**record, 'layer': 'reference'})
            with self.assertRaises(ValueError):
                catalog.validate_label({**record, 'value': 5})
            selected = generate(root, source_id='random_subset', seed=1, classes=['human'],
                                instance_range=[1, 2], feature_range=[2, 3], tasks=['run'],
                                contexts=['run_100m_8kmh'])
            registry = load(root / 'docs/assets/label_generation_scripts.json')
            self.assertEqual(registry['random_label']['instance_range'], [1, 2])
            self.assertEqual(registry['random_label']['feature_range'], [2, 3])
            self.assertEqual(registry['random_label']['contexts'], {'run': ['run_100m_8kmh']})
            self.assertEqual(selected['files'], {'features/human.json': 4, 'tasks_per_context/run.json': 2})
            self.assertEqual(load(root / 'labels/generated/random_subset/sources.json')['selection']['instance_range'], [1, 2])
            mapping = load(root / 'labels/generated/random_subset/features/human.json')
            self.assertEqual(set(mapping), {'human_0001', 'human_0002'})
            self.assertEqual(set(mapping['human_0001']), {'human_f_002', 'human_f_003'})
            with self.assertRaises(ValueError):
                generate(root, source_id='bad_range', instance_range=[10, 1])
            with self.assertRaises(ValueError):
                generate(root, source_id='cub_not_allowed', instance_range=[101, 200])
            with self.assertRaises(ValueError):
                generate(root, source_id='feature_outside_scope', feature_range=[1, 8])
            with self.assertRaises(ValueError):
                generate(root, source_id='bad_class', classes=['unknown'])
            self.assertEqual(load(root / 'docs/assets/label_generation_scripts.json'), registry)
            with self.assertRaisesRegex(ValueError, 'already exists'):
                generate(root, source_id='random_test_a', seed=42)
            self.assertEqual(len(Catalog(root).labels), 12006)
            default = generate(root, seed=7, classes=['human'], instance_range=[1, 1], tasks=[])
            self.assertEqual(default['source'], 'random_label')
            public_labels = load(root / 'docs/assets/instance_labels.json')['sources']
            self.assertEqual(public_labels, {})
            public_tasks = load(root / 'docs/assets/task_labels.json')['sources']
            self.assertEqual(public_tasks, {})
            self.assertEqual(load(root / 'labels/generated/random_label/sources.json')['selection']['contexts'], {})
            before = load(root / 'labels/generated/random_label/features/human.json')
            generate(root, seed=7, classes=['human'], instance_range=[1, 1], tasks=[])
            self.assertEqual(load(root / 'labels/generated/random_label/features/human.json'), before)

