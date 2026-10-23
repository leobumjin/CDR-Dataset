"""Optional model backends. Imports and credentials are needed only for real runs."""
from src.catalog.opinions import TASK_RESPONSE_SCHEMA


def response_schema(keys):
    return {'type': 'object', 'properties': {key: TASK_RESPONSE_SCHEMA for key in keys},
            'required': list(keys), 'additionalProperties': False}



def effective_settings(args):
    result = {'max_tokens': args.max_tokens, 'batch_size': args.batch_size}
    if args.backend == 'openai':
        result.update(timeout=args.timeout, max_retries=args.max_retries)
        if args.temperature is not None:
            result['temperature'] = args.temperature
        if args.reasoning_effort:
            result['reasoning_effort'] = args.reasoning_effort
    else:
        result.update(temperature=0 if args.temperature is None else args.temperature,
                      seed=args.seed, revision=args.revision, dtype='bfloat16',
                      tensor_parallel_size=args.tensor_parallel_size,
                      gpu_memory_utilization=args.gpu_memory_utilization,
                      max_model_len=args.max_model_len, enable_prefix_caching=True,
                      structured_output='json_schema')
    return result


class OpenAIBackend:
    def __init__(self, args, *, client=None):
        self.args = args
        if client is None:
            import os
            if not os.environ.get('OPENAI_API_KEY'):
                raise ValueError('Set OPENAI_API_KEY for the OpenAI backend')
            from openai import OpenAI
            client = OpenAI(timeout=args.timeout, max_retries=args.max_retries)
        self.client = client
        self.metadata = {'backend': 'openai', 'requested_model': args.model}

    def generate(self, jobs):
        for job in jobs:
            request = {'model': self.args.model, 'input': [{'role': 'user', 'content': job['prompt']}],
                       'text': {'format': {'type': 'json_schema', 'name': 'task_opinions',
                                          'strict': True, 'schema': response_schema(job['keys'])}},
                       'max_output_tokens': self.args.max_tokens, 'store': False}
            if job.get('prompt_cache_key'):
                request['prompt_cache_key'] = job['prompt_cache_key']
            if self.args.temperature is not None:
                request['temperature'] = self.args.temperature
            if self.args.reasoning_effort:
                request['reasoning'] = {'effort': self.args.reasoning_effort}
            try:
                response = self.client.responses.create(**request)
            except Exception as error:
                # Exception bodies may include request headers; never copy those into artifacts.
                status = getattr(error, 'status_code', None)
                raise RuntimeError(f'OpenAI request failed: {type(error).__name__}, HTTP {status}') from None
            raw = response.model_dump(mode='json')
            usage = raw.get('usage') or {}
            cached_tokens = (usage.get('input_tokens_details') or {}).get('cached_tokens', 0)
            yield {'output': response.output_text, 'status': response.status,
                   'model': response.model, 'response_id': response.id,
                   'cached_input_tokens': cached_tokens, 'raw_response': raw}

    def close(self):
        self.client.close()


class VLLMBackend:
    def __init__(self, args):
        from vllm import LLM
        self.args = args
        self.llm = LLM(model=args.model, revision=args.revision, dtype='bfloat16', seed=args.seed,
                       tensor_parallel_size=args.tensor_parallel_size,
                       gpu_memory_utilization=args.gpu_memory_utilization,
                       max_model_len=args.max_model_len, enable_prefix_caching=True, limit_mm_per_prompt={'image': 0})
        self.metadata = {'backend': 'vllm', 'requested_model': args.model,
                         'enable_prefix_caching': True, 'structured_output': 'json_schema',
                         'requested_revision': args.revision,
                         'resolved_revision': getattr(self.llm.llm_engine.model_config.hf_config, '_commit_hash', None)}

    def generate(self, jobs):
        from vllm import SamplingParams
        from vllm.sampling_params import StructuredOutputsParams
        sampling = [SamplingParams(
            temperature=0 if self.args.temperature is None else self.args.temperature,
            max_tokens=self.args.max_tokens, seed=self.args.seed,
            structured_outputs=StructuredOutputsParams(json=response_schema(job['keys'])))
            for job in jobs]
        outputs = self.llm.chat([[{'role': 'user', 'content': job['prompt']}] for job in jobs],
                                sampling_params=sampling)
        if len(outputs) != len(jobs):
            raise ValueError('vLLM output count mismatch')
        for result in outputs:
            output = result.outputs[0]
            finish_reason = getattr(output, 'finish_reason', None)
            yield {'output': output.text, 'status': 'incomplete' if finish_reason == 'length' else 'completed',
                   'model': self.args.model, 'finish_reason': finish_reason,
                   'stop_reason': getattr(output, 'stop_reason', None),
                   'token_ids': list(getattr(output, 'token_ids', []))}

    def close(self):
        pass


def create_backend(args):
    return {'openai': OpenAIBackend, 'vllm': VLLMBackend}[args.backend](args)
