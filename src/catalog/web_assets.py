"""Export definitions and explicitly selected frozen feature-sample releases."""
from pathlib import Path
from .files import FORMAT, FileCatalog
from .releases import read_releases, read_snapshot
from .io import write
from .opinions import TASK_LABEL_SCHEMA


def export_catalog(root, catalog_version='v1'):
    root = Path(root)
    catalog = FileCatalog(root, catalog_version=catalog_version)
    classes = [{**c, 'features': {f['id']: {k: v for k, v in f.items() if k != 'id'} for f in c['features']}}
               for c in catalog.classes.values()]
    tasks = list(catalog.tasks.values())
    write(root / 'docs/assets/catalog.json', {'catalog_version': catalog_version, 'classes': classes, 'tasks': tasks, 'task_label_schema': TASK_LABEL_SCHEMA})
    write(root / 'docs/assets/info.json', {
        'catalog_version': catalog_version,
        'sample_definition': 'A sample is determined by a random combination of feature values, subject to the selected generation constraints.',
        'classes': {c['id']: {k: v for k, v in c.items() if k != 'features'} for c in classes},
        'features': {c['id']: c['features'] for c in classes},
        'tasks': {t['id']: t for t in tasks},
        'task_label_schema': TASK_LABEL_SCHEMA,
    })


def export_release_samples(root):
    root = Path(root)
    sources = {}
    for release_id, meta in read_releases(root).items():
        available = meta.get('format') == FORMAT and meta.get('status') == 'released'
        samples, tasks = read_snapshot(root, meta) if available else ({}, {})
        frozen = FileCatalog(root / 'releases' / release_id) if available else None
        sources[release_id] = {'available': available, 'classes': meta['classes'],
                               'status': meta['status'], 'samples': samples, 'tasks': tasks,
                               'sample_provenance': meta.get('sample_provenance', {}),
                               'label_provenance': meta.get('label_provenance', {}),
                               'feature_encoding': meta.get('feature_encoding', {}),
                               'task_label_schema': meta.get('task_label_schema'),
                               'definitions': ({'classes': list(frozen.classes.values()),
                                                'tasks': list(frozen.tasks.values()),
                                                'contexts': [{'task_id': tid, 'class_id': cid, **context}
                                                             for (tid, cid, _), context in frozen.contexts.items()]}
                                               if frozen else None)}
    write(root / 'docs/assets/release_samples.json', {'sources': sources})



if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--catalog-version', default='v1')
    args = parser.parse_args()
    export_catalog(args.root, catalog_version=args.catalog_version)
    export_release_samples(args.root)
