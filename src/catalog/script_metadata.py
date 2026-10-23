"""Record successful source preparation commands."""
import fcntl
from pathlib import Path
from .io import load, write


def record_script(root, name, details):
    root = Path(root)
    path = root / 'docs/assets/label_generation_scripts.json'
    lock_path = root / 'runs/locks/label_generation_scripts.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        records = load(path) if path.exists() else {}
        records[name] = details
        write(path, records)
