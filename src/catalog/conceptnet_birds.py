"""Rank ConceptNet's direct bird subtypes by unique direct IsA children.

No release data, model inference, species validation, or v1 inputs are used.
"""
import argparse
import gzip
import hashlib
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
from .files import FileCatalog, safe_id
from .io import load, write, instance_items, instance_document
from .ranges import reserved_ids
from .sources import load_sources, source_binding


def collection_config(declaration):
    """Keep class.yaml declarative; implementation policy lives here."""
    return {
        **declaration,
        'root': '/c/en/bird',
        'relation': '/r/IsA',
        'language': 'en',
        'candidate_depth': 1,
        'positive_weight_only': True,
        'normalization': 'collapse_part_of_speech_and_sense_to_term_uri',
        'ranking': {'metric': 'unique_direct_child_count', 'order': 'descending',
                    'tie_breaker': 'concept_uri_ascending'},
        'identifiers': {'prefix': 'bird_', 'digits': 4, 'preserve_existing_concept_ids': True},
        'api': {'base_url': 'https://api.conceptnet.io', 'page_size': 1000,
                'request_interval_seconds': 1.1, 'timeout_seconds': 20, 'retries': 2},
    }


def canonical(uri):
    """ConceptNet term URI; merge noun/sense variants without stemming words."""
    pieces = uri.split('/')
    if len(pieces) < 4 or pieces[:2] != ['', 'c'] or not pieces[3]:
        return None
    return '/'.join(pieces[:4])


def normalize(edge, language='en'):
    if edge.get('rel', {}).get('@id') != '/r/IsA' or edge.get('weight', 0) <= 0:
        return None
    start = canonical(edge['start']['@id'])
    end = canonical(edge['end']['@id'])
    prefix = f'/c/{language}/'
    if not start or not end or not start.startswith(prefix) or not end.startswith(prefix) or start == end:
        return None
    return start, end


def children(edges, parent, language='en'):
    result = {}
    for edge in edges:
        pair = normalize(edge, language)
        if pair and pair[1] == parent:
            result.setdefault(pair[0], {})[edge['@id']] = edge
    return {child: list(records.values()) for child, records in result.items()}


def rank(candidates, child_map):
    rows = [{'uri': uri, 'name': uri.split('/')[3].replace('_', ' '),
             'child_count': len(child_map[uri]), 'children': sorted(child_map[uri]),
             'bird_edge_ids': sorted(e['@id'] for e in edges)}
            for uri, edges in candidates.items()]
    return sorted(rows, key=lambda r: (-r['child_count'], r['uri']))


