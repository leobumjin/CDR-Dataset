"""Export v1's public sample schema from the preserved experimental snapshot."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

QUERIES = {
    'birds': ('can_fly', 'Can this bird fly?'),
    'humans': ('can_run', 'Can this person run?'),
    'mammals': ('can_survive_mammal', 'Can this mammal survive?'),
    'plants': ('can_survive_plant', 'Can this plant survive?'),
    'legal_cases': ('is_guilty', 'Is this person guilty?'),
}
CONTEXTS = {
    'birds': ['dry_20m', 'dry_500m', 'wet_20m', 'dry_5m', 'wet_500m'],
    'humans': ['run_100m_8kmh', 'run_5km_10kmh', 'run_1km_uphill', 'run_100m_12kmh', 'run_10km_8kmh'],
    'mammals': ['mammal_mild_7d', 'mammal_cold_24h', 'mammal_heat_24h', 'mammal_no_water_food_3d', 'mammal_no_food_14d'],
    'plants': ['plant_no_water_3d', 'plant_hot_drought_30d', 'plant_freezing_7d', 'plant_watered_7d', 'plant_waterlogged_7d'],
    'legal_cases': ['ordinary_situation', 'emergency_necessity', 'official_duties', 'supervisors_order', 'friends_request'],
}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def export(source, output, metadata=None):
    source, output = Path(source), Path(output)
    metadata = Path(metadata) if metadata else Path(__file__).resolve().parents[1] / "metadata"
    if (source / "source").is_dir():
        source = source / "source"
    specs = json.loads((source/'inputs/specifications.json').read_text())
    instances = {(r['domain'], r['instance_id']): r for r in
                 map(json.loads, (source/'inputs/instances.jsonl').read_text().splitlines())}
    rows = list(map(json.loads, (source/'labels/gpt-5.4/dataset.jsonl').read_text().splitlines()))
    contexts, queries, feature_values, definitions = {}, [], defaultdict(dict), {}
    for domain, (query_id, query_str) in QUERIES.items():
        queries.append({'query_id': query_id, 'query_str': query_str, 'domain': domain,
                        'target_definition': specs[domain]['target_definition']})
        for index, context in enumerate(specs[domain]['contexts']):
            contexts[domain, context['context_id']] = {
                'context_id': CONTEXTS[domain][index], 'context_str': context['description'],
                'query_id': query_id, 'source_context_id': context['context_id']}
        for name, definition in specs[domain]['feature_definitions'].items():
            definitions[domain, name] = definition['description']
    samples = []
    for row in rows:
        domain = row['domain']
        entity_id = row['instance_id'].replace(' ', '_')
        instance = instances[domain, entity_id]
        context = contexts[domain, row['context_id']]
        # Retain actual raw facts and the exact seven experimental judgments.
        features = dict(instance['raw_feature_values'])
        features.update(row['feature_values'])
        if instance.get('species_id'):
            features['species'] = instance['original_identity']
        for name, value in features.items():
            feature_values[domain, name][json.dumps(value, sort_keys=True)] = value
        samples.append({'query_id': QUERIES[domain][0], 'query_str': QUERIES[domain][1],
                        'context_id': context['context_id'], 'context_str': context['context_str'],
                        'entity_id': entity_id, 'entity_name': instance['original_identity'],
                        'feature_values': features, 'label': 'true' if row['label'] == 1 else 'false',
                        'domain': domain, 'split': row['split']})
    output.mkdir(parents=True, exist_ok=True)
    with (output/'samples.jsonl').open('w') as stream:
        for sample in samples:
            stream.write(json.dumps(sample, ensure_ascii=False) + '\n')
    write_json(metadata/'queries.json', {'queries': queries})
    write_json(metadata/'contexts.json', {'contexts': list(contexts.values())})
    features = []
    for (domain, name), values in sorted(feature_values.items()):
        description = definitions.get((domain, name))
        if description is None:
            description = ('The source species identity.' if name == 'species' else
                           f'Stipulated source profile: {name.replace("_", " ")}.')
        features.append({'feature_id': name, 'domain': domain, 'feature_str': description,
                         'possible_values': [values[k] for k in sorted(values)]})
    write_json(metadata/'features.json', {'features': features,
               'notes': 'Feature IDs are scoped by domain. possible_values lists observed v1 values. '
                        'Numeric 0.5 means an ambiguous judgment, not a probability. '
                        'Raw profile facts and experimental judgments are both preserved.'})
    return samples


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--metadata-output', type=Path, help='Defaults to versions/v1/metadata')
    args = parser.parse_args()
    result = export(args.source, args.output, args.metadata_output)
    print(f'Exported {len(result)} samples to {args.output}')
