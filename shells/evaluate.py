"""Offline dataset integrity and distribution evaluation; no model/API calls."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path


def evaluate(data):
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
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = json.dumps(evaluate(args.data), indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result)
    else:
        print(result, end='')


if __name__ == '__main__':
    main()
