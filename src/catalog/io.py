"""Strict YAML reads and atomic JSON/YAML writes."""
import json
import os
import tempfile
from pathlib import Path
import yaml


class UniqueLoader(yaml.SafeLoader):
    pass


def mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f'Duplicate YAML/JSON key: {key}')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)


def load(path):
    path = Path(path)
    if path.suffix in ('.yaml', '.yml'):
        return yaml.load(path.read_text(), Loader=UniqueLoader)
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f'Duplicate JSON key: {key}')
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=pairs)


def write(path, body):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = (yaml.safe_dump(body, sort_keys=False, allow_unicode=True, width=100)
            if path.suffix in ('.yaml', '.yml') else
            json.dumps(body, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f'.{path.name}.')
    try:
        with os.fdopen(fd, 'w') as output:
            output.write(text)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def instance_items(document, class_id):
    """Validate a class-scoped instance mapping and expose internal ID records."""
    if (not isinstance(document, dict) or set(document) != {'class_id', 'instances'}
            or document['class_id'] != class_id or not isinstance(document['instances'], dict)):
        raise ValueError('list.yaml requires matching class_id and an instances mapping')
    items = []
    for iid, spec in document['instances'].items():
        if (not isinstance(iid, str) or not iid or not isinstance(spec, dict)
                or set(spec) != {'name'} or not isinstance(spec['name'], str) or not spec['name']):
            raise ValueError('Instance keys must be nonempty IDs with exactly a name field')
        items.append({'id': iid, **spec})
    return items


def instance_document(class_id, items):
    instances = {}
    for item in items:
        if item['id'] in instances:
            raise ValueError(f"Duplicate instance ID: {item['id']}")
        instances[item['id']] = {'name': item['name']}
    document = {'class_id': class_id, 'instances': instances}
    instance_items(document, class_id)
    return document
