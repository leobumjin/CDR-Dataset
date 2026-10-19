"""Run the archived v1 generator into runs/v1/<name>, never into a release."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

PIPELINE = Path(__file__).resolve().parent
ROOT = PIPELINE.parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['inputs', 'features', 'labels', 'split'])
    parser.add_argument('--run', required=True, help='New experiment name under runs/v1')
    parser.add_argument('--model', choices=['gpt-5.4', 'gpt-4o'], default='gpt-5.4')
    parser.add_argument('--dry-run', action='store_true', help='API stages: validate without requests')
    args = parser.parse_args()
    if not args.run or args.run in ('.', '..') or Path(args.run).name != args.run:
        parser.error('--run must be a single directory name')
    base = (ROOT / 'runs/v1' / args.run).resolve()
    allowed = (ROOT / 'runs').resolve()
    if allowed not in base.parents or allowed == ROOT or ROOT not in allowed.parents:
        parser.error('Run directory must remain inside repository runs/')
    for folder in ('data', 'versions', '.git'):
        protected = (ROOT / folder).resolve()
        if base == protected or protected in base.parents:
            parser.error('Run destination overlaps protected files')
    if (base / 'split_revision.json').exists():
        parser.error('This run is finalized; use a new run name for further generation')
    if args.stage == 'split' and not any((base / 'labels').glob('*/dataset.jsonl')):
        parser.error('Generate labels before the final split stage')
    scripts = {'inputs': 'make_synthetic_inputs.py', 'features': 'make_api_based_features.py',
               'labels': 'make_api_based_labels.py', 'split': 'resplit_dataset.py'}
    command = [sys.executable, str(PIPELINE / 'src' / scripts[args.stage])]
    if args.stage == 'inputs':
        if args.dry_run:
            parser.error('--dry-run applies only to API stages')
        command += ['--output-dir', str(base / 'inputs'), '--catalog', str(PIPELINE / 'configs/species_catalog.json'),
                    '--num-per-domain', '100', '--seed', '2027', '--split-unit', 'instance',
                    '--train-fraction', '0.8', '--validation-fraction', '0']
    elif args.stage == 'split':
        if args.dry_run:
            parser.error('--dry-run applies only to API stages')
        command += ['--root', str(base), '--backup', str(base.with_name(base.name + '-before-split')), '--seed', '2027']
    else:
        command += ['--input-dir', str(base / 'inputs'), '--output-dir', str(base / args.stage / args.model), '--model', args.model]
        if args.stage == 'labels':
            command += ['--feature-dir', str(base / 'features' / args.model)]
        if args.dry_run:
            command += ['--dry-run']
    env = os.environ.copy()
    # Explicit paths take precedence over inherited dataset destination settings.
    for name in ('DATASET_INPUT_DIR', 'DATASET_FEATURE_DIR', 'DATASET_LABEL_DIR'):
        env.pop(name, None)
    return subprocess.call(command, cwd=ROOT, env=env)


if __name__ == '__main__':
    raise SystemExit(main())
