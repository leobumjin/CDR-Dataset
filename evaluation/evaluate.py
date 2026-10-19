"""Offline dataset integrity and distribution evaluation; no model/API calls."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path


def evaluate_public(data, metadata=None):
    metadata = Path(metadata) if metadata else Path(__file__).resolve().parents[1] / 'versions' / data.name / 'metadata'

    rows = [json.loads(line) for line in (data/'samples.jsonl').open()]
    queries = {r['query_id']: r for r in json.loads((metadata/'queries.json').read_text())['queries']}
    contexts = {r['context_id']: r for r in json.loads((metadata/'contexts.json').read_text())['contexts']}
    features = {(r['domain'], r['feature_id']): r for r in json.loads((metadata/'features.json').read_text())['features']}
    seen, splits = set(), defaultdict(set)
    for row in rows:
        key = row['query_id'], row['context_id'], row['entity_id']
        if key in seen:
            raise ValueError(f'Duplicate public sample: {key}')
        seen.add(key)
        if row['label'] not in ('true', 'false'):
            raise ValueError('Public labels must be strings true/false')
        if queries[row['query_id']]['query_str'] != row['query_str']:
            raise ValueError('Query metadata mismatch')
        context = contexts[row['context_id']]
        if context['context_str'] != row['context_str'] or context['query_id'] != row['query_id']:
            raise ValueError('Context metadata mismatch')
        for name, value in row['feature_values'].items():
            allowed = features[row['domain'], name]['possible_values']
            if not any(type(value) is type(v) and value == v for v in allowed):
                raise ValueError(f'Feature metadata mismatch: {name}')
        splits[row['entity_id']].add(row['split'])
    if any(len(v) != 1 for v in splits.values()):
        raise ValueError('Public entity spans splits')
    return {'samples': len(rows), 'entities': len(splits),
            'labels': dict(Counter(r['label'] for r in rows)),
            'splits': dict(Counter(r['split'] for r in rows)),
            'queries': len(queries), 'contexts': len(contexts), 'features': len(features)}


def evaluate(data, metadata=None):
    data = Path(data)
    public = evaluate_public(data, metadata) if (data / 'samples.jsonl').exists() else None
    if (data / 'source').is_dir():
        data = data / 'source'
    reports = {}
    files = sorted((Path(data) / 'labels').glob('*/dataset.jsonl'))
    if not files:
        raise ValueError('No labels/<teacher>/dataset.jsonl found')
    for path in files:
        rows = [json.loads(line) for line in path.open()]
        if not rows or len({r['pair_id'] for r in rows}) != len(rows):
            raise ValueError(f'Empty data or duplicate pair IDs: {path}')
        instances = defaultdict(list)
        for row in rows:
            if type(row['label']) is not int or row['label'] not in (0, 1):
                raise ValueError(f'Nonbinary label: {path}')
            instances[row['domain'], row['instance_id']].append(row)
        for key, group in instances.items():
            if len({r['split'] for r in group}) != 1:
                raise ValueError(f'Instance spans splits: {key}')
            if len({r['context_id'] for r in group}) != len(group):
                raise ValueError(f'Duplicate context: {key}')
            if len({tuple(r['feature_vector']) for r in group}) != 1:
                raise ValueError(f'Inconsistent features: {key}')
        domains = {}
        for domain in sorted({r['domain'] for r in rows}):
            rr = [r for r in rows if r['domain'] == domain]
            contexts = {r['context_id'] for r in rr}
            groups = [v for (d, _), v in instances.items() if d == domain]
            if any({r['context_id'] for r in group} != contexts for group in groups):
                raise ValueError(f'Missing contexts: {domain}')
            domains[domain] = {'instances': len(groups), 'pairs': len(rr),
                               'contexts': len(contexts),
                               'labels': dict(Counter(r['label'] for r in rr)),
                               'split_pairs': dict(Counter(r['split'] for r in rr)),
                               'context_varying_instances': sum(len({r['label'] for r in g}) > 1 for g in groups)}
        reports[path.parent.name] = {'instances': len(instances), 'pairs': len(rows), 'domains': domains}
    if public is not None:
        reports["public_schema"] = public
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--metadata', type=Path, help='Version metadata directory; inferred for data/v1, data/v2, etc.')
    args = parser.parse_args()
    result = json.dumps(evaluate(args.data, args.metadata), indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result)
    else:
        print(result, end='')


if __name__ == '__main__':
    main()
