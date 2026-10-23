"""Explicit, immutable feature-sample source runs; old named runs are never inferred."""
import hashlib
from pathlib import Path
from .files import FORMAT, FileCatalog, safe_id
from .io import load, write
from .opinions import TASK_LABEL_SCHEMA, FEATURE_VALUE_SCHEMA, validate_feature_opinion


def checksums(directory):
    return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(directory).rglob('*')) if p.is_file() and p.suffix in ('.json', '.yaml', '.yml')}


def validate_encoding(samples, encoding):
    if not isinstance(encoding, dict):
        raise ValueError('feature_encoding must be a mapping')
    if encoding.get('type') == 'subjective_logic':
        for key in ('components', 'minimum', 'maximum', 'sum', 'sum_tolerance'):
            if encoding.get(key) != FEATURE_VALUE_SCHEMA[key]:
                raise ValueError('Invalid subjective-logic feature encoding')
        for entries in samples.values():
            for features in entries.values():
                for value in features.values():
                    validate_feature_opinion(value)
    allowed = encoding.get('values')
    if allowed is not None:
        if not isinstance(allowed, list) or not allowed:
            raise ValueError('Encoding values must be a nonempty list')
        for entries in samples.values():
            for features in entries.values():
                for value in features.values():
                    if not any(type(value) is type(v) and value == v for v in allowed):
                        raise ValueError('Feature value is outside source encoding')


class SourceRun:
    def __init__(self, root, source_id, *, catalog=None, _seen=()):
        self.root = Path(root)
        self.id = safe_id(source_id)
        if self.id in _seen:
            raise ValueError('Sample source reference cycle')
        self.directory = self.root / 'labels/generated' / self.id
        self.meta = load(self.directory / 'sources.json')
        if self.meta.get('id') != self.id or self.meta.get('format') != FORMAT:
            raise ValueError('Expected a feature_samples_v1 source; named legacy sources require explicit migration')
        if not (self.directory / 'catalog').is_dir():
            raise ValueError('Feature sources require frozen catalog definitions')
        self.catalog = FileCatalog(self.directory, catalog_version=self.meta.get('catalog_version', 'v1'))
        if self.meta.get('catalog_sha256') != checksums(self.directory / 'catalog'):
            raise ValueError('Source catalog checksum mismatch')
        if self.meta.get('status') != 'complete':
            raise ValueError('Source run is not complete')
        if not isinstance(self.meta.get('provenance'), dict) or not self.meta['provenance'].get('method'):
            raise ValueError('Source provenance requires a generation method')
        self.samples = {p.stem: load(p) for p in sorted((self.directory / 'samples').glob('*.json'))}
        reference = self.meta.get('sample_source')
        if reference:
            if self.samples:
                raise ValueError('Choose owned samples or an explicit sample_source, not both')
            parent = SourceRun(root, reference, catalog=self.catalog, _seen=(*_seen, self.id))
            if self.meta.get('sample_source_sha256') != checksums(parent.directory):
                raise ValueError('Sample source checksum mismatch')
            self.sample_provenance = parent.sample_provenance
            self.samples = parent.samples
            self.feature_encoding = self.meta.get('feature_encoding', parent.feature_encoding)
        if not self.samples or not any(self.samples.values()):
            raise ValueError('Source contains no samples')
        seen = set()
        for cid, entries in self.samples.items():
            self.catalog.validate_samples(cid, entries)
            if seen & entries.keys():
                raise ValueError('Sample IDs must be unique within a source')
            seen.update(entries)
        if not reference:
            self.sample_provenance = self.meta['provenance']
            self.feature_encoding = self.meta.get('feature_encoding', {})
        validate_encoding(self.samples, self.feature_encoding)
        self.tasks = {p.stem: load(p) for p in sorted((self.directory / 'tasks_per_context').glob('*.json'))}
        if self.tasks:
            if self.meta.get('task_label_schema') != TASK_LABEL_SCHEMA:
                raise ValueError('Task labels require the yes/no/unknown opinion schema')
            provenance = self.meta.get('label_provenance', {})
            if not provenance.get('method') or not provenance.get('review_status'):
                raise ValueError('Task labels require generation method and review status')
            if provenance['review_status'] == 'verified' and not provenance.get('evidence'):
                raise ValueError('Verified labels require evidence references')
        for tid, labels in self.tasks.items():
            self.catalog.validate_task_labels(tid, labels, self.samples)

    def stats(self):
        return {'id': self.id, 'samples': sum(map(len, self.samples.values())),
                'feature_values': sum(len(f) for entries in self.samples.values() for f in entries.values()),
                'task_labels': sum(len(v) for entries in self.tasks.values() for v in entries.values())}


def write_run(root, source_id, metadata, samples, tasks=None, extra=None, *, catalog_version='v1'):
    """Validate in isolation, then rename into place without replacing existing runs."""
    import shutil
    import tempfile
    root = Path(root)
    destination = root / 'labels/generated' / safe_id(source_id)
    if destination.exists():
        raise ValueError(f'Source run already exists: {source_id}; choose a new ID')
    staging = Path(tempfile.mkdtemp(prefix='cdr-source-'))
    try:
        selected_catalog = (SourceRun(root, metadata['sample_source']).catalog if metadata.get('sample_source')
                            else FileCatalog(root, catalog_version=catalog_version))
        shutil.copytree(selected_catalog.directory, staging / 'catalog')
        if metadata.get('sample_source'):
            # Resolve references from the original tree; validation below checks exact hashes.
            reference = metadata['sample_source']
            seen = set()
            while reference:
                if reference in seen:
                    raise ValueError('Sample source reference cycle')
                seen.add(reference)
                safe_id(reference)
                original = root / 'labels/generated' / reference
                shutil.copytree(original, staging / 'labels/generated' / reference)
                reference = load(original / 'sources.json').get('sample_source')
        run = staging / 'labels/generated' / source_id
        definitions = (staging / 'labels/generated' / metadata['sample_source'] / 'catalog'
                       if metadata.get('sample_source') else selected_catalog.directory)
        shutil.copytree(definitions, run / 'catalog')
        write(run / 'sources.json', {**metadata, 'id': source_id, 'format': FORMAT,
                                     'catalog_sha256': checksums(run / 'catalog'),
                                     'catalog_version': (load(staging / 'labels/generated' / metadata['sample_source'] / 'sources.json')['catalog_version']
                                                         if metadata.get('sample_source') else catalog_version),
                                     'task_label_schema': TASK_LABEL_SCHEMA})
        for cid, entries in samples.items():
            write(run / 'samples' / f'{safe_id(cid)}.json', entries)
        for tid, entries in (tasks or {}).items():
            write(run / 'tasks_per_context' / f'{safe_id(tid)}.json', entries)
        for filename, body in (extra or {}).items():
            write(run / safe_id(filename), body)
        SourceRun(staging, source_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Copy to a sibling before the final atomic rename (tmp may be another filesystem).
        sibling = Path(tempfile.mkdtemp(prefix='.source-', dir=destination.parent))
        try:
            shutil.copytree(run, sibling, dirs_exist_ok=True)
            import fcntl
            with (destination.parent / '.write.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                if destination.exists():
                    raise ValueError(f'Source run already exists: {source_id}')
                sibling.rename(destination)
        finally:
            if sibling.exists():
                shutil.rmtree(sibling)
    finally:
        shutil.rmtree(staging)
    return SourceRun(root, source_id)
