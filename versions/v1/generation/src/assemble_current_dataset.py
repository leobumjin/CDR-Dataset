"""Assemble the active five-domain snapshot without calling APIs or altering labels."""
import copy
from pathlib import Path

from dataset_common import ROOT, digest, file_digest, read_json, read_jsonl, write_json, write_jsonl
from make_api_based_labels import load_inputs, export_dataset
from make_api_based_features import apply_feature_results, feature_schema


def main():
    output = ROOT / 'data/current'
    if output.exists():
        raise ValueError('data/current already exists; preserve it before rebuilding')
    original = ROOT / 'outputs/dataset/inputs'
    revision = ROOT / 'data/v2-bird-legal/inputs'
    sources = [load_inputs(original), load_inputs(revision)]
    changed = {'birds', 'legal_cases'}
    manifest = copy.deepcopy(sources[0][0])
    domains = manifest['domains']
    instances, pairs, specs, schedules = [], [], {}, {}
    provenance = {}
    for domain in domains:
        index = int(domain in changed)
        source_manifest, source_instances, source_pairs, source_specs, source_schedules = sources[index]
        instances.extend(copy.deepcopy(r) for r in source_instances if r['domain'] == domain)
        pairs.extend(copy.deepcopy(r) for r in source_pairs if r['domain'] == domain)
        specs[domain] = source_specs[domain]
        schedules[domain] = source_schedules[domain]
        provenance[domain] = {'input_directory': str((original, revision)[index].relative_to(ROOT)),
                              'dataset_fingerprint': source_manifest['dataset_fingerprint']}
        manifest['feature_statistics'][domain] = source_manifest['feature_statistics'][domain]
        manifest['counts'][domain] = source_manifest['counts'][domain]
    manifest['assembly_sources'] = provenance
    payloads = {'instances.jsonl': instances, 'pairs.jsonl': pairs, 'specifications.json': specs, 'schedules.json': schedules}
    for name, rows in payloads.items():
        (write_jsonl if name.endswith('.jsonl') else write_json)(output / 'inputs' / name, rows)
    manifest['files'] = {name: file_digest(output / 'inputs' / name) for name in payloads}
    manifest['dataset_fingerprint'] = digest({k: v for k, v in manifest.items() if k != 'dataset_fingerprint'})
    write_json(output / 'inputs/manifest.json', manifest)
    for model in ('gpt-4o', 'gpt-5.4'):
        model_instances = copy.deepcopy(instances)
        annotations = {}
        source_runs = {}
        for index, (source_manifest, _, _, _, _) in enumerate(sources):
            base = ROOT / ('data/v1' if index == 0 else 'data/v2-bird-legal')
            selected_domains = [d for d in domains if int(d in changed) == index]
            selected_instances = [r for r in model_instances if r['domain'] in selected_domains]
            selected_specs = {d: specs[d] for d in selected_domains}
            apply_feature_results(base / 'features' / model, source_manifest, selected_instances, selected_specs)
            label_dir = base / 'labels' / model
            source_runs[str(base.relative_to(ROOT))] = read_json(label_dir / 'run_manifest.json')
            for domain in selected_domains:
                category = {'birds': 'bird', 'humans': 'human', 'mammals': 'mammal', 'plants': 'plant', 'legal_cases': 'legal'}[domain]
                result = read_json(label_dir / f'{category}_result.json')
                for row in result['results']:
                    annotations[row['pair_id']] = row
                feature_path = base / 'features' / model / f'{category}_result.json'
                if feature_path.exists():
                    feature = read_json(feature_path)
                    feature['source_dataset_fingerprint'] = feature['dataset_fingerprint']
                    feature['dataset_fingerprint'] = manifest['dataset_fingerprint']
                    write_json(output / 'features' / model / feature_path.name, feature)
        assert set(annotations) == {p['pair_id'] for p in pairs}
        for pair in pairs:
            annotation = annotations[pair['pair_id']]
            assert annotation['status'] == 'resolved' and annotation['input_hash'] == pair['input_hash']
        feature_output = output / 'features' / model
        feature_settings = read_json(ROOT / 'data/v1/features' / model / 'run_manifest.json')['feature_settings']
        feature_settings['schemas'] = {d: feature_schema(specs[d]['feature_names']) for d in ('birds', 'mammals', 'plants')}
        feature_run_fingerprint = digest([manifest['dataset_fingerprint'], feature_settings])
        feature_annotations = []
        for path in sorted(feature_output.glob('*_result.json')):
            payload = read_json(path)
            payload['source_run_fingerprint'] = payload['run_fingerprint']
            payload['run_fingerprint'] = feature_run_fingerprint
            for row in payload['results']:
                row['source_run_fingerprint'] = row['run_fingerprint']
                row['run_fingerprint'] = feature_run_fingerprint
                feature_annotations.append(row)
            write_json(path, payload)
        write_jsonl(feature_output / 'annotations.jsonl', feature_annotations)
        write_json(feature_output / 'run_manifest.json', {
            'dataset_fingerprint': manifest['dataset_fingerprint'], 'run_fingerprint': feature_run_fingerprint,
            'feature_settings': feature_settings, 'kind': 'assembled_snapshot', 'assembly_sources': provenance,
        })
        feature_fingerprint = apply_feature_results(output / 'features' / model, manifest, model_instances, specs)
        # Preserve the vectors actually used in each source label export, which
        # may have been estimated by a different feature model.
        for instance in model_instances:
            annotation = annotations[f"{instance['instance_id']}/c_1"]
            instance['feature_values'] = annotation['feature_values']
            instance['feature_vector'] = annotation['feature_vector']
            instance['feature_source'] = annotation['feature_source']
        label_output = output / 'labels' / model
        settings = copy.deepcopy(source_runs['data/v1']['teacher_settings'])
        settings['feature_results_fingerprint'] = feature_fingerprint
        if any(r.get('feature_source', {}).get('model', model) != model for r in model_instances):
            settings['assembled_feature_sources'] = {r['domain']: r.get('feature_source') for r in model_instances}
        run_fingerprint = digest([manifest['dataset_fingerprint'], settings])
        for annotation in annotations.values():
            annotation['source_run_fingerprint'] = annotation.get('run_fingerprint')
            annotation['run_fingerprint'] = run_fingerprint
        write_json(label_output / 'run_manifest.json', {
            'dataset_fingerprint': manifest['dataset_fingerprint'],
            'teacher_settings': settings,
            'run_fingerprint': run_fingerprint,
            'kind': 'assembled_snapshot', 'assembly_sources': source_runs,
        })
        write_jsonl(label_output / 'annotations.jsonl', [annotations[p['pair_id']] for p in pairs])
        summary = export_dataset(label_output, manifest, model_instances, pairs, specs, schedules, annotations, {})
        assert summary['retained_pairs'] == 2500 and summary['retained_instances'] == 500
        print(f'{model}: {summary["retained_pairs"]} pairs, {summary["retained_instances"]} instances')
    write_json(output / 'assembly.json', {'input_fingerprint': manifest['dataset_fingerprint'], 'sources': provenance,
                                        'policy': 'Preserve teacher responses and source run metadata; export all five domains from the selected inputs.'})


if __name__ == '__main__':
    main()
