import runpy
import shutil
import tempfile
import unittest
from pathlib import Path
from src.catalog.io import load, write
from src.catalog.manual import generate
from src.catalog.cub_birds import collect
from src.catalog import Catalog

ROOT = Path(__file__).resolve().parents[1]


class ManualCatalogTest(unittest.TestCase):
    def test_all_classes_cub_offset_and_repeat_preserve_other_slots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for cid in ['bird', 'human', 'legal_case', 'mammal', 'plant']:
                for name in ['class.yaml', 'features.yaml']:
                    target = root / f'catalog/classes/{cid}/{name}'
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ROOT / f'catalog/classes/{cid}/{name}', target)
            generate(root)
            registry_path = root / 'docs/assets/catalog_generation_scripts.json'
            self.assertEqual(load(registry_path)['manual']['instance_range'], [1, 100])
            names = load(root / 'catalog/classes/bird/list.yaml')['instances']
            self.assertEqual(len(names), 100)
            self.assertTrue(any('penguin' in item['name'] for item in names.values()))
            classes = root / 'classes.txt'
            classes.write_text(''.join(f'{i} {i:03}.Fixture_Bird_{i}\n' for i in range(1, 201)))
            collect(root, classes_file=classes, source_id='fixture_cub')
            self.assertEqual(load(registry_path)['cub']['instance_range'], [101, 300])
            self.assertIn('manual', load(registry_path))
            before = load(root / 'catalog/classes/bird/list.yaml')
            self.assertEqual(before['instances']['bird_0101']['name'], 'Fixture Bird 1')
            self.assertEqual(before['instances']['bird_0300']['name'], 'Fixture Bird 200')
            generate(root)
            collect(root, classes_file=classes, source_id='fixture_cub_repeat')
            self.assertEqual(load(root / 'catalog/classes/bird/list.yaml'), before)
            catalog = Catalog(root)
            self.assertEqual(len(catalog.instances), 700)
            self.assertEqual(len(catalog.features), 35)
            snapshot = load(root / 'docs/assets/catalog.json')
            self.assertEqual(sum(len(c['instances']) for c in snapshot['classes']), 700)
            self.assertEqual(snapshot['tasks'], [])
            for cid in catalog.classes:
                self.assertEqual(len(catalog.classes[cid]['instances']), 300 if cid == 'bird' else 100)
            self.assertEqual(len(catalog.labels), 0)
            self.assertEqual(catalog.sources['fixture_cub']['class_mapping']['bird_0101']['class_id'], 1)

    def test_feature_names_and_order_match_v1_experimental_definitions(self):
        definitions = runpy.run_path(str(ROOT / 'versions/v1/generation/src/dataset_features.py'))['FEATURE_DEFINITIONS']
        for cid, domain in [('bird','birds'),('human','humans'),('legal_case','legal_cases'),('mammal','mammals'),('plant','plants')]:
            features = load(ROOT / f'catalog/classes/{cid}/features.yaml')['features']
            self.assertEqual(list(features), [f'{cid}_f_{i:03}' for i in range(1,8)])
            self.assertEqual([f['name'] for f in features.values()], list(definitions[domain]))
            self.assertTrue(all(set(f) == {'name', 'description'} for f in features.values()))
