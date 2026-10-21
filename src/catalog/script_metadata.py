"""Record successful generation scripts for the website."""
import fcntl
from pathlib import Path
from .io import load, write
from .web_assets import export_catalog


def record_script(root, name, details, *, category):
    root = Path(root)
    if category not in ('catalog', 'label'):
        raise ValueError('Unknown script metadata category')
    path = root / f'docs/assets/{category}_generation_scripts.json'
    lock_path = root / f'runs/locks/{category}_generation_scripts.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        records = load(path) if path.exists() else {}
        if category == 'catalog':
            export_catalog(root)
        records[name] = details
        write(path, records)
