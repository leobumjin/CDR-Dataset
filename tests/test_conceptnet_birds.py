import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from src.catalog import Catalog
from src.catalog.io import load, write, instance_items, instance_document
from src.catalog.conceptnet_birds import Api, children, collect, identifiers, rank, collection_config


CONFIG = {'id': 'bird', 'revision': 1, 'collection': {'source': 'conceptnet', 'indices': [1, 100], 'script': 'shells/catalog/classes_bird_conceptnet.sh'}}


def edge(child, parent, id=None, weight=1, relation='/r/IsA'):
    return {'@id': id or f'{child}->{parent}', 'rel': {'@id': relation},
            'start': {'@id': child}, 'end': {'@id': parent}, 'weight': weight,
            'license': 'cc:by/4.0', 'dataset': '/d/test', 'sources': []}


class ConceptNetBirdTest(unittest.TestCase):
    def make_root(self, root, limit):
        definition = json.loads(json.dumps(CONFIG))
        definition['collection'] = {'source': 'conceptnet', 'indices': [1, limit],
                                    'script': 'shells/catalog/classes_bird_conceptnet.sh'}
        write(root / 'catalog/classes/bird/class.yaml', definition)
        write(root / 'catalog/classes/bird/list.yaml', {'class_id': 'bird', 'instances': {}})
        write(root / 'catalog/classes/bird/features.yaml', {'class_id': 'bird', 'features': {}})

    def dump(self, path, edges):
        opener = gzip.open if path.suffix == '.gz' else open
        with opener(path, 'wt') as output:
            for e in edges:
                metadata = {k:v for k,v in e.items() if k not in ('@id', 'rel', 'start', 'end')}
                output.write('\t'.join([e['@id'], e['rel']['@id'], e['start']['@id'],
                                        e['end']['@id'], json.dumps(metadata)]) + '\n')

    def test_inclusive_index_range_and_invalid_boundaries(self):
        from src.catalog.ranges import reserved_ids
        config = {**CONFIG['collection'], 'indices': [42, 43]}
        self.assertEqual(list(reserved_ids(config)), ['bird_0042', 'bird_0043'])
        for indices in ([0, 100], [100, 1], [True, 100], [1, 10000], [1]):
            with self.assertRaises(ValueError):
                reserved_ids({**config, 'indices': indices})

    def test_unique_children_relation_direction_and_sense_normalization(self):
        data = [edge('/c/en/duck/n', '/c/en/bird/n', 'a'),
                edge('/c/en/duck/n/wn/animal', '/c/en/bird/n', 'b'),
                edge('/c/en/bird', '/c/en/duck', 'reverse'),
                edge('/c/fr/canard', '/c/en/bird', 'french'),
                edge('/c/en/crow', '/c/en/bird', 'related', relation='/r/RelatedTo'),
                edge('/c/en/dodo', '/c/en/bird', 'negative', weight=-1)]
        found = children(data, '/c/en/bird')
        self.assertEqual(set(found), {'/c/en/duck'})
        self.assertEqual(len(found['/c/en/duck']), 2)

    def test_ranking_counts_distinct_child_nodes_and_breaks_ties_by_uri(self):
        candidates = {'/c/en/crow': [], '/c/en/duck': [], '/c/en/eagle': []}
        counts = {'/c/en/crow': {'/c/en/raven': {}}, '/c/en/duck': {'/c/en/mallard': {}},
                  '/c/en/eagle': {}}
        self.assertEqual([r['uri'] for r in rank(candidates, counts)],
                         ['/c/en/crow', '/c/en/duck', '/c/en/eagle'])

    def test_exact_top100_and_source_evidence_without_v1(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_root(root, 100)
            data = [edge(f'/c/en/type_{i:03d}', '/c/en/bird') for i in range(101)]
            data += [edge('/c/en/subtype', '/c/en/type_100')]
            data += [edge('/c/en/subtype/n', '/c/en/type_100/n', 'duplicate-sense')]
            p = root / 'assertions.tsv.gz';self.dump(p, data)
            result = collect(root, assertions=p, source_id='conceptnet_test')
            self.assertEqual(result['selected'], 100)
            items = instance_items(load(root / 'catalog/classes/bird/list.yaml'), 'bird')
            self.assertEqual(items[0]['name'], 'type 100')
            self.assertEqual(items[0]['id'], 'bird_0001')
            self.assertEqual(items[-1]['id'], 'bird_0100')
            self.assertTrue(all(set(i) == {'id', 'name'} for i in items))
            c = Catalog(root)
            self.assertEqual(c.sources['conceptnet_test']['concepts']['bird_0001']['child_count'], 1)
            self.assertEqual(c.sources['conceptnet_test']['input']['mode'], 'assertions_tsv')
            self.assertEqual(len(c.labels), 0)
            self.assertTrue((root / 'labels/generated/conceptnet_test/evidence.json').exists())
            # Refresh preserves IDs even when ranking order changes.
            data += [edge('/c/en/new_subtype_1', '/c/en/type_000'),
                     edge('/c/en/new_subtype_2', '/c/en/type_000')]
            self.dump(p, data)
            collect(root, assertions=p, source_id='conceptnet_refresh')
            refreshed = instance_items(load(root / 'catalog/classes/bird/list.yaml'), 'bird')
            self.assertEqual(refreshed[0]['name'], 'type 100')
            self.assertEqual(refreshed[0]['id'], 'bird_0001')
            self.assertEqual(load(root / 'labels/generated/conceptnet_refresh/ranking.json')[0]['name'], 'type 000')
            self.assertEqual(load(root / 'catalog/classes/bird/class.yaml')['collection']['indices'], [1, 100])
            self.assertNotIn('instances', load(root / 'catalog/classes/bird/class.yaml'))

    def test_insufficient_candidates_does_not_publish_or_replace_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);self.make_root(root, 100)
            path = root / 'assertions.tsv';self.dump(path, [edge('/c/en/duck', '/c/en/bird')])
            with self.assertRaisesRegex(ValueError, 'Only 1 candidates'):
                collect(root, assertions=path, source_id='insufficient')
            self.assertEqual(load(root / 'catalog/classes/bird/list.yaml'), {'class_id': 'bird', 'instances': {}})
            self.assertFalse((root / 'labels/generated/insufficient').exists())

    def test_paginated_api_counts_all_pages_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            api = Api(collection_config(CONFIG['collection'])['api'], tmp, offline=True)
            page1 = {'edges': [edge('/c/en/duck', '/c/en/bird')], 'view': {'nextPage': '/query?offset=1'}}
            page2 = {'edges': [edge('/c/en/crow', '/c/en/bird')]}
            with patch.object(api, 'page', side_effect=[page1, page2]) as page:
                self.assertEqual(len(api.children('/c/en/bird')), 2)
                self.assertEqual(page.call_count, 2)
            with patch.object(api, 'page', return_value={'edges': [], 'view': {'nextPage': '/query?offset=1'}}):
                with self.assertRaisesRegex(ValueError, 'pagination loop'):
                    api.children('/c/en/bird')

    def test_existing_ids_not_reassigned(self):
        rows = [{'uri': '/c/en/crow'}, {'uri': '/c/en/duck'}]
        registry = {'bird_0042': {'source': 'conceptnet', 'concept_uri': '/c/en/duck'},
                    'bird_0043': {'source': 'conceptnet', 'concept_uri': None}}
        result = identifiers(rows, registry)
        self.assertEqual(result['bird_0042']['uri'], '/c/en/duck')
        self.assertEqual(result['bird_0043']['uri'], '/c/en/crow')

    def test_missing_preserved_concept_fails_without_rebinding(self):
        registry = {'bird_0001': {'source': 'conceptnet', 'concept_uri': '/c/en/duck'}}
        with self.assertRaisesRegex(ValueError, 'Preserved concept is missing'):
            identifiers([{'uri': '/c/en/crow'}], registry)
        self.assertEqual(registry['bird_0001']['concept_uri'], '/c/en/duck')

    def test_failed_publication_preserves_class_config_and_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);self.make_root(root, 1)
            before = load(root / 'catalog/classes/bird/class.yaml')
            p = root / 'assertions.tsv';self.dump(p, [edge('/c/en/duck', '/c/en/bird')])
            with patch('src.catalog.conceptnet_birds.FileCatalog', side_effect=ValueError('bad publication')) as mocked:
                mocked.validate_groups = Catalog.validate_groups
                with self.assertRaisesRegex(ValueError, 'bad publication'):
                    collect(root, assertions=p, source_id='failed')
            self.assertEqual(load(root / 'catalog/classes/bird/class.yaml'), before)
            self.assertEqual(load(root / 'catalog/classes/bird/list.yaml'), {'class_id': 'bird', 'instances': {}})
            self.assertFalse((root / 'labels/generated/failed').exists())



if __name__ == '__main__':
    unittest.main()
