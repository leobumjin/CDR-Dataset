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
    '{"uncertainty_percent": INTEGER, "belief_ratio": INTEGER, "disbelief_ratio": INTEGER}. '
    'First choose uncertainty_percent as an integer from 0 to 100 for uncommitted uncertainty. '
    'Then split the remaining mass in the ratio belief_ratio:disbelief_ratio, each an integer from 0 to 9. '
    'Belief supports the task and disbelief opposes it. These ratios allocate only the mass remaining after uncertainty. '
    'The ratio cannot be 0:0 unless uncertainty_percent is 100; for full uncertainty use 100 and 0:0. '
    'For example, 20 percent uncertainty and a 4:1 ratio encode yes=0.64, no=0.16, unknown=0.20. '
    'Return only the three integers per key, without a value wrapper, reason, or computed masses. '
    'Use subjective-logic support, opposition and uncommitted uncertainty masses, not three mutually exclusive world outcomes. '
    'Lack of evidence belongs to unknown; completely insufficient evidence is {"uncertainty_percent":100,"belief_ratio":0,"disbelief_ratio":0}. '
    'Do not return null, a scalar label, or extra components.\n'
)


def common_prefix(job):
    data = job['input']
    return ('Feature definitions:\n' + encode(data['feature_definitions']) +
            '\nFeature encoding:\n' + encode(data['feature_encoding']) +
            '\nLabeling instructions:\n' + INSTRUCTIONS +
            'Task label schema:\n' + encode(data['task_label_schema']) +
            '\nTask response schema:\n' + encode(data['task_response_schema']) +
            '\nTask:\n' + encode(data['task']) +
            '\nContext:\n' + encode(data['context']) +
            '\nRequested keys: ' + encode(job['keys']) + '\n')


def sample_suffix(job):
    return 'Sample feature values:\n' + encode(job['input']['features']) + '\nJSON output:\n'


def prompt(job):
    return common_prefix(job) + sample_suffix(job)


def cache_key(prefix):
    return 'task-labels-' + hashlib.sha256(prefix.encode('utf-8')).hexdigest()[:48]
