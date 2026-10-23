"""Generate task opinions from anonymous feature samples with a selected LLM backend."""
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from src.catalog.files import safe_id
from src.catalog.io import write
from src.catalog.opinions import TASK_LABEL_SCHEMA, TASK_RESPONSE_SCHEMA, opinion_from_ratio
from src.catalog.sample_sources import SourceRun, checksums, write_run
from src.catalog.script_metadata import record_script
from src.labels.backends import create_backend, effective_settings
from releases.v1.scripts.prompts import prompt, common_prefix, cache_key


def prepare(root, sample_source, *, tasks=None, contexts=None, catalog_version=None):
    source = SourceRun(root, sample_source)
    if catalog_version is not None and source.meta.get('catalog_version') != catalog_version:
        raise ValueError('Sample source catalog version does not match the requested version')
    catalog = source.catalog
    selected = set(catalog.tasks if tasks is None else tasks)
    if not selected <= catalog.tasks.keys():
        raise ValueError('Unknown selected task')
    applicable = [key for key in catalog.contexts if key[0] in selected and key[1] in source.samples]
    if contexts is not None and not set(contexts) <= {key[2] for key in applicable}:
        raise ValueError('Unknown selected context')
    jobs = []
    for tid, cid, ctxid in sorted(applicable):
        if contexts is not None and ctxid not in contexts:
            continue
        binding = next(b for b in catalog.tasks[tid]['bindings'] if b['class_id'] == cid)
        for sid, features in sorted(source.samples[cid].items()):
            jobs.append({'task_id': tid, 'sample_id': sid, 'keys': [ctxid],
                         'input': {'features': features,
                                   'feature_definitions': catalog.classes[cid]['features'],
                                   'feature_encoding': source.feature_encoding,
                                   'task_label_schema': TASK_LABEL_SCHEMA,
                                   'task_response_schema': TASK_RESPONSE_SCHEMA,
                                   'task': {k: v for k, v in binding.items() if k not in ('class_id', 'contexts')},
                                   'context': catalog.contexts[tid, cid, ctxid]}})
    return {'catalog_version': source.meta.get('catalog_version'), 'sample_source': sample_source, 'sample_source_sha256': checksums(source.directory)}, jobs


def parse_output(raw, keys):
    body = raw.strip()
    if body.startswith('```'):
        if '\n' not in body or not body.endswith('```'):
            raise ValueError('Malformed fenced JSON response')
        body = body.split('\n', 1)[1].rsplit('```', 1)[0]
    def unique_pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate model response key')
            result[key] = value
        return result
    result = json.loads(body, object_pairs_hook=unique_pairs)
    if not isinstance(result, dict) or set(result) != set(keys):
        raise ValueError('Model response keys do not match requested labels')
    labels = {}
    for key, item in result.items():
        labels[key] = opinion_from_ratio(item)
    return labels


