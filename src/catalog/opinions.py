"""Binary subjective-logic opinion masses: support, opposition and uncertainty."""
import math

COMPONENTS = ('yes', 'no', 'unknown')
TASK_RESPONSE_SCHEMA = {
    'type': 'object',
    'properties': {
        'uncertainty_percent': {'type': 'integer', 'minimum': 0, 'maximum': 100},
        'belief_ratio': {'type': 'integer', 'minimum': 0, 'maximum': 9},
        'disbelief_ratio': {'type': 'integer', 'minimum': 0, 'maximum': 9},
    },
    'required': ['uncertainty_percent', 'belief_ratio', 'disbelief_ratio'],
    'additionalProperties': False,
}


def opinion_from_ratio(value):
    """Decode an explicit uncertainty/ratio judgment into stored opinion masses."""
    if not isinstance(value, dict) or set(value) != set(TASK_RESPONSE_SCHEMA['required']):
        raise ValueError('Task response must contain exactly uncertainty_percent, belief_ratio and disbelief_ratio')
    for key, spec in TASK_RESPONSE_SCHEMA['properties'].items():
        if type(value[key]) is not int or not spec['minimum'] <= value[key] <= spec['maximum']:
            raise ValueError(f'{key} must be an integer in [{spec["minimum"]}, {spec["maximum"]}]')
    u = value['uncertainty_percent'] / 100
    total = value['belief_ratio'] + value['disbelief_ratio']
    if u == 1:
        return validate_opinion({'yes': 0, 'no': 0, 'unknown': 1})
    if total == 0:
        raise ValueError('Belief/disbelief ratio cannot be 0:0 unless uncertainty is 100%')
    return validate_opinion({'yes': (1 - u) * value['belief_ratio'] / total,
                             'no': (1 - u) * value['disbelief_ratio'] / total,
                             'unknown': u})


TASK_LABEL_SCHEMA = {'components': list(COMPONENTS), 'minimum': 0, 'maximum': 1,
                     'sum': 1, 'sum_tolerance': 1e-9,
                     'interpretation': {'yes': 'supporting belief mass',
                                        'no': 'opposing belief mass',
                                        'unknown': 'uncommitted uncertainty mass'}}


def validate_opinion(value):
    if not isinstance(value, dict) or set(value) != set(COMPONENTS):
        raise ValueError('Task label must contain exactly yes, no and unknown')
    for mass in value.values():
        if type(mass) not in (int, float) or not 0 <= mass <= 1 or not math.isfinite(mass):
            raise ValueError('Opinion masses must be finite numbers in [0, 1], not booleans')
    if not math.isclose(math.fsum(value.values()), 1, rel_tol=0, abs_tol=TASK_LABEL_SCHEMA['sum_tolerance']):
        raise ValueError('yes + no + unknown must sum to 1')
    return value


FEATURE_COMPONENTS = ('belief', 'disbelief', 'uncertain')
FEATURE_VALUE_SCHEMA = {
    'type': 'subjective_logic', 'components': list(FEATURE_COMPONENTS),
    'minimum': 0, 'maximum': 1, 'sum': 1, 'sum_tolerance': 1e-9,
    'interpretation': {'belief': 'support for the feature predicate',
                       'disbelief': 'opposition to the feature predicate',
                       'uncertain': 'uncommitted uncertainty about the feature predicate'},
}


def validate_feature_opinion(value):
    if not isinstance(value, dict) or set(value) != set(FEATURE_COMPONENTS):
        raise ValueError('Feature value must contain exactly belief, disbelief and uncertain')
    for mass in value.values():
        if type(mass) not in (int, float) or not math.isfinite(mass) or not 0 <= mass <= 1:
            raise ValueError('Feature masses must be finite numbers in [0, 1], not booleans')
    if not math.isclose(math.fsum(value.values()), 1, rel_tol=0, abs_tol=1e-9):
        raise ValueError('belief + disbelief + uncertain must sum to 1')
    return value
