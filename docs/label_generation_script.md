# Versioned sample preparation and LLM labeling

Catalogs are small, explicit snapshots: catalog/v1/classes/*.yaml and
catalog/v1/tasks/*.yaml. Future changes use catalog/v2/, catalog/v3/, etc. The
existing ten feature groups and four tasks are in v1; no future version is implied.
Catalog versions are independent of the historical versions/v1 publication.

releases/v1/shells/ has two entrypoints for the first v1 experiment:

```text
releases/v1/shells/run1_prepare_samples.sh
releases/v1/shells/run1_prepare_labels.sh
```

## 1. Prepare feature samples

```bash
bash releases/v1/shells/run1_prepare_samples.sh --count 100 --seed 0
bash releases/v1/shells/run1_prepare_samples.sh --classes bird --count 10 --source-id v1_bird_samples
bash releases/v1/shells/run1_prepare_samples.sh --classes bird --count 10 --source-id v1_custom_samples --feature-values '[{"belief":0.7,"disbelief":0.2,"uncertain":0.1}]'
```

The wrapper selects catalog version v1 and defaults to source v1_run1_samples.
It samples a random combination of values for every feature, without object names
or task labels. --classes defaults to all groups; --count defaults to 100 per group.
Each feature value is an object with exactly `belief`, `disbelief`, and `uncertain`:
finite numbers in [0, 1] whose sum is 1 (tolerance 1e-9). These represent support
for the feature predicate, opposition, and uncommitted uncertainty. By default,
the generator independently samples each feature uniformly on the three-component
simplex (Dirichlet(1,1,1)), using two sorted uniform cuts. The seed reproduces the
same values. `--feature-values` optionally supplies a nonempty list of valid
opinion objects to sample uniformly instead; scalar values are rejected.
This source encoding is recorded explicitly and is distinct from task labels,
which continue to use `yes`, `no`, and `unknown`. Historical source encodings
remain unchanged. Independent sampling does not claim physical
realizability or enforce domain-specific dependencies.

Each source ID is immutable. Choose a new ID for another execution. The source
records catalog_version, the selected encoding, seed and provenance, and freezes
only the selected catalog version. IDs reference samples inside their source;
features define the samples' meaning.

## 2. Prepare LLM-generated labels

```bash
PYTHON=python bash releases/v1/shells/run1_prepare_labels.sh --backend vllm --model google/gemma-3-27b-it --dry-run
bash releases/v1/shells/run1_prepare_labels.sh --backend vllm --model google/gemma-3-27b-it
bash releases/v1/shells/run1_prepare_labels.sh --backend openai --model "$OPENAI_MODEL" --source-id v1_run1_openai_labels
```

Run the wrapper without model arguments to select an API or vLLM model:

```bash
bash releases/v1/shells/run1_prepare_labels.sh
bash releases/v1/shells/run1_prepare_labels.sh --dry-run
```

The shared `shells/common/models.sh` defines `API_MODELS` and `VLLM_MODELS`.
The first choice is OpenAI `gpt-4o-mini`; press Enter to select it. Noninteractive
runs use the first configured choice (also gpt-4o-mini by default). Supplying
`--backend vllm` limits selection to vLLM models. Explicit `--backend` and `--model`
skip selection; unlisted models require both. No API calls or model loading happen
during selection. `--help` skips selection entirely.

Future release wrappers can source `shells/common/select_label_model.sh`, call
`select_label_model "$@"`, and prepend `"${LABEL_MODEL_ARGS[@]}"` to their script
arguments. The selected backend/model are also available as `LABEL_BACKEND` and
`LABEL_MODEL`. Model configuration is shared across releases.

OpenAI runs use `PYTHON` or `python`; vLLM runs prefer the configured venv unless
`PYTHON` is supplied. Install `requirements-openai.txt` in the chosen API Python
environment and set `OPENAI_API_KEY` before actual API execution.

OPENAI_MODEL above is an explicitly selected model ID. The wrapper defaults to sample source v1_run1_samples and output v1_run1_labels.
It requires the sample source to belong to catalog version v1 and uses its frozen
feature/task/context definitions. --sample-source and --source-id override these
IDs. --tasks and --contexts optionally restrict applicable requests. Groups without
task bindings do not produce task requests.

Dry-run prepares and validates requests without SDK imports, GPU loading, API calls or weight downloads.
Actual vLLM labeling requires a configured GPU runtime and model access. OpenAI
labeling instead requires its optional SDK and OPENAI_API_KEY in the environment. Auxiliary setup
is separate from the experiment entrypoints:

```bash
python -m pip install -r requirements-openai.txt  # OpenAI only
bash tools/setup_vllm.sh                         # vLLM only
bash tools/setup_vllm.sh --check
```

Inputs contain only feature values, their definitions/encoding, task, context and
task_label_schema. Object names, external identities, sample IDs and hidden raw
profiles never enter prompts. Model responses require all requested context keys:

```json
{"dry_20m": {"value": {"yes": 0.7, "no": 0.2, "unknown": 0.1}, "reason": "Basis in supplied features and context."}}
```

Exactly yes, no and unknown are required, finite and in [0, 1], summing to 1 within
1e-9. These are support, opposition and uncommitted uncertainty masses. Fully
insufficient evidence is {yes: 0, no: 0, unknown: 1}. Null/scalar labels, extra
components, duplicate keys, booleans and invalid sums are rejected without automatic
normalization. An absent judgment means it was not produced; it differs from an
explicit full-unknown opinion. Missing feature values remain absent keys.

Task-only sources reference sample_source with checksums, retain catalog_version,
and record ai_generated and unverified provenance. Exact prompts, raw responses,
actual model/revision and settings are saved. Failed attempts remain under
runs/inference/; completed sources also preserve responses.json.

Shared options include --model, --batch-size and --max-tokens. --temperature is
omitted for OpenAI by default and defaults to 0 for vLLM. OpenAI options include
--reasoning-effort, --timeout and --max-retries; vLLM options include --revision,
--seed, --tensor-parallel-size, --max-model-len and --gpu-memory-utilization. PYTHON overrides the
interpreter; CDR_VENV overrides the runtime directory.

## Validation, releases and tools

```bash
python -m src.catalog --catalog-version v1 validate
python -m src.catalog source v1_run1_samples
python -m src.catalog.web_assets --catalog-version v1
bash tools/serve.sh
```

Source storage remains labels/generated/<source-id>/ with sources.json, frozen
catalog/, samples/<class>.json and optional tasks_per_context/<task>.json. Generated
sources stay local and never become website fallback data. Successful runs update
only their script metadata entry. Source generation never automatically creates a
release or publishes data. See [release assembly](../releases/README.md).

Other preview/setup/historical publication helpers live in tools/. Retired named-catalog code, random task-label helpers and unversioned wrappers
have been removed. Frozen
historical versions/v1 and data/v1 exports remain unchanged.

## Dependencies and backend implementation

requirements.txt contains only base catalog/sampling dependencies. OpenAI and vLLM
are optional, separate dependency files; OpenAI labeling does not require CUDA.
The Python implementations are releases/v1/scripts/prepare_samples.py and
releases/v1/scripts/prepare_labels.py,
with prompt text and formatting in releases/v1/scripts/prompts.py
and backend adapters in src/labels/backends.py. No model-specific entrypoint is
needed. API keys are read only from the environment and never saved in metadata.

OpenAI requests use the [official Responses API structured-output format](https://developers.openai.com/api/docs/guides/structured-outputs).
Both backend paths still validate opinion sums locally. Raw outputs, actual
response model IDs and provenance are saved, and incomplete/refused/invalid output
never becomes a completed source. Successful results remain unverified model
estimates unless separately reviewed with evidence.

## Shared prompt prefixes and JSON decoding

`releases/v1/scripts/prompts.py` separates `common_prefix(job)` from
`sample_suffix(job)`. Feature definitions and source encoding come first, followed
by labeling instructions, opinion schema, task, context and requested keys. Only
the final suffix contains the sample feature values. JSON keys are sorted for
stable serialization. Requests already run in task/class/context groups, keeping
samples with the same prefix adjacent. No previous sample's answer enters another
sample's prompt.

OpenAI requests send a deterministic hash of the common prefix as
`prompt_cache_key` and retain strict JSON-schema output. Actual cache use is
provider-dependent, including minimum prefix length and cache availability; a key
does not guarantee a hit. Each response records `cached_input_tokens` from API
usage, and the completed run reports the total. Raw usage remains in responses.json.
See [OpenAI prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching).

vLLM explicitly enables prefix caching and uses per-request
`StructuredOutputsParams(json=...)` with the same opinion response schema.
See [vLLM structured outputs](https://docs.vllm.ai/en/v0.11.0/examples/offline_inference/structured_outputs.html).
Both paths parse JSON locally, validate exact context keys, nonempty reasons,
finite masses and the sum constraint before writing any completed source.
Dry-run reports the number of requests and distinct shared prefixes without
making model calls. GPU cache hit rates and API cache savings require a real run;
unit tests only verify prefix stability, backend settings and output validation.
