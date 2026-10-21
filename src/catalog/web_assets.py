"""Export public catalog definitions for the static project page."""
from pathlib import Path
import re
from .io import load, write


def export_catalog(root):
    root = Path(root)
    classes = []
    for directory in sorted((root / 'catalog/classes').iterdir()):
        if not (directory / 'class.yaml').exists():
            continue
        definition = load(directory / 'class.yaml')
        classes.append({'id': definition['id'], 'name': definition.get('name', definition['id']),
                        'collections': definition.get('collections', []),
                        'instances': load(directory / 'list.yaml')['instances'],
                        'features': load(directory / 'features.yaml')['features']})
    tasks = []
    for path in sorted((root / 'catalog/tasks').glob('*/task.yaml')):
        task = load(path)
        tasks.append({'id': task['id'], 'name': task.get('name', task['id']), 'bindings': task['bindings'],
                      'contexts': load(path.with_name('contexts.yaml'))['contexts']})
    write(root / 'docs/assets/catalog.json', {'classes': classes, 'tasks': tasks})


def export_instance_labels(root):
    """Publish release label selections only; generated values stay local."""
    root = Path(root)
    features, tasks = {}, {}
    directories = [path for path in (root / 'releases').glob('v*/') if re.fullmatch(r'v[1-9][0-9]*', path.name)]
    for directory in sorted(directories, key=lambda path: int(path.name[1:])):
        if not (directory / 'meta_info.json').exists():
            continue
        meta = load(directory / 'meta_info.json')
        if meta.get('id') != directory.name:
            raise ValueError('Release directory/ID mismatch')
        if not isinstance(meta.get('classes'), list) or not meta['classes'] or not all(isinstance(cid, str) and cid for cid in meta['classes']):
            raise ValueError('Release metadata requires explicit classes')
        for key in ('instance_range', 'feature_range'):
            interval = meta.get(key)
            if (not isinstance(interval, list) or len(interval) != 2
                    or any(type(value) is not int for value in interval)
                    or not 1 <= interval[0] <= interval[1]):
                raise ValueError(f'Release metadata requires an inclusive {key}')
        if (not isinstance(meta.get('tasks'), dict) or not meta['tasks']
                or any(not isinstance(ids, list) or not ids or not all(isinstance(i, str) and i for i in ids)
                       for ids in meta['tasks'].values())):
            raise ValueError('Release metadata requires explicit task/context IDs')
        shared = {'kind': 'release', 'name': directory.name,
                  'available': meta.get('status') != 'labels_unavailable',
                  'classes': meta.get('classes', []), 'instance_range': meta.get('instance_range'),
                  'feature_range': meta.get('feature_range'), 'contexts': meta.get('tasks', {})}
        features[directory.name] = {**shared, 'features': {}}
        tasks[directory.name] = {**shared, 'tasks': {}}
        if shared['available']:
            features[directory.name]['features'] = {
                path.stem: load(path) for path in sorted((directory / 'labels/features').glob('*.json'))}
            tasks[directory.name]['tasks'] = {
                path.stem: load(path) for path in sorted((directory / 'labels/tasks_per_context').glob('*.json'))}
    write(root / 'docs/assets/instance_labels.json', {'sources': features})
    write(root / 'docs/assets/task_labels.json', {'sources': tasks})


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    export_catalog(root)
    export_instance_labels(root)
