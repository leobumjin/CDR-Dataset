"""Prepare, publish, or download an explicitly versioned Hugging Face dataset."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

from evaluate import evaluate
from release import ROOT, verify

DEFAULT_REPO_ID = "leo-bjpark/CDR-Dataset"


def check_version(version):
    if not re.fullmatch(r'v[1-9][0-9]*', version):
        raise ValueError('Version must be v1, v2, v3, ...')


def prepare(version, repo_id=DEFAULT_REPO_ID):
    check_version(version)
    entry, manifest = verify(version)
    evaluation = evaluate(ROOT / entry['data'])
    destination = ROOT / 'runs/huggingface' / version
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Stage from verified files, not from an unrestricted working directory.
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        stage = Path(temporary)
        payload = stage / version
        shutil.copytree(ROOT / entry['data'], payload / 'data')
        metadata = payload / 'metadata'
        metadata.mkdir()
        (metadata / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        shutil.copy2(ROOT / 'versions' / version / 'statistics.json', metadata / 'statistics.json')
        shutil.copy2(ROOT / 'versions' / version / 'README.md', metadata / 'release-notes.md')
        (metadata / 'evaluation.json').write_text(json.dumps(evaluation, indent=2) + '\n')
        configs = [f'  - config_name: {version}', '    default: true',
                   '    data_files:', '      - split: all',
                   f'        path: {version}/data/labels/{entry["primary_teacher"]}/dataset.jsonl']
        card = '\n'.join(['---', 'language:', '  - en', 'tags:', '  - contextual-reasoning',
                          '  - belief-retraction', 'configs:', *configs, '---', '',
                          '# CDR-Dataset', '', 'Contextual Default Retraction Dataset', '',
                          'A dataset for evaluating contextual default reasoning and belief retraction in language models.', '',
                          f'Release: **{version}**. Teacher-generated references, not independently verified ground truth.', '',
                          'The `all` split contains all rows; use the `split` column to select train, revision-1, revision-2, or test.', '',
                          '```python', 'from datasets import load_dataset',
                          f'data = load_dataset("{repo_id}", "{version}", split="all")',
                          'train = data.filter(lambda row: row["split"] == "train")', '```', '',
                          f'See [release notes]({version}/metadata/release-notes.md), [statistics]({version}/metadata/statistics.json),',
                          f'and [evaluation]({version}/metadata/evaluation.json).', '',
                          'Generation code: https://github.com/leobumjin/CDR-Dataset',
                          'The manifest pins the matching pipeline files with SHA-256 hashes.', ''])
        (stage / 'README.md').write_text(card)
        # Validate the staged payload again to detect changes during copying.
        for name, checksum in manifest['files'].items():
            relative = Path(name).relative_to(entry['data']) if name.startswith(entry['data'] + '/') else None
            if relative is not None and hashlib.sha256((payload/'data'/relative).read_bytes()).hexdigest() != checksum:
                raise ValueError(f'Data changed during preparation: {name}')
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(stage, destination)
    return destination


def merge_cards(existing, incoming):
    """Keep other version configs and existing prose while updating one config."""
    import yaml

    def split_card(text):
        if text.startswith('---\n'):
            parts = text.split('\n---', 1)
            if len(parts) == 2:
                return yaml.safe_load(parts[0][4:]) or {}, parts[1].lstrip('\n')
        return {}, text

    old, old_body = split_card(existing)
    new, new_body = split_card(incoming)
    current = new['configs'][0]
    # Remove the previous teacher/default configs during migration to versions.
    configs = [c for c in old.get('configs', [])
               if c['config_name'] not in ('default', 'gpt-5.4', 'gpt-4o', current['config_name'])]
    configs.append(current)
    configs.sort(key=lambda c: (int(c['config_name'][1:]) if re.fullmatch(r'v[1-9][0-9]*', c['config_name']) else float('inf'), c['config_name']))
    default = next((c['config_name'] for c in configs if c.get('default') and c is not current), current['config_name'])
    for config in configs:
        config['default'] = config['config_name'] == default
    old.update({k: v for k, v in new.items() if k != 'configs'})
    old['configs'] = configs
    # Replace the old generated revision-based instructions on first migration.
    body = old_body if any(re.fullmatch(r'v[1-9][0-9]*', c.get('config_name', '')) for c in (split_card(existing)[0].get('configs', []))) else new_body
    return '---\n' + yaml.safe_dump(old, sort_keys=False, allow_unicode=True) + '---\n\n' + body


def upload(version, repo_id, public=True):
    stage = prepare(version, repo_id)
    from huggingface_hub import HfApi, hf_hub_download
    api = HfApi()
    api.create_repo(repo_id=repo_id, repo_type='dataset', private=not public, exist_ok=True)
    api.update_repo_settings(repo_id=repo_id, repo_type='dataset', private=not public)
    parent = api.repo_info(repo_id=repo_id, repo_type='dataset', revision='main').sha
    files = api.list_repo_files(repo_id=repo_id, repo_type='dataset', revision=parent)
    existing = ''
    if 'README.md' in files:
        existing = Path(hf_hub_download(repo_id=repo_id, repo_type='dataset', filename='README.md', revision=parent)).read_text()
    card = stage / 'README.md'
    card.write_text(merge_cards(existing, card.read_text()))
    result = api.upload_folder(repo_id=repo_id, repo_type='dataset', folder_path=str(stage),
                               revision='main', parent_commit=parent,
                               delete_patterns=[f'{version}/*'],
                               commit_message=f'Publish CDR-Dataset config {version}')
    receipt = {'repo_id': repo_id, 'version': version, 'config': version,
               'commit_sha': result.oid,
               'url': f'https://huggingface.co/datasets/{repo_id}/tree/main/{version}'}
    path = ROOT / 'versions' / version / 'huggingface.json'
    path.write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def download(version, repo_id):
    check_version(version)
    registry = json.loads((ROOT/'versions/registry.json').read_text())
    entry = registry['versions'][version]
    destination = ROOT / entry['data']
    if destination.exists():
        raise ValueError(f'Destination exists: {destination}; move it aside before downloading')
    from huggingface_hub import snapshot_download
    receipt_path = ROOT/'versions'/version/'huggingface.json'
    revision = "main"
    remote_prefix = version
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        if receipt['repo_id'] != repo_id:
            raise ValueError('Repository differs from the recorded release receipt')
        if receipt.get('config') == version:
            revision = receipt['commit_sha']
    snapshot = Path(snapshot_download(repo_id=repo_id, repo_type='dataset', revision=revision,
                                      allow_patterns=[f'{remote_prefix}/data/*', f'{remote_prefix}/metadata/manifest.json']))
    manifest = json.loads((ROOT/entry['manifest']).read_text())
    expected = {str(Path(n).relative_to(entry['data'])): h for n,h in manifest['files'].items()
                if n.startswith(entry['data']+'/')}
    payload = snapshot / remote_prefix / 'data'
    actual = {str(p.relative_to(payload)): p for p in payload.rglob('*') if p.is_file()}
    if set(actual) != set(expected):
        raise ValueError('Downloaded file inventory differs from local release manifest')
    for name, checksum in expected.items():
        if hashlib.sha256(actual[name].read_bytes()).hexdigest() != checksum:
            raise ValueError(f'Download checksum mismatch: {name}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(payload, destination)
    return str(destination)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # Shorthand: --version v1 means prepare the verified payload, then upload.
    if argv and argv[0].startswith('-') and argv[0] not in ('-h', '--help'):
        argv.insert(0, 'upload')
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog='Shortcut: bash shells/huggingface.sh --version v1 (prepare + upload). '
               'Add --dry-run for offline preparation only.')
    commands = parser.add_subparsers(dest='command')
    for name in ('prepare', 'upload', 'download'):
        sub = commands.add_parser(name)
        sub.add_argument('--version', required=True)
        sub.add_argument('--repo-id', default=os.getenv('HF_REPO_ID') or DEFAULT_REPO_ID,
                         help=f'HF dataset repository (default: {DEFAULT_REPO_ID})')
        if name == 'upload':
            sub.add_argument('--public', action='store_true', default=True, help='Publish publicly (default)')
            sub.add_argument('--dry-run', action='store_true', help='Offline preparation only; no network or upload')
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    try:
        check_version(args.version)
        if args.command == 'prepare' or (args.command == 'upload' and args.dry_run):
            print(f'Prepared locally: {prepare(args.version, args.repo_id)}')
            return 0
        if not args.repo_id or not re.fullmatch(r'[\w.-]+/[\w.-]+', args.repo_id):
            parser.error('Provide --repo-id leo-bjpark/CDR-Dataset or set HF_REPO_ID')
        if args.command == 'upload':
            print(json.dumps(upload(args.version, args.repo_id, args.public), indent=2))
        else:
            print(f'Downloaded: {download(args.version, args.repo_id)}')
    except (ValueError, KeyError, OSError, ImportError) as exc:
        parser.exit(1, f'{exc}\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
