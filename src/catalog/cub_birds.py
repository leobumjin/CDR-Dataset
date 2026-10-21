"""Import bird names from the public CUB-200-2011 classes.txt distribution."""
import argparse
import hashlib
import re
import shutil
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen
from zoneinfo import ZoneInfo
from .script_metadata import record_script
from .files import FileCatalog, safe_id
from .io import load, write, instance_items, instance_document
from .ranges import reserved_ids
from .sources import load_sources, source_binding


REPOSITORY = 'pawlo2013/CUB'
REVISION = '8a8486039c718e33d87b96ed42c0f457e6a7d939'
PATH = 'CUB_200_2011/classes.txt'
URL = f'https://huggingface.co/datasets/{REPOSITORY}/resolve/{REVISION}/{PATH}'
PROJECT = 'https://www.vision.caltech.edu/datasets/cub_200_2011/'
EXPECTED_SHA256 = '66a884364a73edde6c71eeb7fd5d8bb791e80979b64759bd6a5d5d209bdc02ba'


def parse_classes(text):
    classes = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        number, original = line.split(maxsplit=1)
        number = int(number)
        match = re.fullmatch(r'(\d+)\.(.+)', original)
        if not match or int(match[1]) != number or number in classes:
            raise ValueError(f'Invalid or duplicate CUB class: {line}')
        classes[number] = {'class_id': number, 'original_name': original,
                           'name': match[2].replace('_', ' ')}
    if set(classes) != set(range(1, 201)):
        raise ValueError('Expected the complete original CUB class IDs 1..200')
    return classes


def collect(root, *, classes_file=None, source_id=None):
    root = Path(root)
    definition = load(root / 'catalog/classes/bird/class.yaml')
    declaration = (next(c for c in definition['collections'] if c['source'] == 'cub_200_2011')
                   if 'collections' in definition else definition['collection'])
    if declaration['source'] != 'cub_200_2011':
        raise ValueError('class.yaml source must be cub_200_2011')
    slots = reserved_ids(declaration)
    offset = declaration['indices'][0] - 1 if 'collections' in definition else 0
    if len(slots) > 200 or declaration['indices'][1] - offset > 200:
        raise ValueError('CUB-200-2011 has only 200 class IDs')
    cached = root / 'data/sources/cub_200_2011/classes.txt'
    downloaded = classes_file is None
    path = Path(classes_file) if classes_file is not None else cached
    if not path.exists():
        if not downloaded:
            raise ValueError(f'Missing classes file: {path}')
        with urlopen(URL, timeout=30) as response:
            raw = response.read()
        # Validate before caching or modifying the live catalog.
        parse_classes(raw.decode('utf-8'))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    raw = path.read_bytes()
    if downloaded and hashlib.sha256(raw).hexdigest() != EXPECTED_SHA256:
        raise ValueError('Cached CUB classes differ from the pinned public distribution')
    classes = parse_classes(raw.decode('utf-8'))
    now = datetime.now(ZoneInfo('Asia/Seoul')).isoformat()
    source_id = source_id or 'classes_bird_cub'
    safe_id(source_id)
    destination = root / 'labels' / 'generated' / source_id
    if destination.exists() and source_id != 'classes_bird_cub':
        raise ValueError(f'Source run already exists: {source_id}')
    previous = load(root / 'catalog/classes/bird/list.yaml')
    previous_items = instance_items(previous, 'bird')
    old = {item['id']: item for item in previous_items}
    sources = load_sources(root)
    selected, items = {}, []
    for iid, index in zip(slots, range(declaration['indices'][0] - offset, declaration['indices'][1] + 1 - offset)):
        row = classes[index]
        if iid in old:
            has_binding = any(meta.get('provider') == declaration['source']
                              and iid in meta.get('class_mapping', {}) for meta in sources.values())
            if has_binding:
                old_class = source_binding(sources, declaration['source'], iid)
                if old_class != row:
                    raise ValueError(f'Existing ID has a different meaning: {iid}')
            elif (hashlib.sha256(raw).hexdigest() != EXPECTED_SHA256
                  or old[iid]['name'] != row['name']):
                raise ValueError(f'Cannot restore missing binding from pinned CUB input: {iid}')
        selected[iid] = row
        items.append({'id': iid, 'name': row['name']})
    items += [item for item in previous_items if item['id'] not in slots]
    # "classes" here is an ID-to-dataset-class map, not profile claims.
    metadata = {'id': source_id, 'provider': 'cub_200_2011', 'added_time': now,
                'script': declaration['script'], 'selection': declaration,
                'selection_rule': 'original_dataset_class_id_plus_catalog_offset', 'catalog_id_offset': offset,
                'dataset': 'Caltech-UCSD Birds-200-2011', 'project_url': PROJECT,
                'input': {'mode': 'public_mirror' if downloaded else 'local_classes_file',
                          'url': URL if downloaded else None,
                          'repository': REPOSITORY if downloaded else None,
                          'revision': REVISION if downloaded else None,
                          'filename': PATH, 'sha256': hashlib.sha256(raw).hexdigest()},
                'class_mapping': selected, 'available_classes': 200, 'selected_count': len(selected),
                'name_transform': 'remove numeric class prefix; replace underscores with spaces',
                'note': 'Class names only. No images, taxonomy, feature values or task judgments inferred.'}
    previous_source = {p.relative_to(destination): p.read_bytes() for p in destination.rglob('*') if p.is_file()}
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    try:
        write(destination / 'sources.json', metadata)
        (destination / 'raw').mkdir()
        (destination / 'raw/classes.txt').write_bytes(raw)
        write(root / 'catalog/classes/bird/list.yaml', instance_document('bird', sorted(items, key=lambda item: item['id'])))
        FileCatalog(root)
        record_script(root, 'cub', {'script': declaration['script'], 'classes': ['bird'],
                                  'instance_range': declaration['indices']}, category='catalog')
    except Exception:
        write(root / 'catalog/classes/bird/list.yaml', previous)
        shutil.rmtree(destination)
        for relative, content in previous_source.items():
            path = destination / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        raise
    return {'source': source_id, 'selected': len(selected), 'available': 200,
            'list': 'catalog/classes/bird/list.yaml'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--classes', type=Path, dest='classes_file')
    parser.add_argument('--source-id')
    args = parser.parse_args()
    import json
    try:
        print(json.dumps(collect(args.root, classes_file=args.classes_file, source_id=args.source_id), indent=2))
    except (ValueError, OSError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
