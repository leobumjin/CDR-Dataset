"""Generate the authored 1..100 instance slots for the five classes.

The checked-in seeds are curated examples, not observations or feature labels.
No v1 data is read at runtime. Re-running preserves the external-source slots.
"""
import argparse
import json
from pathlib import Path
from .io import load, write, instance_items, instance_document
from .script_metadata import record_script
from .files import FileCatalog


def generate(root):
    root = Path(root)
    seeds = load(Path(__file__).with_name('manual_instances.yaml'))
    prepared = {}
    for cid, seed in seeds.items():
        if 'names' in seed:
            names = seed['names']
        elif cid == 'human':
            names = [f'{role} {situation}' for role in seed['roles'] for situation in seed['situations']]
        else:
            names = [f'{action} {situation}' for action in seed['actions'] for situation in seed['situations']]
        if len(names) != 100 or len(set(names)) != 100:
            raise ValueError(f'{cid} requires 100 distinct authored names')
        path = root / f'catalog/classes/{cid}/list.yaml'
        old = instance_items(load(path), cid) if path.exists() else []
        items = [{'id': f'{cid}_{n:04}', 'name': name} for n, name in enumerate(names, 1)]
        items += [item for item in old if int(item['id'].rsplit('_', 1)[-1]) > 100]
        prepared[path] = instance_document(cid, sorted(items, key=lambda item: item['id']))
    previous = {p: p.read_bytes() if p.exists() else None for p in prepared}
    try:
        for path, document in prepared.items():
            write(path, document)
        FileCatalog(root)
        record_script(root, 'manual', {'script': 'shells/catalog/manual.sh',
                                     'classes': sorted(seeds), 'instance_range': [1, 100]}, category='catalog')
    except Exception:
        for path, raw in previous.items():
            if raw is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(raw)
        raise
    return {cid: 100 for cid in seeds}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    print(json.dumps(generate(args.root), indent=2))


if __name__ == '__main__':
    main()
