import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.catalog.io import load
from src.catalog.opinions import opinion_from_ratio, validate_opinion
from src.catalog.sample_sources import SourceRun
from src.labels.backends import OpenAIBackend, VLLMBackend
from src.labels.prepare_labels import execute, parser
from src.labels.prepare_samples import generate
from src.labels.prepare_labels import prepare, parse_output
from releases.v1.scripts.prompts import common_prefix, sample_suffix, prompt, cache_key

ROOT = Path(__file__).resolve().parents[1]
RATIO = {'uncertainty_percent': 20, 'belief_ratio': 4, 'disbelief_ratio': 1}
OPINION = {'yes': 0.64, 'no': 0.16, 'unknown': 0.2}


class FakeResponse:
    def __init__(self, keys, status='completed', value=None):
        self.output_text = json.dumps({key: RATIO if value is None else value for key in keys})
        self.status = status
        self.id = 'response-test'
        self.model = 'resolved-model'

    def model_dump(self, mode):
        return {'id': self.id, 'model': self.model, 'status': self.status, 'output_text': self.output_text,
                'usage': {'output_tokens': 20, 'input_tokens_details': {'cached_tokens': 128}}}


class FakeClient:
    def __init__(self, *, status='completed', value=None):
        self.responses = self
        self.requests = []
        self.status = status
        self.value = value
        self.closed = False

    def create(self, **request):
        self.requests.append(request)
        keys = request['text']['format']['schema']['required']
        return FakeResponse(keys, status=self.status, value=self.value)

    def close(self):
        self.closed = True


