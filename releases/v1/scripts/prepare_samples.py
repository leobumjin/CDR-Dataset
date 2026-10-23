"""Sample anonymous feature combinations from a versioned catalog."""
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import json
import math
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from src.catalog.files import FileCatalog
from src.catalog.opinions import FEATURE_VALUE_SCHEMA, validate_feature_opinion
from src.catalog.sample_sources import write_run
from src.catalog.script_metadata import record_script



# Each component is sampled independently; regions are disjoint.
FEATURE_REGIONS = {
    'high_confidence_true': {'belief': {'minimum': 0.8}},
    'high_confidence_false': {'disbelief': {'minimum': 0.8}},
    'balanced': {key: {'minimum': 0.25, 'maximum': 0.40}
                 for key in ('belief', 'disbelief', 'uncertain')},
    'high_uncertainty': {'uncertain': {'minimum': 0.7}},
}


def in_region(value, region):
    return all(bounds.get('minimum', 0) <= value[key] <= bounds.get('maximum', 1)
               for key, bounds in FEATURE_REGIONS[region].items())


def sample_simplex(rng):
    # Uniform Dirichlet(1,1,1) via two sorted uniform cuts.
    first, second = sorted((rng.random(), rng.random()))
    return {'belief': first, 'disbelief': second - first, 'uncertain': 1 - second}


def round_opinion(value):
    """Allocate 100 hundredths by largest remainder, preserving total mass."""
    keys = tuple(FEATURE_VALUE_SCHEMA['components'])
    scaled = [value[key] * 100 for key in keys]
    units = [math.floor(mass) for mass in scaled]
    order = sorted(range(len(keys)), key=lambda i: scaled[i] - units[i], reverse=True)
    for i in order[:100 - sum(units)]:
        units[i] += 1
    return {key: units[i] / 100 for i, key in enumerate(keys)}


def sample_region(rng, region):
    # Rejection preserves uniform density within the selected region.
    while True:
        value = sample_simplex(rng)
        if in_region(value, region):
            return value


def generate(root, *, seed=0, source_id='samples', classes=None, count=5000,
             feature_values=None, catalog_version='v1', sampling='balanced_regions'):
    root = Path(root)
    catalog = FileCatalog(root, catalog_version=catalog_version)
    selected = sorted(set(catalog.classes if classes is None else classes))
    if not selected or not set(selected) <= catalog.classes.keys():
        raise ValueError('Choose known feature groups')
    if type(count) is not int or count < 1:
        raise ValueError('Sample count must be positive')
    if sampling not in ('balanced_regions', 'uniform_simplex'):
        raise ValueError('Unknown feature sampling mode')
    if feature_values is not None:
        if not isinstance(feature_values, list) or not feature_values:
            raise ValueError('Supply a nonempty list of feature opinion objects')
        for value in feature_values:
            validate_feature_opinion(value)
        feature_values = [round_opinion(value) for value in feature_values]
    rng = random.Random(seed)
    region_counts = dict.fromkeys(FEATURE_REGIONS, 0)

    def sample_value():
        if feature_values is not None:
            return dict(rng.choice(feature_values))
        if sampling == 'uniform_simplex':
            return round_opinion(sample_simplex(rng))
        region = rng.choice(tuple(FEATURE_REGIONS))
        region_counts[region] += 1
        return round_opinion(sample_region(rng, region))

    sampling_metadata = {'base_distribution': 'Dirichlet(1,1,1)',
                         'algorithm': 'two_sorted_uniform_cuts'}
    if sampling == 'balanced_regions' and feature_values is None:
        sampling_metadata.update(
            algorithm='region_choice_then_rejection',
            region_probabilities={key: 0.25 for key in FEATURE_REGIONS},
            regions=FEATURE_REGIONS, region_counts=region_counts)

    per_class, remainder = divmod(count, len(selected))
    extra_classes = set(rng.sample(selected, remainder))
    class_counts = {cid: per_class + int(cid in extra_classes) for cid in selected}
    samples = {}
    for cid in selected:
        if not class_counts[cid]:
            continue
        samples[cid] = {}
        for index in range(1, class_counts[cid] + 1):
            sid = f'{cid}_s_{index:06}'
            samples[cid][sid] = {f['id']: sample_value() for f in catalog.classes[cid]['features']}
    meta = {'status': 'complete', 'purpose': 'sample_preparation', 'seed': seed,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'provenance': {'method': 'random', 'script': os.environ.get('CDR_ENTRYPOINT', 'python releases/v1/scripts/prepare_samples.py')},
            'feature_encoding': {**FEATURE_VALUE_SCHEMA,
                                 'decimal_places': 2,
                                 'sampling': sampling if feature_values is None else 'discrete_uniform',
                                 **({'values': feature_values} if feature_values is not None else {})},
            'sampling_config': {**(sampling_metadata if feature_values is None else {'algorithm': 'uniform_choice'}),
                                'quantization': {'decimal_places': 2, 'algorithm': 'largest_remainder',
                                                 'tie_break': list(FEATURE_VALUE_SCHEMA['components'])}},
            'selection': {'classes': selected, 'count': count, 'class_counts': class_counts},
            'definition_snapshot': {cid: catalog.classes[cid]['features'] for cid in selected},
            'note': 'Independently sampled feature combinations. No real object identity or observed-feature claim.'}
    run = write_run(root, source_id, meta, samples, catalog_version=catalog_version)
    record_script(root, source_id, {'script': os.environ.get('CDR_ENTRYPOINT', 'python releases/v1/scripts/prepare_samples.py'),
                  'source': source_id, 'seed': seed, 'sampling': meta['feature_encoding']['sampling'], **meta['selection']})
    return run.stats()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[3])
    p.add_argument('--catalog-version', default='v1')
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--source-id', default='samples')
    p.add_argument('--count', type=int, default=5000,
                   help='Total samples across selected classes (default: 5000), allocated as evenly as possible')
    p.add_argument('--classes', nargs='+')
    p.add_argument('--sampling', choices=['balanced_regions', 'uniform_simplex'],
                   default='balanced_regions', help='Default: equal-probability choice of four confidence regions')
    p.add_argument('--feature-values', type=json.loads, help='Optional JSON array of belief/disbelief/uncertain objects summing to 1')
    a = p.parse_args()
    print(json.dumps(generate(a.root, seed=a.seed, source_id=a.source_id, classes=a.classes,
                              count=a.count, feature_values=a.feature_values, catalog_version=a.catalog_version, sampling=a.sampling), indent=2))


if __name__ == '__main__':
    main()
