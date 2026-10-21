import tempfile
import unittest
from pathlib import Path
from src.catalog.io import load, write
from src.catalog.web_assets import export_instance_labels


class ReleaseAssetTest(unittest.TestCase):
    def test_only_release_values_are_exported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / 'labels/generated/random_label/features/bird.json', {'bird_0001': {'bird_f_001': 1}})
            scope = {'classes': ['bird'], 'instance_range': [1, 100], 'feature_range': [1, 7], 'tasks': {'fly': ['dry_20m']}}
            write(root / 'releases/v1/meta_info.json', {'id': 'v1', 'status': 'labels_unavailable', **scope})
            export_instance_labels(root)
            features = load(root / 'docs/assets/instance_labels.json')['sources']
            self.assertEqual(set(features), {'v1'})
            self.assertFalse(features['v1']['available'])
            self.assertEqual(features['v1']['features'], {})
            write(root / 'releases/v2/meta_info.json', {'id': 'v2', 'status': 'released', **scope})
            values = {'bird_0001': {'bird_f_001': 0}}
            tasks = {'bird_0001': {'dry_20m': 'false'}}
            write(root / 'releases/v2/labels/features/bird.json', values)
            write(root / 'releases/v2/labels/tasks_per_context/fly.json', tasks)
            export_instance_labels(root)
            self.assertEqual(load(root / 'docs/assets/instance_labels.json')['sources']['v2']['features']['bird'], values)
            self.assertEqual(load(root / 'docs/assets/task_labels.json')['sources']['v2']['tasks']['fly'], tasks)

    def test_release_scope_is_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / 'releases/v1/meta_info.json', {'id': 'v1', 'status': 'labels_unavailable'})
            with self.assertRaisesRegex(ValueError, 'explicit classes'):
                export_instance_labels(root)
