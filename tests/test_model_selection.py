"""Exercise the shared launcher without model downloads or API calls."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ModelSelectionTests(unittest.TestCase):
    def test_all_vllm_models_use_separate_processes_and_source_ids(self):
        result = self.launch('--model', 'all_vllm_models', '--source-id', 'experiment',
                             '--batch-size', '4', '--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        runs = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(runs), 6)
        sources = set()
        for args in runs:
            model = args[args.index('--model') + 1]
            source = args[args.index('--source-id') + 1]
            self.assertEqual(source, 'experiment_' + model.replace('/', '_'))
            self.assertEqual(args[args.index('--backend') + 1], 'vllm')
            self.assertEqual(args[args.index('--batch-size') + 1], '4')
            self.assertIn('--dry-run', args)
            sources.add(source)
        self.assertEqual(len(sources), 6)

    def test_all_vllm_models_rejects_openai_backend(self):
        result = self.launch('--backend', 'openai', '--model=all_vllm_models')
        self.assertEqual(result.returncode, 2)
        self.assertIn('requires the vllm backend', result.stderr)

    def launch(self, *args):
        with tempfile.TemporaryDirectory() as directory:
            interpreter = Path(directory) / 'capture'
            interpreter.write_text('#!/usr/bin/env python3\nimport json, sys\nprint(json.dumps(sys.argv[1:]))\n')
            interpreter.chmod(0o755)
            return subprocess.run(
                ['bash', str(ROOT / 'releases/v1/shells/run1_prepare_labels.sh'), *args],
                cwd='/tmp', env={**os.environ, 'PYTHON': str(interpreter)},
                stdin=subprocess.DEVNULL, capture_output=True, text=True)

    def test_default_and_explicit_models(self):
        for options, backend, model in [
            ([], 'openai', 'gpt-4o-mini'),
            (['--backend', 'vllm'], 'vllm', 'google/gemma-3-27b-it'),
            (['--model', 'gpt-4o-mini'], 'openai', 'gpt-4o-mini'),
            (['--model=google/gemma-3-27b-it'], 'vllm', 'google/gemma-3-27b-it'),
            (['--backend', 'openai', '--model', 'custom-model'], 'openai', 'custom-model'),
        ]:
            with self.subTest(options=options):
                result = self.launch(*options)
                self.assertEqual(result.returncode, 0, result.stderr)
                args = json.loads(result.stdout)
                def option(name):
                    for index, arg in reversed(list(enumerate(args))):
                        if arg.startswith(name + '='):
                            return arg.split('=', 1)[1]
                        if arg == name:
                            return args[index + 1]
                self.assertEqual(option('--backend'), backend)
                self.assertEqual(option('--model'), model)
                self.assertTrue(args[0].endswith('releases/v1/scripts/prepare_labels.py'))

    def test_help_does_not_select_or_run_models(self):
        result = self.launch('--help')
        self.assertEqual(result.returncode, 0)
        self.assertNotIn('Labeling model:', result.stderr)
        self.assertNotIn('--model', json.loads(result.stdout))

    def test_unknown_model_requires_backend(self):
        result = self.launch('--model', 'custom-model')
        self.assertEqual(result.returncode, 2)
        self.assertIn('--backend', result.stderr)