class Api:
    def __init__(self, config, cache, offline=False):
        self.config, self.cache, self.offline = config, Path(cache), offline
        self.cache.mkdir(parents=True, exist_ok=True)
        self.pages, self.last_request = {}, 0.0

    def page(self, url):
        base = self.config['base_url']
        if urlparse(url).netloc != urlparse(base).netloc or urlparse(url).scheme != urlparse(base).scheme:
            raise ValueError('Pagination URL changed API origin')
        key = hashlib.sha256(url.encode()).hexdigest()
        path = self.cache / f'{key}.json'
        if path.exists():
            saved = load(path)
            if saved['url'] != url:
                raise ValueError('Cache URL mismatch')
        else:
            if self.offline:
                raise ValueError(f'Missing cached API page: {url}')
            for attempt in range(self.config['retries'] + 1):
                wait = self.config['request_interval_seconds'] - (time.monotonic() - self.last_request)
                if wait > 0:
                    time.sleep(wait)
                self.last_request = time.monotonic()
                try:
                    request = Request(url, headers={'User-Agent': 'CDR-Dataset ConceptNet catalog collector'})
                    with urlopen(request, timeout=self.config['timeout_seconds']) as response:
                        body = json.load(response)
                    if 'edges' not in body or not isinstance(body['edges'], list) or body.get('error'):
                        raise ValueError('Unexpected ConceptNet response; no result has been published')
                    saved = {'url': url, 'retrieved_at': datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),
                             'body': body}
                    write(path, saved)
                    break
                except (HTTPError, URLError, TimeoutError, OSError) as error:
                    if attempt == self.config['retries']:
                        raise RuntimeError(f'ConceptNet request failed: {url}: {error}') from error
                    time.sleep(min(2 ** attempt, 5))
        if not isinstance(saved.get('body', {}).get('edges'), list):
            raise ValueError('Invalid cached API response')
        self.pages[key] = {'url': url, 'retrieved_at': saved['retrieved_at'],
                           'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        return saved['body']

    def children(self, parent):
        query = urlencode({'rel': '/r/IsA', 'end': parent, 'limit': self.config['page_size']})
        url = self.config['base_url'].rstrip('/') + '/query?' + query
        edges, seen = [], set()
        while url:
            if url in seen:
                raise ValueError('ConceptNet pagination loop; refusing incomplete ranking')
            seen.add(url)
            body = self.page(url)
            edges.extend(body['edges'])
            next_page = body.get('view', {}).get('nextPage')
            url = urljoin(self.config['base_url'], next_page) if next_page else None
        return children(edges, parent)


def dump_edges(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', encoding='utf-8') as stream:
        for line in stream:
            fields = line.rstrip('\n').split('\t', 4)
            if len(fields) != 5:
                raise ValueError('Expected ConceptNet assertions TSV with five columns')
            eid, relation, start, end, metadata = fields
            if relation != '/r/IsA':
                continue
            data = json.loads(metadata)
            yield {**data, '@id': eid, 'rel': {'@id': relation},
                   'start': {'@id': start}, 'end': {'@id': end}}


def from_dump(path, root):
    # First pass finds candidates; second pass counts every candidate's children.
    candidates = children(dump_edges(path), root)
    child_map = {uri: {} for uri in candidates}
    evidence = {e['@id']: e for edges in candidates.values() for e in edges}
    for edge in dump_edges(path):
        pair = normalize(edge)
        if pair and pair[1] in child_map and pair[0] != root:
            child_map[pair[1]].setdefault(pair[0], {})[edge['@id']] = edge
            evidence[edge['@id']] = edge
    return candidates, child_map, list(evidence.values())


def validate_config(config):
    if (config['source'], config['relation'], config['language'], config['candidate_depth']) != (
            'conceptnet', '/r/IsA', 'en', 1):
        raise ValueError('Collector supports English direct IsA children only')
    if canonical(config['root']) != config['root'] or not config['root'].startswith('/c/en/'):
        raise ValueError('Root must be an English term URI')
    if config['ranking'] != {'metric': 'unique_direct_child_count', 'order': 'descending',
                             'tie_breaker': 'concept_uri_ascending'}:
        raise ValueError('Unsupported ranking policy')
    if config['positive_weight_only'] is not True:
        raise ValueError('Collector requires positive-weight edges')
    if config['normalization'] != 'collapse_part_of_speech_and_sense_to_term_uri':
        raise ValueError('Unsupported normalization')
    reserved_ids(config)
    if (config['identifiers']['prefix'], config['identifiers']['digits']) != ('bird_', 4):
        raise ValueError('Expected bird_0001-style IDs')
    if config['identifiers']['preserve_existing_concept_ids'] is not True:
        raise ValueError('Concept IDs must remain stable')


def identifiers(ranked, registry):
    """Fill unbound reserved slots; existing URI bindings are authoritative."""
    by_uri = {row['uri']: row for row in ranked}
    used = set()
    slots = {iid: entry for iid, entry in registry.items() if entry['source'] == 'conceptnet'}
    for iid, entry in slots.items():
        if len(iid) != 9 or not iid.startswith('bird_') or not iid[5:].isdigit():
            raise ValueError(f'Invalid reserved bird ID: {iid}')
        uri = entry.get('concept_uri')
        if uri is not None:
            if not isinstance(uri, str) or canonical(uri) != uri or not uri.startswith('/c/en/'):
                raise ValueError(f'Invalid preserved concept URI: {uri}')
            if uri in used:
                raise ValueError(f'Concept URI reserved more than once: {uri}')
            if uri not in by_uri:
                raise ValueError(f'Preserved concept is missing from current candidates: {uri}')
            used.add(uri)
    available = iter(row for row in ranked if row['uri'] not in used)
    result = {}
    for iid, entry in slots.items():
        uri = entry.get('concept_uri')
        row = by_uri[uri] if uri else next(available, None)
        if row is None:
            raise ValueError('Not enough candidates to fill the reserved ConceptNet IDs')
        result[iid] = row
    return result


def collect(root, *, assertions=None, source_id=None, offline=False):
    root = Path(root)
    definition_path = root / 'catalog/classes/bird/class.yaml'
    definition = load(definition_path)
    config = collection_config(definition['collection'])
    validate_config(config)
    registry = reserved_ids(config)
    limit = len(registry)
    previous_list = load(root / 'catalog/classes/bird/list.yaml')
    previous_items = instance_items(previous_list, 'bird')
    sources = load_sources(root)
    for item in previous_items:
        if item['id'] not in registry:
            continue
        binding = source_binding(sources, config['source'], item['id'])
        if not binding or not binding.get('uri'):
            raise ValueError(f'Existing source lacks the ID binding: {item["id"]}')
        registry[item['id']]['concept_uri'] = binding['uri']
    reserved = registry
    now = datetime.now(ZoneInfo('Asia/Seoul')).isoformat()
    source_id = source_id or 'conceptnet_' + datetime.now(ZoneInfo('Asia/Seoul')).strftime('%y%m%d_%H%M%S')
    safe_id(source_id)
    destination = root / 'labels' / 'generated' / source_id
    if destination.exists():
        raise ValueError(f'Source run already exists: {source_id}')
    cache = root / 'data/sources/conceptnet/bird'
    page_metadata = {}
    if assertions:
        assertions = Path(assertions).resolve()
        candidates, child_map, evidence = from_dump(assertions, config['root'])
        with assertions.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        input_info = {'mode': 'assertions_tsv', 'filename': assertions.name, 'sha256': digest,
                      'format': 'ConceptNet five-column assertions TSV (optionally gzip)'}
    else:
        api = Api(config['api'], cache, offline)
        candidates = api.children(config['root'])
        if len(candidates) < limit:
            raise ValueError(f'Only {len(candidates)} candidates; need {limit}. No changes published.')
        child_map, edges_by_id = {}, {e['@id']: e for edges in candidates.values() for e in edges}
        for index, uri in enumerate(sorted(candidates), 1):
            print(f'Counting {index}/{len(candidates)}: {uri}', file=sys.stderr, flush=True)
            found = api.children(uri)
            found.pop(config['root'], None)
            child_map[uri] = found
            edges_by_id.update({e['@id']: e for edges in found.values() for e in edges})
        evidence, page_metadata = list(edges_by_id.values()), api.pages
        input_info = {'mode': 'api', 'base_url': config['api']['base_url'],
                      'cache_replay': offline, 'pages': page_metadata}
    ranked = rank(candidates, child_map)
    if len(ranked) < limit:
        raise ValueError(f'Only {len(ranked)} candidates; need {limit}. No changes published.')
    bound = identifiers(ranked, registry)
    items = [{'id': iid, 'name': row['name']} for iid, row in bound.items()]
    # Refresh only the IDs owned by this collector; retain other list entries.
    items += [item for item in previous_items if item['id'] not in reserved]
    groups = {'bird': []}
    for iid, row in bound.items():
        groups[row['uri']] = [{'group_id': 'bird', 'edge_ids': row['bird_edge_ids']}]
        groups[iid] = [{'group_id': row['uri'], 'method': 'catalog_id_binding'}]
    FileCatalog.validate_groups(groups)
    metadata = {'id': source_id, 'provider': 'conceptnet', 'added_time': now,
                'script': config['script'], 'selection': config, 'input': input_info,
                'candidate_count': len(ranked), 'selected_count': len(bound), 'concepts': bound,
                'id_registry': {iid: {'uri': row['uri']} for iid, row in bound.items()},
                'class_definition': definition,
                'licenses': sorted({e['license'] for e in evidence if e.get('license')}),
                'ranking_file': 'ranking.json', 'evidence_file': 'evidence.json',
                'note': 'ConceptNet concepts, not verified biological species. No feature or task labels inferred.'}
    # Validate and stage every result before replacing the live list. A failed
    # request or insufficient candidate count never publishes a partial catalog.
    stage = root / 'runs/conceptnet' / source_id
    if stage.exists():
        raise ValueError(f'Staging directory already exists: {stage}')
    stage.mkdir(parents=True)
    write(stage / 'sources.json', metadata)
    write(stage / 'ranking.json', ranked)
    write(stage / 'evidence.json', evidence)
    write(stage / 'groups/bird.json', groups)
    for key in page_metadata:
        target = stage / 'raw' / f'{key}.json'
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(cache / f'{key}.json', target)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(stage, destination)
        write(root / 'catalog/classes/bird/list.yaml', instance_document('bird', items))
        FileCatalog(root)
    except Exception:
        write(root / 'catalog/classes/bird/list.yaml', previous_list)
        if destination.exists():
            shutil.rmtree(destination)
        raise
    return {'source': source_id, 'candidates': len(ranked), 'selected': len(bound),
            'list': 'catalog/classes/bird/list.yaml'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--source-id')
    parser.add_argument('--assertions', type=Path, help='Local official assertions TSV or TSV.GZ')
    parser.add_argument('--offline', action='store_true', help='Replay complete cached API pages only')
    args = parser.parse_args()
    try:
        print(json.dumps(collect(args.root, assertions=args.assertions, source_id=args.source_id,
                                 offline=args.offline), indent=2))
    except (ValueError, RuntimeError, OSError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
