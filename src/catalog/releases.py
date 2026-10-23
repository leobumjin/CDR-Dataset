"""Freeze explicit feature samples and optional task labels into releases."""
import argparse
import json
from pathlib import Path
from .files import FORMAT, FileCatalog, safe_id
from .io import load, write
from .opinions import TASK_LABEL_SCHEMA
from .sample_sources import SourceRun, checksums, validate_encoding


def read_releases(root):
    result = {}
    for path in sorted((Path(root) / 'releases').glob('*/meta_info.json')):
        meta = load(path)
        if meta.get('id') != path.parent.name:
            raise ValueError('Release directory/ID mismatch')
        safe_id(meta['id'])
        if meta.get('format') != FORMAT:
            raise ValueError('Releases require format feature_samples_v1')
        if any(key in meta for key in ('type', 'synthetic_release', 'real_feature_sources', 'instance_range')):
            raise ValueError('Feature releases have no N/R/R2 family or named instance range')
        if meta.get('status') not in ('planned', 'in_progress', 'ready', 'released'):
            raise ValueError('Invalid release status')
        if not isinstance(meta.get('classes'), list) or not meta['classes']:
            raise ValueError('Release requires explicit feature groups')
        if meta['status'] in ('ready', 'released'):
            for key in ('catalog_commit', 'source_checksums', 'definition_snapshot'):
                if not meta.get(key):
                    raise ValueError(f'Release requires {key}')
            read_snapshot(root, meta)
        result[meta['id']] = meta
    return result


def read_snapshot(root, meta):
    directory = Path(root) / 'releases' / safe_id(meta['id'])
    # Validate against frozen definitions, not later changes to the live catalog.
    catalog = FileCatalog(directory)
    samples = {p.stem: load(p) for p in sorted((directory / 'samples').glob('*.json'))}
    if set(samples) != set(meta['classes']) or not any(samples.values()):
        raise ValueError('Release sample groups do not match metadata')
    all_ids = set()
    for cid, entries in samples.items():
        catalog.validate_samples(cid, entries)
        if all_ids & entries.keys():
            raise ValueError('Duplicate release sample IDs')
        all_ids.update(entries)
    validate_encoding(samples, meta.get('feature_encoding', {}))
    tasks = {p.stem: load(p) for p in sorted((directory / 'labels/tasks_per_context').glob('*.json'))}
    if tasks and meta.get('task_label_schema') != TASK_LABEL_SCHEMA:
        raise ValueError('Release task labels require the yes/no/unknown opinion schema')
    if tasks and not meta.get('label_provenance'):
        raise ValueError('Release task labels require provenance')
    for tid, labels in tasks.items():
        catalog.validate_task_labels(tid, labels, samples)
    if meta.get('artifact_checksums') != checksums_for_snapshot(directory):
        raise ValueError('Release artifact checksum mismatch')
    return samples, tasks


def checksums_for_snapshot(directory):
    import hashlib
    return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('samples', 'labels', 'catalog')
            for p in sorted((directory / folder).rglob('*')) if p.is_file()}


def assemble(root, release_id, sample_source, *, label_sources=(), catalog_commit):
    """Create a local frozen release; never overwrite or publish it."""
    import shutil
    import tempfile
    root = Path(root)
    release_id = safe_id(release_id)
    destination = root / 'releases' / release_id
    def check_destination():
        if destination.exists() and (
                not destination.is_dir() or
                any(p.name not in {'scripts', 'shells'} or not p.is_dir()
                    or p.is_symlink() for p in destination.iterdir())):
            raise ValueError('Release already exists; choose a new ID')
    check_destination()
    if not isinstance(catalog_commit, str) or not catalog_commit.strip():
        raise ValueError('Provide the catalog commit explicitly')
    sample_run = SourceRun(root, sample_source)
    tasks = {}
    provenance = {}
    sources = {sample_source: checksums(sample_run.directory)}
    for sid in label_sources:
        run = SourceRun(root, sid)
        if run.meta['catalog_sha256'] != sample_run.meta['catalog_sha256']:
            raise ValueError('Label and sample source definitions do not match')
        if run.samples != sample_run.samples:
            raise ValueError('Label source sample vectors do not match the selected samples')
        sources[sid] = checksums(run.directory)
        if not run.meta.get('label_provenance'):
            raise ValueError('Task labels require label_provenance')
        provenance[sid] = run.meta['label_provenance']
        for tid, labels in run.tasks.items():
            for sample_id, judgments in labels.items():
                output = tasks.setdefault(tid, {}).setdefault(sample_id, {})
                if output.keys() & judgments.keys():
                    raise ValueError('Overlapping task labels; select one result explicitly')
                output.update(judgments)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.release-', dir=destination.parent))
    try:
        shutil.copytree(sample_run.directory / 'catalog', staging / 'catalog')
        for cid, entries in sample_run.samples.items():
            write(staging / 'samples' / f'{cid}.json', entries)
        for tid, labels in tasks.items():
            write(staging / 'labels/tasks_per_context' / f'{tid}.json', labels)
        metadata = {'id': release_id, 'format': FORMAT, 'status': 'released',
                    'catalog_version': sample_run.meta['catalog_version'],
                    'classes': sorted(sample_run.samples), 'catalog_commit': catalog_commit,
                    'definition_snapshot': 'catalog/', 'sample_source': sample_source,
                    'source_checksums': sources,
                    'feature_encoding': sample_run.feature_encoding,
                    'sample_provenance': sample_run.sample_provenance,
                    'task_label_schema': TASK_LABEL_SCHEMA,
                    'label_provenance': provenance,
                    'artifact_checksums': checksums_for_snapshot(staging)}
        write(staging / 'meta_info.json', metadata)
        # Reserve the target with a lock to avoid concurrent overwrites.
        import fcntl
        with (destination.parent / '.write.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            check_destination()
            if destination.exists():
                # Code may precede the snapshot. Publish metadata last so readers
                # discover only the completed release; keep code untouched.
                installed = []
                try:
                    for artifact in sorted(staging.iterdir(), key=lambda p: p.name == 'meta_info.json'):
                        target = destination / artifact.name
                        artifact.rename(target)
                        installed.append(target)
                except Exception:
                    for target in reversed(installed):
                        target.rename(staging / target.name)
                    raise
            else:
                staging.rename(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return metadata


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    p.add_argument('--release-id', required=True)
    p.add_argument('--sample-source', required=True)
    p.add_argument('--label-sources', nargs='*', default=[])
    p.add_argument('--catalog-commit', required=True)
    a = p.parse_args()
    print(json.dumps(assemble(a.root, a.release_id, a.sample_source,
                              label_sources=a.label_sources, catalog_commit=a.catalog_commit), indent=2))


if __name__ == '__main__':
    main()