def execute(args, *, backend_factory=create_backend):
    root = args.root.resolve()
    sid = safe_id(args.source_id)
    if args.batch_size < 1 or args.max_tokens < 1 or args.timeout <= 0 or args.max_retries < 0:
        raise ValueError('Batch size, token budget and timeout must be positive; retries must be nonnegative')
    if (root / 'labels/generated' / sid).exists():
        raise ValueError('Source already exists; choose a new --source-id')
    metadata, jobs = prepare(root, args.sample_source, tasks=args.tasks, contexts=args.contexts,
                             catalog_version=args.catalog_version)
    if not jobs:
        raise ValueError('No inference requests selected')
    for job in jobs:
        job['prompt'] = prompt(job)
        job['prompt_cache_key'] = cache_key(common_prefix(job))
    summary = {'source': sid, 'requests': len(jobs), 'backend': args.backend,
               'model': args.model, 'dry_run': args.dry_run,
               'shared_prefixes': len({job['prompt_cache_key'] for job in jobs})}
    if args.dry_run:
        return summary
    from tqdm import tqdm
    import uuid
    attempt = root / 'runs/inference' / (sid + '-' + uuid.uuid4().hex)
    attempt.mkdir(parents=True)
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, text=True,
                            capture_output=True, check=False)
    metadata.update({'status': 'running', 'purpose': 'task_inference',
                     'response_encoding': {'name': 'uncertainty_percent_ratio_v1',
                                           'schema': TASK_RESPONSE_SCHEMA,
                                           'conversion': 'u=uncertainty_percent/100; yes=(1-u)*belief_ratio/total; no=(1-u)*disbelief_ratio/total; unknown=u; total=belief_ratio+disbelief_ratio; u=1 yields full unknown'},
                     'created_at': datetime.now(timezone.utc).isoformat(),
                     'provenance': {'method': 'ai_generated', 'backend': args.backend, 'model': args.model},
                     'label_provenance': {'method': 'ai_generated', 'review_status': 'unverified'},
                     'settings': effective_settings(args),
                     'selection': {'tasks': args.tasks, 'contexts': args.contexts},
                     'catalog_commit': commit.stdout.strip() if commit.returncode == 0 else None})
    write(attempt / 'request_metadata.json', metadata)
    write(attempt / 'requests.json', jobs)
    records, responses, errors = {}, [], []
    backend = None
    try:
        backend = backend_factory(args)
        metadata.update(backend.metadata)
        with (attempt / 'responses.jsonl').open('x') as log, (attempt / 'errors.jsonl').open('x') as error_log, tqdm(
                total=len(jobs), desc='Label inference', unit='request', file=sys.stderr) as progress:
            for start in range(0, len(jobs), args.batch_size):
                batch = jobs[start:start + args.batch_size]
                count = 0
                for output in backend.generate(batch):
                    if count >= len(batch):
                        raise ValueError('Backend returned too many outputs')
                    job = batch[count]
                    count += 1
                    response = {**job, **output}
                    log.write(json.dumps(response, ensure_ascii=False, allow_nan=False) + '\n')
                    log.flush()
                    responses.append(response)
                    try:
                        if output['status'] != 'completed':
                            raise ValueError('Model response was incomplete')
                        labels = parse_output(output['output'], job['keys'])
                    except ValueError as error:
                        failure = {**response, 'status': 'error', 'response_status': output['status'],
                                   'error_type': type(error).__name__, 'error': str(error)}
                        errors.append(failure)
                        error_log.write(json.dumps(failure, ensure_ascii=False, allow_nan=False) + '\n')
                        error_log.flush()
                    else:
                        records.setdefault(job['task_id'], {}).setdefault(job['sample_id'], {}).update(labels)
                    progress.update(1)
                    progress.set_postfix(errors=len(errors), refresh=False)
                if count != len(batch):
                    raise ValueError('Backend output count mismatch')
        metadata['status'] = 'complete'
        summary.update(succeeded=len(responses) - len(errors), failed=len(errors))
        metadata.update(succeeded=summary['succeeded'], failed=summary['failed'],
                        outcome='completed_with_errors' if errors else 'completed')
        if args.backend == 'openai':
            summary['cached_input_tokens'] = sum(r.get('cached_input_tokens', 0) for r in responses)
            metadata['cached_input_tokens'] = summary['cached_input_tokens']
        metadata['response_models'] = sorted({response['model'] for response in responses})
        write_run(root, sid, metadata, {}, records, extra={'responses.json': responses, 'errors.json': errors},
                  catalog_version=metadata['catalog_version'])
    except Exception as error:
        metadata.update(status='failed', error_type=type(error).__name__)
        raise
    finally:
        write(attempt / 'request_metadata.json', metadata)
        if backend is not None:
            backend.close()
    record_script(root, sid, {'script': os.environ.get('CDR_ENTRYPOINT', 'python releases/v1/scripts/prepare_labels.py'),
                  'source': sid, 'sample_source': args.sample_source, 'backend': args.backend,
                  'model': args.model, 'requests': len(jobs)})
    return summary


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[3])
    p.add_argument('--catalog-version', help='Require this version of the frozen sample catalog')
    p.add_argument('--sample-source', required=True)
    p.add_argument('--source-id', default='llm_labels')
    p.add_argument('--backend', choices=['openai', 'vllm'], required=True)
    p.add_argument('--model', required=True, help='Model ID for the selected backend')
    p.add_argument('--tasks', nargs='+')
    p.add_argument('--contexts', nargs='+')
    p.add_argument('--max-tokens', type=int, default=2048)
    p.add_argument('--batch-size', type=int, default=32)
    p.add_argument('--temperature', type=float, help='Omitted for OpenAI by default; vLLM defaults to 0')
    p.add_argument('--reasoning-effort', help='Optional OpenAI reasoning effort; model must support it')
    p.add_argument('--timeout', type=float, default=120, help='OpenAI request timeout in seconds')
    p.add_argument('--max-retries', type=int, default=2, help='OpenAI SDK retries')
    p.add_argument('--revision', default='main', help='vLLM model revision')
    p.add_argument('--seed', type=int, default=0, help='vLLM seed')
    p.add_argument('--tensor-parallel-size', type=int, default=1)
    p.add_argument('--gpu-memory-utilization', type=float, default=0.9)
    p.add_argument('--max-model-len', type=int, default=8192)
    p.add_argument('--dry-run', action='store_true')
    return p


def main():
    p = parser()
    args = p.parse_args()
    if args.backend == 'vllm' and args.reasoning_effort:
        p.error('--reasoning-effort is an OpenAI option')
    print(json.dumps(execute(args)), flush=True)


if __name__ == '__main__':
    main()
