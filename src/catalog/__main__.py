import argparse
import json
from pathlib import Path
from .files import FileCatalog


def main():
    parser = argparse.ArgumentParser(description='CDR file catalogs')
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('stats', 'validate'):
        sub.add_parser(name)
    sub.add_parser('annotate').add_argument('input', type=Path)
    p = sub.add_parser('feature-sources')
    p.add_argument('class_id')
    p.add_argument('--output', type=Path)
    args = parser.parse_args()
    catalog = FileCatalog(args.root)
    if args.command == 'feature-sources':
        result = catalog.feature_sources(args.class_id)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
            result = {'output': str(args.output)}
    elif args.command == 'annotate':
        result = catalog.append_label(json.loads(args.input.read_text()))
    else:
        result = catalog.stats()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
