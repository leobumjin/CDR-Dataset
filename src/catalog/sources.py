"""Resolve stable class bindings from provider runs without annotating list rows."""
import json
from pathlib import Path
from .io import load


def load_sources(root):
    result = {}
    for path in sorted((Path(root) / 'labels' / 'generated').glob('*/sources.json')):
        meta = load(path)
        if meta['id'] != path.parent.name:
            raise ValueError('Source directory/ID mismatch')
        result[meta['id']] = meta
    return result


def source_binding(sources, provider, instance_id):
    key = {'cub_200_2011': 'class_mapping', 'conceptnet': 'id_registry'}.get(provider)
    if key is None:
        raise ValueError(f'Unsupported class binding provider: {provider}')
    candidates = [meta[key][instance_id] for meta in sources.values()
                  if meta.get('provider') == provider and instance_id in meta.get(key, {})]
    if not candidates:
        raise ValueError(f'Missing source binding: {provider}/{instance_id}')
    if len({json.dumps(v, sort_keys=True) for v in candidates}) != 1:
        raise ValueError(f'Conflicting source bindings: {provider}/{instance_id}')
    return candidates[0]