class BackendTests(unittest.TestCase):
    def test_ratio_conversion_bounds_and_full_uncertainty(self):
        for uncertainty in range(101):
            for belief in range(10):
                for disbelief in range(10):
                    value = {'uncertainty_percent': uncertainty,
                             'belief_ratio': belief, 'disbelief_ratio': disbelief}
                    if uncertainty < 100 and belief == disbelief == 0:
                        with self.assertRaises(ValueError):
                            opinion_from_ratio(value)
                    else:
                        opinion = opinion_from_ratio(value)
                        validate_opinion(opinion)
                        self.assertEqual(opinion['unknown'], uncertainty / 100)
        for key, invalid_values in {
            'uncertainty_percent': [-1, 101, 20.0, True, None],
            'belief_ratio': [-1, 10, 4.0, False, '4'],
            'disbelief_ratio': [-1, 10, 1.0, True, None],
        }.items():
            for value in invalid_values:
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    parse_output(json.dumps({'ctx': {**RATIO, key: value}}), ['ctx'])
        for value in ({**RATIO, 'reason': 'extra'}, {'belief_ratio': 4}, None):
            with self.assertRaises(ValueError):
                parse_output(json.dumps({'ctx': value}), ['ctx'])
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            parse_output('{"ctx":{"uncertainty_percent":20,"belief_ratio":4,"belief_ratio":5,"disbelief_ratio":1}}', ['ctx'])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT / 'catalog', self.root / 'catalog')
        generate(self.root, source_id='samples', count=1, classes=['bird'])

    def args(self, backend='openai', *extra):
        return parser().parse_args(['--root', str(self.root), '--sample-source', 'samples',
                                    '--source-id', 'labels', '--backend', backend,
                                    '--model', 'chosen-model', *extra])

    def test_sample_values_follow_identical_common_prefixes(self):
        generate(self.root, source_id='multiple', count=2, classes=['bird'])
        _, jobs = prepare(self.root, 'multiple')
        first, second, other_context = jobs[:3]
        self.assertEqual(common_prefix(first), common_prefix(second))
        self.assertEqual(cache_key(common_prefix(first)), cache_key(common_prefix(second)))
        self.assertNotEqual(sample_suffix(first), sample_suffix(second))
        self.assertTrue(prompt(first).startswith(common_prefix(first)))
        self.assertNotIn('bird_s_000001', prompt(first))
        self.assertTrue(prompt(first).index('Feature definitions:') < prompt(first).index('Sample feature values:'))
        self.assertNotEqual(cache_key(common_prefix(first)), cache_key(common_prefix(other_context)))
        # JSON insertion order must not invalidate a reusable prefix or suffix.
        import copy
        reordered = copy.deepcopy(first)
        reordered['input']['features'] = dict(reversed(list(first['input']['features'].items())))
        self.assertEqual(prompt(first), prompt(reordered))

    def test_dry_run_never_constructs_a_backend(self):
        for backend in ('openai', 'vllm'):
            with self.subTest(backend=backend):
                factory = lambda args: self.fail('Dry run loaded a backend')
                result = execute(self.args(backend, '--dry-run'), backend_factory=factory)
                self.assertEqual(result['backend'], backend)
                self.assertEqual(result['requests'], 5)
        self.assertFalse((self.root / 'labels/generated/labels').exists())
        self.assertFalse((self.root / 'runs/inference').exists())

    def test_openai_requests_structured_opinions_and_saves_model_provenance(self):
        client = FakeClient()
        args = self.args('openai', '--reasoning-effort', 'low')
        args.batch_size = 2
        with patch('tqdm.tqdm') as progress:
            result = execute(args, backend_factory=lambda args: OpenAIBackend(args, client=client))
        progress.assert_called_once_with(total=5, desc='Label inference', unit='request', file=sys.stderr)
        self.assertEqual(progress.return_value.__enter__.return_value.update.call_count, 5)
        self.assertEqual(result['requests'], 5)
        self.assertEqual(result['cached_input_tokens'], 640)
        self.assertEqual(result['shared_prefixes'], 5)
        self.assertTrue(client.closed)
        request = client.requests[0]
        self.assertEqual(request['model'], 'chosen-model')
        self.assertFalse(request['store'])
        self.assertTrue(request['prompt_cache_key'].startswith('task-labels-'))
        self.assertNotIn('temperature', request)
        self.assertNotIn('seed', request)
        self.assertEqual(request['reasoning'], {'effort': 'low'})
        schema = request['text']['format']['schema']
        value_schema = next(iter(schema['properties'].values()))
        self.assertEqual(set(value_schema['required']), {'uncertainty_percent', 'belief_ratio', 'disbelief_ratio'})
        run = SourceRun(self.root, 'labels')
        self.assertEqual(run.meta['backend'], 'openai')
        self.assertEqual(run.meta['cached_input_tokens'], 640)
        self.assertNotIn('seed', run.meta['settings'])
        self.assertNotIn('revision', run.meta['settings'])
        self.assertEqual(run.meta['response_models'], ['resolved-model'])
        self.assertEqual(run.tasks['fly']['bird_s_000001']['dry_20m'], OPINION)
        responses = load(run.directory / 'responses.json')
        self.assertEqual(responses[0]['response_id'], 'response-test')
        self.assertEqual(responses[0]['raw_response']['usage']['output_tokens'], 20)

    def test_invalid_mass_or_incomplete_output_never_creates_source(self):
        for status, value in [('completed', {'yes': 1, 'no': 1, 'unknown': 1}), ('incomplete', RATIO)]:
            with self.subTest(status=status):
                client = FakeClient(status=status, value=value)
                with self.assertRaises(ValueError):
                    execute(self.args(), backend_factory=lambda args: OpenAIBackend(args, client=client))
                self.assertFalse((self.root / 'labels/generated/labels').exists())
                self.assertTrue(client.closed)
        attempts = list((self.root / 'runs/inference').iterdir())
        self.assertEqual(len(attempts), 2)
        for attempt in attempts:
            self.assertEqual(load(attempt / 'request_metadata.json')['status'], 'failed')
            self.assertTrue((attempt / 'responses.jsonl').read_text())
            self.assertTrue((attempt / 'requests.json').exists())

    def test_openai_errors_do_not_echo_request_secrets(self):
        client = FakeClient()
        def fail(**kwargs):
            raise RuntimeError('secret-api-key')
        client.create = fail
        backend = OpenAIBackend(self.args(), client=client)
        with self.assertRaisesRegex(RuntimeError, 'OpenAI request failed') as error:
            list(backend.generate([{'keys': ['ctx'], 'prompt': 'input'}]))
        self.assertNotIn('secret-api-key', str(error.exception))

    def test_vllm_uses_selected_model_and_sampling_settings(self):
        calls = {}
        def llm(**kwargs):
            calls['model'] = kwargs
            def chat(messages, sampling_params, use_tqdm):
                calls['use_tqdm'] = use_tqdm
                calls['messages'] = messages
                calls['sampling'] = sampling_params
                return [SimpleNamespace(outputs=[SimpleNamespace(text=json.dumps({'ctx': RATIO}), finish_reason='stop', token_ids=[1, 2])])]
            return SimpleNamespace(chat=chat, llm_engine=SimpleNamespace(model_config=SimpleNamespace(hf_config=SimpleNamespace(_commit_hash='revision-id'))))
        fake = SimpleNamespace(LLM=llm, SamplingParams=lambda **kwargs: kwargs)
        with patch.dict(sys.modules, {'vllm': fake, 'vllm.sampling_params': SimpleNamespace(StructuredOutputsParams=lambda **kwargs: kwargs)}):
            backend = VLLMBackend(self.args('vllm', '--temperature', '0.25', '--tensor-parallel-size', '2'))
            output = list(backend.generate([{'prompt': 'anonymous features', 'keys': ['ctx']}]))[0]
        self.assertEqual(calls['model']['model'], 'chosen-model')
        self.assertEqual(calls['model']['tensor_parallel_size'], 2)
        self.assertEqual(calls['sampling'][0]['temperature'], 0.25)
        self.assertTrue(calls['model']['enable_prefix_caching'])
        self.assertFalse(calls['use_tqdm'])
        self.assertEqual(calls['sampling'][0]['structured_outputs']['json']['required'], ['ctx'])
        self.assertEqual(parse_output(output['output'], ['ctx']), {'ctx': OPINION})
        self.assertEqual(output['status'], 'completed')
        self.assertEqual(backend.metadata['resolved_revision'], 'revision-id')
        self.assertEqual(calls['messages'], [[{'role': 'user', 'content': 'anonymous features'}]])
