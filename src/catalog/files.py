"""Catalog definitions, independent of sample identities and source runs."""
import json
import re
from pathlib import Path
from .io import load
from .opinions import validate_opinion

FORMAT = 'feature_samples_v1'


def safe_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', value):
        raise ValueError(f'Invalid ID: {value!r}')
    return value


def unique(items, key, what):
    result = {}
    for item in items:
        identifier = key(item)
        if identifier in result:
            raise ValueError(f'Duplicate {what}: {identifier}')
        result[identifier] = item
    return result


class FileCatalog:
    def __init__(self, root='.', catalog_version='v1'):
        self.root = Path(root)
        self.version = safe_id(catalog_version)
        if not re.fullmatch(r'v[1-9][0-9]*', self.version):
            raise ValueError('Catalog versions must use v1, v2, v3, ...')
        base = self.root / 'catalog'
        self.directory = base if (base / 'classes').is_dir() else base / self.version
        if not (self.directory / 'classes').is_dir() or not (self.directory / 'tasks').is_dir():
            raise ValueError(f'Catalog version not found: {self.version}')
        self.classes, self.features, self.tasks, self.contexts = {}, {}, {}, {}
        for path in sorted((self.directory / 'classes').glob('*.yaml')):
            c = load(path)
            cid = safe_id(c['id'])
            if cid != path.stem:
                raise ValueError('Class directory/ID mismatch')
            if any(k in c for k in ('instances', 'collections', 'collection', 'grounding', 'feature_value_schema')):
                raise ValueError('Classes define feature groups, not named objects or value encodings')
            part = c
            if not isinstance(part.get('features'), dict):
                raise ValueError('Classes require an ID-keyed features mapping')
            features = []
            for fid, spec in part['features'].items():
                if not isinstance(fid, str) or not re.fullmatch(re.escape(cid) + r'_f_[0-9]{3}', fid) or int(fid.rsplit('_', 1)[1]) < 1:
                    raise ValueError('Feature keys must use the class_f_001 format')
                if not isinstance(spec, dict):
                    raise ValueError('Invalid feature definition')
                for key in ('name', 'description'):
                    if not isinstance(spec.get(key), str) or not spec[key].strip():
                        raise ValueError(f'Feature definition requires a {key}')
                if any(k in spec for k in ('id', 'revision', 'grounding', 'values', 'type', 'possible_values')):
                    raise ValueError('Feature definitions describe meaning; put value encodings in source metadata')
                feature = {'id': fid, **spec}
                features.append(feature)
                self.features[cid, fid] = feature
            unique(features, lambda f: f['name'], 'feature names')
            self.classes[cid] = {**c, 'features': features}
        for path in sorted((self.directory / 'tasks').glob('*.yaml')):
            task = load(path)
            tid = safe_id(task['id'])
            if tid != path.stem:
                raise ValueError('Task directory/ID mismatch')
            definitions = task.get('contexts')
            if not isinstance(definitions, dict):
                raise ValueError('Tasks require an ID-keyed contexts mapping')
            for ctxid, spec in definitions.items():
                safe_id(ctxid)
                if (not isinstance(spec, dict) or set(spec) != {'description'}
                        or not isinstance(spec['description'], str) or not spec['description'].strip()):
                    raise ValueError('Contexts require only a nonempty description')
            bindings = unique(task['bindings'], lambda b: b['class_id'], 'task/class binding')
            if not set(bindings) <= self.classes.keys():
                raise ValueError('Unknown bound class')
            used = set()
            for cid, binding in bindings.items():
                if len(bindings) > 1 and 'contexts' not in binding:
                    raise ValueError('Multi-class tasks require explicit context IDs')
                selected = binding.get('contexts', list(definitions))
                if not isinstance(selected, list) or len(set(selected)) != len(selected) or not set(selected) <= definitions.keys():
                    raise ValueError('Invalid task binding contexts')
                for ctxid in selected:
                    self.contexts[tid, cid, ctxid] = {'id': ctxid, **definitions[ctxid]}
                used.update(selected)
            if used != definitions.keys():
                raise ValueError('Unbound context definitions')
            self.tasks[tid] = task

    def validate_samples(self, cid, samples):
        if cid not in self.classes or not isinstance(samples, dict):
            raise ValueError('Samples require a known class and sample-ID mapping')
        for sample_id, features in samples.items():
            safe_id(sample_id)
            if not isinstance(features, dict) or not features:
                raise ValueError('A sample must contain feature values')
            for fid, value in features.items():
                if (cid, fid) not in self.features:
                    raise ValueError(f'Unknown feature: {cid}/{fid}')
                if value is None:
                    raise ValueError('Missing features must be absent keys, not null')
                # No implicit numeric scale, boolean encoding or bounds.
                try:
                    json.dumps(value, allow_nan=False)
                except (ValueError, TypeError) as error:
                    raise ValueError('Feature values must be finite JSON data') from error

    def validate_task_labels(self, tid, labels, samples):
        if tid not in self.tasks or not isinstance(labels, dict):
            raise ValueError('Task labels require a known task and sample-ID mapping')
        owners = {}
        for cid, entries in samples.items():
            for sample_id in entries:
                if sample_id in owners:
                    raise ValueError('Sample IDs must be unique within a source or release')
                owners[sample_id] = cid
        for sample_id, values in labels.items():
            if sample_id not in owners or not isinstance(values, dict):
                raise ValueError(f'Unknown sample/value mapping: {sample_id}')
            for ctxid, value in values.items():
                if (tid, owners[sample_id], ctxid) not in self.contexts:
                    raise ValueError('Unknown or unbound task/context')
                validate_opinion(value)

    def stats(self):
        return {'classes': len(self.classes), 'features': len(self.features),
                'tasks': len(self.tasks), 'contexts': len(self.contexts)}
