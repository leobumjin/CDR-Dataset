import argparse
import json
from pathlib import Path
from .files import FileCatalog
from .releases import read_releases
from .sample_sources import SourceRun


def main():
    p = argparse.ArgumentParser(description='CDR feature definitions and anonymous sample sources')
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    p.add_argument('--catalog-version', default='v1')
    sub = p.add_subparsers(dest='command', required=True)
    for name in ('stats', 'validate', 'releases'):
        sub.add_parser(name)
    sub.add_parser('source').add_argument('source_id')
    a = p.parse_args()
    catalog = FileCatalog(a.root, catalog_version=a.catalog_version)
    if a.command == 'releases':
        result = read_releases(a.root)
    elif a.command == 'source':
        result = SourceRun(a.root, a.source_id, catalog=catalog).stats()
    else:
        if a.command == 'validate':
            read_releases(a.root)
        result = catalog.stats()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
