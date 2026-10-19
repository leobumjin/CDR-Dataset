"""Verify or restore a registered, immutable dataset release; no API calls."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def verify(version, root=ROOT):
    registry = json.loads((root / 'versions/registry.json').read_text())
    entry = registry['versions'][version]
    manifest = json.loads((root / entry['manifest']).read_text())
    expected = manifest['files']
    actual = {str(p.relative_to(root)) for directory in (entry['data'], entry['pipeline'])
              for p in (root / directory).rglob('*')
              if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    if actual != set(expected):
        raise ValueError(f'File inventory mismatch: missing={set(expected)-actual}, extra={actual-set(expected)}')
    for name, checksum in expected.items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != checksum:
            raise ValueError(f'Checksum mismatch: {name}')
    return entry, manifest


def restore(version, output, root=ROOT):
    entry, _ = verify(version, root)
    output = Path(output).resolve()
    for folder in ('data', 'versions', 'shells', 'docs', '.git'):
        protected = (root / folder).resolve()
        if output == protected or protected in output.parents or output in protected.parents:
            raise ValueError('Restore destination overlaps repository source or release files')
    if output.exists():
        raise ValueError(f'Destination already exists: {output}')
    shutil.copytree(root / entry['data'], output)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['verify', 'restore'])
    parser.add_argument('version', help='Explicit release, e.g. v1')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'restore':
            if args.output is None:
                parser.error('restore requires --output')
            print(f'Restored {args.version}: {restore(args.version, args.output)}')
        else:
            _, manifest = verify(args.version)
            print(f"Verified {args.version}: {len(manifest['files'])} files")
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(1, f'{exc}\n')


if __name__ == '__main__':
    main()
