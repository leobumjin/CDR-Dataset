"""Stable common prefixes and per-sample suffixes for v1 task labeling."""
import hashlib
import json


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


INSTRUCTIONS = (
    'Judge the task under its context using only the supplied feature values and definitions. '
    'When the feature encoding is subjective_logic, belief supports the feature predicate, '
    'disbelief opposes it, and uncertain is uncommitted uncertainty; these masses sum to 1. '
    'Do not collapse a feature opinion to a scalar or reinterpret it as a task label. '
    'Any scalar labeling rubric in a feature definition is background guidance, not the supplied value encoding. '
    'The sample is defined by these features. Do not assume an object identity or invent missing features. '
    'Return only a JSON object with exactly the requested keys, each mapping to '
    '{"value": {"yes": NUMBER, "no": NUMBER, "unknown": NUMBER}, "reason": "brief basis"}. '
    'All three masses are required, finite and between 0 and 1; yes + no + unknown must equal 1. '
    'Use subjective-logic support, opposition and uncommitted uncertainty masses, not three mutually exclusive world outcomes. '
    'Lack of evidence belongs to unknown; completely insufficient evidence is {"yes":0,"no":0,"unknown":1}. '
    'Do not return null, a scalar label, or extra components.\n'
)


def common_prefix(job):
    data = job['input']
    return ('Feature definitions:\n' + encode(data['feature_definitions']) +
            '\nFeature encoding:\n' + encode(data['feature_encoding']) +
            '\nLabeling instructions:\n' + INSTRUCTIONS +
            'Task label schema:\n' + encode(data['task_label_schema']) +
            '\nTask:\n' + encode(data['task']) +
            '\nContext:\n' + encode(data['context']) +
            '\nRequested keys: ' + encode(job['keys']) + '\n')


def sample_suffix(job):
    return 'Sample feature values:\n' + encode(job['input']['features']) + '\nJSON output:\n'


def prompt(job):
    return common_prefix(job) + sample_suffix(job)


def cache_key(prefix):
    return 'task-labels-' + hashlib.sha256(prefix.encode('utf-8')).hexdigest()[:48]
