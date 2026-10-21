"""Generate reproducible synthetic feature and task label templates."""
import argparse
import json
import random
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from src.catalog import Catalog
from src.catalog.web_assets import export_instance_labels
from src.catalog.script_metadata import record_script
from src.catalog.files import safe_id
from src.catalog.io import write


DEFAULT_CLASSES = ['bird', 'human', 'legal_case', 'mammal', 'plant']
DEFAULT_INSTANCE_RANGE = (1, 100)
DEFAULT_FEATURE_RANGE = (1, 7)
DEFAULT_CONTEXTS = {'fly': ['dry_20m', 'dry_500m', 'wet_20m', 'dry_5m', 'wet_500m'], 'guilt': ['ordinary_situation', 'emergency_necessity', 'official_duties', 'supervisors_order', 'friends_request'], 'run': ['run_100m_8kmh', 'run_5km_10kmh', 'run_1km_uphill', 'run_100m_12kmh', 'run_10km_8kmh'], 'survive': ['mammal_mild_7d', 'mammal_cold_24h', 'mammal_heat_24h', 'mammal_no_water_food_3d', 'mammal_no_food_14d', 'plant_no_water_3d', 'plant_hot_drought_30d', 'plant_freezing_7d', 'plant_watered_7d', 'plant_waterlogged_7d']}


def generate(root, *, seed=0, source_id=None, classes=None, instance_range=None,
             feature_range=None, tasks=None, contexts=None):
    root = Path(root)
    catalog = Catalog(root)
    now = datetime.now(ZoneInfo('Asia/Seoul')).isoformat()
    source_id = safe_id(source_id or 'random_label')
    destination = root / 'labels' / 'generated' / source_id
    if destination.exists() and source_id != 'random_label':
        raise ValueError(f'Source run already exists: {source_id}')
    rng = random.Random(seed)
    values = [0, 0.5, 1]
    metadata = {'id': source_id, 'provider': 'random', 'synthetic': True,
                'purpose': 'template', 'seed': seed, 'created_at': now,
                'script': 'shells/labels/random_label.sh',
                'feature_values': values, 'task_values': ['true', 'false', 'ambiguous'],
                'note': 'Independent random placeholders; not observations or factual judgments. Feature encoding is local to this template run.'}
    instance_range = list(DEFAULT_INSTANCE_RANGE if instance_range is None else instance_range)
    feature_range = list(DEFAULT_FEATURE_RANGE if feature_range is None else feature_range)
    selected_classes = sorted(DEFAULT_CLASSES if classes is None else classes)
    selected_tasks = sorted(DEFAULT_CONTEXTS if tasks is None else tasks)
    if not set(selected_classes) <= set(catalog.classes) or not set(selected_tasks) <= set(catalog.tasks):
        raise ValueError('Unknown selected class or task')
    for interval in (instance_range, feature_range):
        if interval is not None and (len(interval) != 2 or not 1 <= interval[0] <= interval[1]):
            raise ValueError('Ranges must be inclusive positive START END pairs')
    if instance_range[1] > 100:
        raise ValueError('Random labels are limited to manual instances 1..100')
    if feature_range[1] > 7:
        raise ValueError('Feature range must stay within the configured 1..7 scope')
    applicable = {(tid, cid, ctxid) for tid, cid, ctxid in catalog.contexts
                  if tid in selected_tasks and cid in selected_classes}
    if contexts is None:
        selected_contexts = {(tid, cid, ctxid) for tid, cid, ctxid in applicable
                             if ctxid in DEFAULT_CONTEXTS.get(tid, [])}
    else:
        if not set(contexts) <= {key[2] for key in applicable}:
            raise ValueError('Unknown selected context')
        selected_contexts = {key for key in applicable if key[2] in contexts}
    def in_range(identifier, interval):
        return interval is None or interval[0] <= int(identifier.rsplit('_', 1)[-1]) <= interval[1]
    metadata['selection'] = {'classes': selected_classes, 'instance_range': instance_range,
                             'feature_range': feature_range, 'tasks': selected_tasks, 'contexts': contexts}
    records = {}
    for (cid, iid), instance in sorted(catalog.instances.items()):
        if cid not in selected_classes or not in_range(iid, instance_range):
            continue
        for (fcid, fid), feature in sorted(catalog.features.items()):
            if fcid == cid and in_range(fid, feature_range):
                records.setdefault(f'features/{cid}.json', {}).setdefault(iid, {})[fid] = rng.choice(values)
        for (tid, ccid, ctxid), context in sorted(catalog.contexts.items()):
            if ccid == cid and (tid, ccid, ctxid) in selected_contexts:
                records.setdefault(f'tasks_per_context/{tid}.json', {}).setdefault(iid, {})[ctxid] = rng.choice(metadata['task_values'])
    metadata['selection']['contexts'] = {
        Path(path).stem: sorted({context_id for sample in values.values() for context_id in sample})
        for path, values in records.items() if path.startswith('tasks_per_context/')}
    metadata['selection']['tasks'] = sorted(metadata['selection']['contexts'])
    if not records:
        raise ValueError('Selection contains no feature or task labels')
    previous = {p.relative_to(destination): p.read_bytes() for p in destination.rglob('*') if p.is_file()}
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    try:
        write(destination / 'sources.json', metadata)
        for path, labels in records.items():
            write(destination / path, labels)
        Catalog(root)
        if source_id == 'random_label':
            export_instance_labels(root)
        record_script(root, 'random_label', {
            'script': 'shells/labels/random_label.sh', 'source': source_id,
            **metadata['selection'], 'seed': seed}, category='label')
    except Exception:
        shutil.rmtree(destination)
        for relative, raw in previous.items():
            path = destination / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        raise
    return {'source': source_id, 'files': {path: sum(len(values) for values in labels.values()) for path, labels in records.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--source-id', default='random_label', help='Output directory name (default: random_label; regenerated in place)')
    parser.add_argument('--classes', nargs='+')
    parser.add_argument('--instance-range', nargs=2, type=int, default=DEFAULT_INSTANCE_RANGE, metavar=('START', 'END'), help='Manual instance suffixes, default: 1 100')
    parser.add_argument('--feature-range', nargs=2, type=int, default=DEFAULT_FEATURE_RANGE, metavar=('START', 'END'), help='Feature suffixes, default: 1 7')
    parser.add_argument('--tasks', nargs='*')
    parser.add_argument('--contexts', nargs='*')
    args = parser.parse_args()
    print(json.dumps(generate(args.root, seed=args.seed, source_id=args.source_id, classes=args.classes,
                              instance_range=args.instance_range, feature_range=args.feature_range,
                              tasks=args.tasks, contexts=args.contexts), indent=2))


if __name__ == '__main__':
    main()
