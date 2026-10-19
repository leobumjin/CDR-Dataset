"""Repartition saved data without API calls; preserve a backup and source provenance."""
from __future__ import annotations
import argparse
from collections import defaultdict
from pathlib import Path
import random
import shutil
from dataset_common import read_json, read_jsonl, write_json, write_jsonl, digest, file_digest
from make_synthetic_inputs import make_schedules


SPLITS = ("train", "revision-1", "revision-2", "test")
FRACTIONS = dict(zip(SPLITS, (.4, .2, .2, .2)))

def split_assignment(instances, seed=2027):
    domains = defaultdict(list)
    for row in instances:
        if row.get('split') == 'validation':
            continue
        domains[row['domain']].append(row['instance_id'])
    assignment = {}
    for domain, ids in sorted(domains.items()):
        ids = sorted(ids)
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate instance ID')
        random.Random(f'{seed}:{domain}').shuffle(ids)
        if len(ids) % 5:
            raise ValueError('Each domain needs a multiple of five non-validation instances')
        sizes = [len(ids) * n // 5 for n in (2, 1, 1, 1)]
        offset = 0
        for split, count in zip(SPLITS, sizes):
            assignment.update({(domain, iid): split for iid in ids[offset:offset + count]})
            offset += count
    return assignment


def canonical_id(row):
    return row.get('pair_id', '').split('/')[0] or row.get('instance_id', '').replace(' ', '_')



def refresh_configuration_status(value):
    records = []
    def collect(item):
        if isinstance(item, list):
            for child in item: collect(child)
        elif isinstance(item, dict):
            if all(k in item for k in ('domain', 'split', 'feature_vector')):
                records.append(item)
            for child in item.values(): collect(child)
    collect(value)
    seen = defaultdict(set)
    for row in records:
        if row['split'] == 'train': seen[row['domain']].add(tuple(row['feature_vector']))
    for row in records:
        if 'configuration_status' in row:
            row['configuration_status'] = ('training' if row['split'] == 'train' else
                'seen_configuration' if tuple(row['feature_vector']) in seen[row['domain']] else 'new_configuration')
    return value


def repartition(root, backup, seed=2027):
    instances = read_jsonl(root / 'inputs/instances.jsonl')
    assignment = split_assignment(instances, seed)
    if backup.exists():
        raise ValueError(f'Backup already exists: {backup}')
    shutil.copytree(root, backup)
    revision = {'seed': seed, 'unit': 'instance', 'fractions': FRACTIONS,
                'assignment_sha256': digest(sorted((d, i, s) for (d, i), s in assignment.items())),
                'source_backup': str(backup), 'policy': 'Keep five contexts together; feature duplicates are preserved.'}

    def update(value):
        if isinstance(value, list):
            return [update(v) for v in value]
        if not isinstance(value, dict):
            return value
        value = {k: update(v) for k, v in value.items()}
        key = (value.get('domain'), canonical_id(value))
        if 'split' in value and key in assignment:
            value['split'] = assignment[key]
            if 'split_group' in value:
                value['split_group'] = key[1]
        return value

    for path in sorted(root.rglob('*')):
        if path.suffix == '.jsonl':
            write_jsonl(path, refresh_configuration_status(update(read_jsonl(path))))
        elif path.suffix == '.json':
            write_json(path, refresh_configuration_status(update(read_json(path))))

    overlap = []
    for dataset in sorted((root / 'labels').glob('*/dataset.jsonl')):
        rows = read_jsonl(dataset)
        seen = defaultdict(set)
        for row in rows:
            if row['split'] == 'train':
                seen[row['domain']].add(tuple(row['feature_vector']))
        for row in rows:
            row['configuration_status'] = ('training' if row['split'] == 'train' else
                'seen_configuration' if tuple(row['feature_vector']) in seen[row['domain']] else 'new_configuration')
        write_jsonl(dataset, rows)
        for variant in rows[0]['student_prompts']:
            directory = dataset.parent / 'student' / variant
            for split in (*SPLITS, 'validation'):
                write_jsonl(directory / f'{split}.jsonl', [
                    {**{k: row[k] for k in ('pair_id', 'domain', 'instance_id', 'context_id', 'configuration_status')},
                     'prompt': row['student_prompts'][variant], 'completion': str(row['label'])}
                    for row in rows if row['split'] == split])
        summary = read_json(dataset.parent / 'summary.json')
        for domain, stats in summary['domains'].items():
            domain_rows = [r for r in rows if r['domain'] == domain]
            stats['split_pairs'] = {s: sum(r['split'] == s for r in domain_rows) for s in SPLITS}
            unique = {canonical_id(r): r for r in domain_rows}
            test = [r for r in unique.values() if r['split'] == 'test']
            overlap.append({'teacher': dataset.parent.name, 'domain': domain,
                            'instances': len(unique), 'unique_feature_vectors': len({tuple(r['feature_vector']) for r in unique.values()}),
                            'test_instances': len(test), 'test_seen_feature_instances': sum(r['configuration_status'] == 'seen_configuration' for r in test)})
        summary['split_revision'] = revision
        write_json(dataset.parent / 'summary.json', summary)
        write_json(dataset.parent / 'split_revision.json', revision)
    manifest = read_json(root / 'inputs/manifest.json')
    write_json(root / 'inputs/schedules.json', make_schedules(read_jsonl(root / 'inputs/instances.jsonl'), seed, manifest.get('initial_fraction', .5)))
    manifest['files'] = {name: file_digest(root / 'inputs' / name) for name in manifest['files']}
    manifest['split_unit'] = 'instance'
    manifest['split_fractions'] = revision['fractions']
    manifest['counts'] = {d: {s: sum(dd == d and ss == s for (dd, _), ss in assignment.items())
                              for s in SPLITS} for d in sorted({d for d, _ in assignment})}
    # dataset_fingerprint is source generation provenance; revision hashes track this repartition.
    manifest['split_revision'] = revision
    write_json(root / 'inputs/manifest.json', manifest)
    write_json(root / 'split_revision.json', {**revision, 'feature_overlap': overlap})
    return overlap


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('data/current'))
    parser.add_argument('--backup', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=2027)
    args = parser.parse_args()
    for row in repartition(args.root, args.backup, args.seed):
        print(row)
