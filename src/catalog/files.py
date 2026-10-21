"""YAML catalog definitions and source-run JSON result histories."""
import fcntl
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from .io import load, write, instance_items
from .ranges import reserved_ids
from .sources import source_binding


def unique(items, key, what):
    result = {}
    for item in items:
        id = key(item)
        if id in result:
            raise ValueError(f'Duplicate {what}: {id}')
        result[id] = item
    return result


def safe_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', value):
        raise ValueError(f'Invalid directory ID: {value!r}')
    return value


class FileCatalog:
    def __init__(self, root='.'):
        self.root = Path(root)
        self.directory = self.root / 'catalog'
        self.sources = {}
        for directory in sorted((self.root / 'labels' / 'generated').glob('*/')):
            sid = safe_id(directory.name)
            meta = load(directory / 'sources.json')
            if meta['id'] != sid:
                raise ValueError('Source directory/ID mismatch')
            self.sources[sid] = meta
        self.classes, self.instances, self.features, self.contexts = {}, {}, {}, {}
        for list_path in sorted((self.directory / 'classes').glob('*/list.yaml')):
            directory = list_path.parent
            cid = safe_id(directory.name)
            items = instance_items(load(directory / 'list.yaml'), cid)
            info_path = directory / 'class.yaml'
            c = load(info_path) if info_path.exists() else {'id': cid, 'name': cid, 'revision': 1}
            if c['id'] != cid:
                raise ValueError('Class directory/ID mismatch')
            declarations = c.get('collections', [c['collection']] if 'collection' in c else [])
            registry = {}
            for declaration in declarations:
                scoped = {**declaration, 'identifiers': {'prefix': cid + '_', 'digits': 4}}
                slots = reserved_ids(scoped)
                if set(registry) & set(slots):
                    raise ValueError('Overlapping collection indices')
                registry.update(slots)
                for item in items:
                    if item['id'] not in slots:
                        continue
                    provider = declaration['source']
                    if provider == 'conceptnet':
                        saved = source_binding(self.sources, provider, item['id'])
                        if not saved.get('uri'):
                            raise ValueError(f'ConceptNet binding mismatch: {item["id"]}')
                        registry[item['id']]['concept_uri'] = saved['uri']
                    elif provider == 'cub_200_2011':
                        row = source_binding(self.sources, provider, item['id'])
                        offset = declaration['indices'][0] - 1 if 'collections' in c else 0
                        if row.get('name') != item['name'] or row.get('class_id') != int(item['id'].rsplit('_', 1)[-1]) - offset:
                            raise ValueError(f'CUB dataset class mapping mismatch: {item["id"]}')
            if declarations:
                c['instance_registry'] = registry
                if any(item['id'] not in registry for item in items):
                    raise ValueError('List ID is outside class.yaml indices')
            revisions = c.get('instance_revisions', {})
            if not set(revisions) <= {i['id'] for i in items}:
                raise ValueError('Unknown instance revision ID')
            c['instances'] = [{**item, 'class': cid, 'revision': revisions.get(item['id'], 1)} for item in items]
            part = load(directory / 'features.yaml')
            if part['class_id'] != cid:
                raise ValueError('Feature class mismatch')
            if not isinstance(part['features'], dict):
                raise ValueError('features.yaml features must be keyed by feature ID')
            c['features'] = []
            for fid, spec in part['features'].items():
                if not isinstance(fid, str) or not fid or not isinstance(spec, dict):
                    raise ValueError('Invalid feature definition')
                feature_id = fid
                if (not re.fullmatch(re.escape(cid) + r'_f_[0-9]{3}', feature_id)
                        or int(feature_id.rsplit('_', 1)[-1]) < 1):
                    raise ValueError('Feature keys must use the class_f_001 format')
                if not isinstance(spec.get('name'), str) or not spec['name'].strip():
                    raise ValueError('Feature definition requires a name')
                if not isinstance(spec.get('description'), str) or not spec['description'].strip():
                    raise ValueError('Feature definition requires a description')
                if any(k in spec for k in ('id', 'feature_id', 'revision', 'possible_values')):
                    raise ValueError('Use the feature ID as key and name/description as fields')
                if 'values' in spec and (not isinstance(spec['values'], list) or not spec['values']):
                    raise ValueError('Feature values must be a nonempty list')
                c['features'].append({**spec, 'id': feature_id, 'revision': 1})
            unique(c['features'], lambda feature: feature['name'], 'feature names')
            self._revisions([c, *c['instances'], *c['features']])
            self.classes[cid] = c
            for field, target in [('instances', self.instances), ('features', self.features)]:
                for id, item in unique(c[field], lambda x: x['id'], field).items():
                    target[cid, id] = item
        self.tasks = unique([load(p) for p in sorted((self.directory / 'tasks').glob('*/task.yaml'))],
                            lambda x: x['id'], 'task')
        for tid, task in self.tasks.items():
            safe_id(tid)
            self._revisions([task])
            bindings = unique(task['bindings'], lambda x: x['class_id'], 'task/class binding')
            if not set(bindings) <= set(self.classes):
                raise ValueError(f'Unknown bound class: {tid}')
            ctx = load(self.directory / 'tasks' / tid / 'contexts.yaml')
            if ctx['task_id'] != tid:
                raise ValueError('Context file task mismatch')
            definitions = ctx['contexts']
            if not isinstance(definitions, dict):
                raise ValueError('Contexts must be keyed by context ID')
            for context_id, spec in definitions.items():
                safe_id(context_id)
                if (not isinstance(spec, dict) or set(spec) != {'description'}
                        or not isinstance(spec['description'], str) or not spec['description'].strip()):
                    raise ValueError('Contexts require only a nonempty description')
            used = set()
            for cid, binding in bindings.items():
                if len(bindings) > 1 and 'contexts' not in binding:
                    raise ValueError('Multi-class tasks require context IDs in each binding')
                selected = binding.get('contexts', list(definitions))
                if not isinstance(selected, list) or len(selected) != len(set(selected)) or not set(selected) <= set(definitions):
                    raise ValueError('Invalid task binding contexts')
                for context_id in selected:
                    self.contexts[tid, cid, context_id] = {
                        'id': context_id, 'class_id': cid, 'revision': 1, **definitions[context_id]}
                used.update(selected)
            if used != set(definitions):
                raise ValueError('Unbound context definitions')
        # Source-specific profile claims stay in sources.json; do not implicitly
        # choose a source's state/attributes or labels for a catalog instance.
        for sid, meta in self.sources.items():
            for cid, profile in meta.get('classes', {}).items():
                if cid not in self.classes:
                    raise ValueError(f'Unknown source profile class: {cid}')
                if any((cid, iid) not in self.instances for iid in profile.get('instances', {})):
                    raise ValueError(f'Unknown source profile instance: {sid}/{cid}')
        self.groups = {}
        for sid in self.sources:
            for path in sorted((self.root / 'labels' / 'generated' / sid / 'groups').glob('*.json')):
                cid = path.stem
                if cid not in self.classes:
                    raise ValueError('Unknown group class')
                groups = load(path)
                self.validate_groups(groups)
                self.groups[sid, cid] = groups
        self.labels = {}
        for sid in self.sources:
            for category in ('features', 'tasks_per_context'):
                for path in sorted((self.root / 'labels' / 'generated' / sid / category).glob('*.json')):
                    records = load(path)
                    if isinstance(records, dict):
                        records = self.expand_values(sid, category, path.stem, records)
                    elif not isinstance(records, list):
                        raise ValueError('Labels must map instance IDs to feature/context values')
                    for label in records:
                        if label['id'] in self.labels:
                            raise ValueError(f'Duplicate label ID: {label["id"]}')
                        if label.get('source') != sid or path != self.label_path(label):
                            raise ValueError('Label source or file path mismatch')
                        self.labels[label['id']] = label
        for label in self.labels.values():
            self.validate_label(label)
            seen, current = set(), label
            while current.get('supersedes'):
                if current['id'] in seen:
                    raise ValueError('Label supersedes cycle')
                seen.add(current['id'])
                current = self.labels[current['supersedes']]

    def expand_values(self, sid, category, owner, mapping):
        """Resolve compact on-disk values into the internal validation view."""
        meta = self.sources[sid]
        synthetic = meta.get('provider') == 'random' and meta.get('synthetic') is True
        records = []
        for iid, values in mapping.items():
            classes = [cid for cid, instance_id in self.instances if instance_id == iid]
            if len(classes) != 1 or not isinstance(values, dict):
                raise ValueError(f'Unknown or ambiguous instance/value mapping: {iid}')
            cid = classes[0]
            if category == 'features' and cid != owner:
                raise ValueError('Feature file class mismatch')
            for key, value in values.items():
                record = {'id': f'{sid}:{category}:{owner}:{iid}:{key}', 'source': sid,
                          'class_id': cid, 'instance_id': iid,
                          'instance_revision': self.instances[cid, iid]['revision'],
                          'layer': 'template' if synthetic else meta.get('layer', 'reference'),
                          'status': meta.get('status', 'proposed'),
                          'created_at': meta.get('created_at', 'source-run'),
                          'provenance': meta.get('provenance', {
                              'method': 'random' if synthetic else meta.get('provider', 'source'),
                              'agent': meta.get('script', sid)}), 'value': value}
                if category == 'features':
                    if (cid, key) not in self.features:
                        raise ValueError(f'Unknown feature: {cid}/{key}')
                    record.update(kind='feature', feature_id=key,
                                  feature_revision=self.features[cid, key]['revision'])
                else:
                    if owner not in self.tasks or (owner, cid, key) not in self.contexts:
                        raise ValueError(f'Unknown task/context: {owner}/{cid}/{key}')
                    record.update(kind='judgment', task_id=owner, context_id=key,
                                  task_revision=self.tasks[owner]['revision'],
                                  context_revision=self.contexts[owner, cid, key]['revision'])
                records.append(record)
        return records

    @staticmethod
    def _revisions(items):
        for item in items:
            if type(item['revision']) is not int or item['revision'] < 1:
                raise ValueError('Revision must be a positive integer')

    @staticmethod
    def validate_groups(groups):
        if not isinstance(groups, dict):
            raise ValueError('Group results must map item IDs to membership lists')
        for item, memberships in groups.items():
            if not isinstance(item, str) or not item or not isinstance(memberships, list):
                raise ValueError('Invalid group membership mapping')
            seen = set()
            for membership in memberships:
                if not isinstance(membership, dict) or not isinstance(membership.get('group_id'), str):
                    raise ValueError('Each membership requires group_id')
                group = membership['group_id']
                if group not in groups or group in seen:
                    raise ValueError(f'Unknown or duplicate group: {group}')
                seen.add(group)
        visited = set()
        def visit(item, path):
            if item in path:
                raise ValueError(f'Group membership cycle: {item}')
            if item in visited:
                return
            for membership in groups[item]:
                visit(membership['group_id'], path | {item})
            visited.add(item)
        for item in groups:
            visit(item, set())

    def label_path(self, label):
        sid = safe_id(label['source'])
        if sid not in self.sources:
            raise ValueError(f'Unknown source: {sid}')
        if label['kind'] == 'feature' and label['class_id'] in self.classes:
            return self.root / 'labels' / 'generated' / sid / 'features' / f"{label['class_id']}.json"
        if label['kind'] == 'judgment' and label['task_id'] in self.tasks:
            return self.root / 'labels' / 'generated' / sid / 'tasks_per_context' / f"{label['task_id']}.json"
        raise ValueError('Unknown label kind, class or task')
    @staticmethod
    def subject(label):
        fields = ['kind', 'class_id', 'instance_id', 'instance_revision', 'layer']
        fields += (['feature_id', 'feature_revision'] if label['kind'] == 'feature'
                   else ['task_id', 'task_revision', 'context_id', 'context_revision'])
        return tuple(label[k] for k in fields)

    def validate_label(self, label, *, current_only=False):
        self.label_path(label)
        if not label.get('id') or not label.get('layer') or not label.get('created_at'):
            raise ValueError('Label requires id, layer and created_at')
        cid = label['class_id']
        def reference(records, key, revision):
            if key not in records or type(revision) is not int or revision < 1 or revision > records[key]['revision']:
                raise ValueError(f'Unknown record/revision: {key}@{revision}')
            if current_only and revision != records[key]['revision']:
                raise ValueError('New labels must reference current definitions')
        reference(self.instances, (cid, label['instance_id']), label['instance_revision'])
        if label['kind'] == 'feature':
            key = cid, label['feature_id']
            reference(self.features, key, label['feature_revision'])
            # Historical revisions remain audit records. Only compare current
            # values against the current definition's permitted values.
            definition = self.features[key]
            source = self.sources[label['source']]
            synthetic_template = (source.get('provider') == 'random' and source.get('synthetic') is True
                                  and source.get('purpose') == 'template' and label['layer'] == 'template'
                                  and label['status'] == 'proposed'
                                  and label.get('provenance', {}).get('method') == 'random')
            if synthetic_template:
                definition = {'revision': definition['revision'], 'values': source['feature_values']}
            if 'values' not in definition and 'type' not in definition:
                raise ValueError('Feature value schema is not configured; define values or type before labeling')
            if label['feature_revision'] == definition['revision']:
                value = label['value']
                if value is None:
                    if not definition.get('nullable', False):
                        raise ValueError('This feature does not allow an explicit unknown value')
                else:
                    # Compare both type and value: Python otherwise treats 1,
                    # 1.0 and True as equivalent members of an enumeration.
                    if 'values' in definition and not any(type(value) is type(v) and value == v for v in definition['values']):
                        raise ValueError('Feature value is outside values')
                    if definition.get('type') == 'boolean' and type(value) is not bool:
                        raise ValueError('Feature value must be true or false, not a numeric judgment')
                    if definition.get('type') == 'number':
                        if type(value) not in (int, float) or not math.isfinite(value):
                            raise ValueError('Feature value must be a finite number')
                        if 'minimum' in definition and value < definition['minimum']:
                            raise ValueError('Feature value is below minimum')
                    if definition.get('type') == 'string' and not isinstance(value, str):
                        raise ValueError('Feature value must be a string')
        else:
            reference(self.tasks, label['task_id'], label['task_revision'])
            reference(self.contexts, (label['task_id'], cid, label['context_id']), label['context_revision'])
            if label['value'] not in ('true', 'false', 'ambiguous'):
                raise ValueError('Invalid judgment value')
        if label['status'] not in {'imported', 'proposed', 'fact_checked', 'disputed', 'retracted'}:
            raise ValueError('Invalid review status')
        p = label['provenance']
        if not p.get('method') or not p.get('agent'):
            raise ValueError('Provenance requires method and agent')
        if label['status'] == 'fact_checked' and (not p.get('evidence') or not p.get('checked_at')):
            raise ValueError('fact_checked requires evidence and checked_at')
        previous = label.get('supersedes')
        if previous and (previous not in self.labels or self.subject(self.labels[previous]) != self.subject(label)):
            raise ValueError('supersedes must reference the same subject revision and layer')

    def append_label(self, label):
        return self.append_labels([label])[0]

    def append_labels(self, labels):
        labels = [dict(label) for label in labels]
        for label in labels:
            label.setdefault('id', str(uuid4()))
            label.setdefault('created_at', datetime.now(timezone.utc).isoformat())
        directory = self.root / 'labels' / 'generated'
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / '.write.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            current = FileCatalog(self.root)
            for label in labels:
                current.validate_label(label, current_only=True)
                if label['id'] in current.labels:
                    raise ValueError('Label ID already exists; use a new ID for an update')
                json.dumps(label, allow_nan=False)
                current.labels[label['id']] = label
            by_path = {}
            for label in labels:
                by_path.setdefault(current.label_path(label), []).append(label)
            for path, records in by_path.items():
                previous = load(path) if path.exists() else []
                if isinstance(previous, dict):
                    raise ValueError('Compact source runs are snapshots; create a new source run for updates')
                write(path, previous + records)
            self.labels = current.labels
        return labels

    def feature_sources(self, class_id):
        if class_id not in self.classes:
            raise ValueError('Unknown class')
        result = {}
        for label in self.labels.values():
            if label['kind'] == 'feature' and label['class_id'] == class_id:
                result.setdefault(label['instance_id'], {}).setdefault(label['feature_id'], {}).setdefault(
                    label['source'], []).append(label)
        return {'class_id': class_id, 'instances': result}

    def stats(self):
        return {'classes': len(self.classes), 'instances': len(self.instances),
                'features': len(self.features), 'tasks': len(self.tasks),
                'contexts': len(self.contexts), 'sources': len(self.sources),
                'group_sets': len(self.groups), 'labels': len(self.labels)}
