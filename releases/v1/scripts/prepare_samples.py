"""Sample anonymous feature combinations from a versioned catalog."""
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from src.catalog.files import FileCatalog
from src.catalog.opinions import FEATURE_VALUE_SCHEMA, validate_feature_opinion
from src.catalog.sample_sources import write_run
from src.catalog.script_metadata import record_script


def generate(root, *, seed=0, source_id='samples', classes=None, count=100,
             feature_values=None, catalog_version='v1'):
    root = Path(root)
    catalog = FileCatalog(root, catalog_version=catalog_version)
    selected = sorted(catalog.classes if classes is None else classes)
    if not selected or not set(selected) <= catalog.classes.keys():
        raise ValueError('Choose known feature groups')
    if type(count) is not int or count < 1:
        raise ValueError('Sample count must be positive')
    if feature_values is not None:
        if not isinstance(feature_values, list) or not feature_values:
            raise ValueError('Supply a nonempty list of feature opinion objects')
        for value in feature_values:
            validate_feature_opinion(value)
    rng = random.Random(seed)

    def sample_value():
        if feature_values is not None:
            return dict(rng.choice(feature_values))
        # Two sorted uniform cuts sample uniformly on the three-mass simplex.
        first, second = sorted((rng.random(), rng.random()))
        return {'belief': first, 'disbelief': second - first, 'uncertain': 1 - second}

    samples = {}
    for cid in selected:
        samples[cid] = {}
        for index in range(1, count + 1):
            sid = f'{cid}_s_{index:06}'
            samples[cid][sid] = {f['id']: sample_value() for f in catalog.classes[cid]['features']}
    meta = {'status': 'complete', 'purpose': 'sample_preparation', 'seed': seed,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'provenance': {'method': 'random', 'script': os.environ.get('CDR_ENTRYPOINT', 'python releases/v1/scripts/prepare_samples.py')},
            'feature_encoding': {**FEATURE_VALUE_SCHEMA,
                                 'sampling': 'uniform_simplex' if feature_values is None else 'discrete_uniform',
                                 **({'values': feature_values} if feature_values is not None else {})},
            'selection': {'classes': selected, 'count_per_class': count},
            'definition_snapshot': {cid: catalog.classes[cid]['features'] for cid in selected},
            'note': 'Independently sampled feature combinations. No real object identity or observed-feature claim.'}
    run = write_run(root, source_id, meta, samples, catalog_version=catalog_version)
    record_script(root, source_id, {'script': os.environ.get('CDR_ENTRYPOINT', 'python releases/v1/scripts/prepare_samples.py'),
                  'source': source_id, 'seed': seed, **meta['selection']})
    return run.stats()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[3])
    p.add_argument('--catalog-version', default='v1')
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--source-id', default='samples')
    p.add_argument('--count', type=int, default=100)
    p.add_argument('--classes', nargs='+')
    p.add_argument('--feature-values', type=json.loads, help='Optional JSON array of belief/disbelief/uncertain objects summing to 1')
    a = p.parse_args()
    print(json.dumps(generate(a.root, seed=a.seed, source_id=a.source_id, classes=a.classes,
                              count=a.count, feature_values=a.feature_values, catalog_version=a.catalog_version), indent=2))


if __name__ == '__main__':
    main()
