# Data management guide

Keep repository documentation and the visible website in English.

## Model

A sample is defined by its feature values. It has a source-scoped `sample_id` for
reference, not an object name or an assumed real-world identity. Catalog classes
are feature groups, not registries of named entities. Keep the existing ten groups
and stable 70 feature IDs unless explicitly changing their definitions.

- Catalog defines feature meanings, tasks, class/task bindings and contexts.
- Source runs own sample feature vectors and optionally task labels.
- Task inference consumes feature values, their definitions/encoding, a task and
  context. Never pass object names, original identities, sample IDs or hidden raw
  profiles to the model. Sample IDs remain external bookkeeping.
- Feature provenance and label generation/review provenance are independent.
  Constructed samples may have AI-generated labels. A label is not verified ground
  truth merely because a model produced it.
- There are no N/R/R2 release families, real-name grounding flags, catalog instance
  lists, reserved instance ranges or name-based feature inference.
- Feature values have no universal range/type. Put an encoding in source metadata;
  the v1 sampler uses belief/disbelief/uncertain masses in [0,1] summing to 1,
  recorded as a subjective_logic source encoding. Historical encodings remain local.
- Task labels contain exactly yes, no and unknown masses in [0, 1], summing to 1
  (floating-point tolerance 1e-9). Yes is support, no opposition and unknown
  uncommitted uncertainty. Do not normalize invalid model output silently.
- Missing features remain absent keys. A missing task label means not generated;
  an explicit {yes: 0, no: 0, unknown: 1} is a generated opinion with full uncertainty.
  Never conflate these states or substitute null/scalar labels.

```text
catalog/<version>/classes/<class>.yaml             # group identity + features
catalog/<version>/tasks/<task>.yaml                # task + bindings + context definitions
labels/generated/<source_run>/
  sources.json                          # format, provenance, encoding, selections
  catalog/                              # frozen source definitions
  samples/<class>.json                   # sample ID -> feature ID -> value
  tasks_per_context/<task>.json          # optional sample ID -> context ID -> label
releases/<version>/
  meta_info.json                        # explicit sources, hashes and provenance
  catalog/                              # frozen definitions
  samples/<class>.json                   # frozen sample vectors
  labels/tasks_per_context/<task>.json   # optional frozen judgments
```

## Definitions

Catalog loading discovers flat classes/*.yaml and tasks/*.yaml, never list.yaml. Feature keys use
`<class>_f_001`; definitions contain name, description and optional labeling rubric.
Feature names describe predicates, not sample identities. Keep IDs stable when
renaming. Definition history belongs in Git. Reject duplicate IDs/names, missing
names/descriptions, unknown bindings and unbound contexts. Multi-class tasks must
explicitly bind their context IDs; do not infer applicability from ID prefixes.

Do not move sample values into catalog definitions or inherit class-wide encodings.
Changing a definition must not automatically reinterpret historical results.

## Source runs and generation

Read docs/label_generation_script.md before changing generators. Current sources
explicitly declare `format: feature_samples_v1`. Use SourceRun to load an explicitly
selected run. FileCatalog reads definitions only; it does not scan old source runs
or select a preferred result. Old named sources are not automatically migrated.

Sources contain direct feature maps, with no per-sample name or wrapper object.
Sample IDs must be unique within one source; resolve them with their source ID
across runs. Do not assume that identical ID strings from different runs mean the
same feature combination. Repeated vectors are allowed; sample IDs are references,
not semantic object identities.

Source runs are immutable. Use a new source ID for each execution; failed validation
must leave no completed source directory. Explicit source references carry checksums.
Task-only runs reference `sample_source` instead of copying or reconstructing its
features. The shared task-label schema is in src/catalog/opinions.py and is included
in model inputs. Validate every response, source and release against it. Label metadata records generation method and review status separately;
verified status requires evidence references. Preserve raw AI requests/responses.

- prepare_samples samples each feature independently as belief/disbelief/uncertain
  masses summing to 1. Default balanced_regions chooses T>=0.8, F>=0.8,
  balanced (each 0.25–0.40), or uncertain>=0.7 with equal probability, then
  samples uniformly inside the selected region. Keep uniform_simplex as a
  baseline and explicit opinion lists as an override. Record region parameters
  and counts in source metadata; it never generates task labels.
- prepare_labels uses --backend openai|vllm and an explicit --model. Both backends
  consume the same anonymous requests and validate the same opinion contract.
  --dry-run imports no model SDK and makes no network requests.

Do not run model inference, downloads or publication merely to edit this pipeline.
Source provenance may retain external identifiers for auditing, but model inputs
must exclude them. Keep raw observations, constructed values and model estimates
explicitly distinguished in provenance.

## Releases

Releases select feature samples and optionally task labels. Use src/catalog/releases.py
to assemble a new local snapshot from explicit source IDs and a catalog commit.
Require matching sample vectors, reject overlapping labels and preserve generation
and review provenance. Freeze definitions and artifact checksums. Existing release
snapshots must never be overwritten. A version directory containing only scripts/
and shells/ may receive its first snapshot without modifying its code. Sources are never chosen by recency.

No task labels is a valid release state. Missing labels do not imply a special
synthetic/real type. Keep historical versions/v1 and data/v1 unchanged; do not
transfer their IDs or judgments to feature-defined samples. The empty legacy
releases/v1 preview stub has been removed. Typed N/R/R2 plans are
retired. Publication/upload is a separate user-authorized action.

## Website

Serve docs/ locally with tools/serve.sh. The Catalog page lives at /catalog/
and displays sample IDs and feature vectors, never named
catalog instances. Catalog mode displays definitions without invented samples.
The class browser includes Features and Task-Context tabs. There is no separate
Task–Context page; keep navigation within the selected class.
Use frozen release definitions for released values. Preserve numeric zero and show
missing values as `-`. Keep search focus and accessible feature information.

Regenerate assets with `python -m src.catalog.web_assets`. catalog.json contains
only definitions. release_samples.json contains only explicit releases; unpublished
source runs never appear as fallback data. Keep historical v1 pages/examples separate.
Generation script registries record actual successful runs only.

## Validation and storage

```bash
python -m src.catalog validate
python -m unittest discover -s tests -q
node tests/test_ui.cjs
python -m src.catalog.web_assets
```

Use `python -m src.catalog source <source_id>` to validate an explicit source and
`python -m src.catalog releases` to validate release manifests/snapshots.
Keep runs/, data/ and generated source payloads local/ignored. Retired named
catalog code and unversioned wrappers have been removed. Preserve historical
versions/v1 and data/v1 artifacts and their independent publication tools.


## Catalog versions and execution entrypoints

Catalog definitions live in catalog/v1/{classes,tasks}/. A new catalog version
gets a separate v2/, v3/, etc.; do not choose the latest directory implicitly or
create speculative version copies. --catalog-version explicitly selects a version
(default v1). Sources record catalog_version and freeze only that version's
classes/tasks. Task runs inherit frozen sample definitions and must match the
version required by their wrapper. Releases retain catalog_version.

releases/<version>/shells/ contains versioned experiment entrypoints;
releases/<version>/scripts/ contains their Python generation implementations:
- releases/v1/shells/run1_prepare_samples.sh samples feature combinations without task labels;
  default source ID v1_run1_samples. Its encoding is a source parameter.
- releases/v1/shells/run1_prepare_labels.sh runs LLM task inference for that sample source;
  default output v1_run1_labels. --dry-run validates requests without loading a model.

Use new source IDs for reruns. Auxiliary preview/setup/legacy publication tools
live in tools/.
Catalog v1 is distinct from the immutable historical versions/v1 publication.


## Model backends and dependencies

Install requirements.txt for catalog/sampling work, requirements-openai.txt for
OpenAI labeling, or requirements-vllm.txt for local GPU labeling. Keep SDK imports
inside backend construction so dry runs need only the base dependencies.

OPENAI_API_KEY stays in the environment; never save it in CLI settings, prompts or
source metadata. OpenAI uses Responses API structured output, with local validation
for opinion bounds and sum. Record actual response models, usage, IDs and raw output.
vLLM records the requested model/revision, resolved revision, generation settings
and raw output. Incomplete/invalid responses must leave a failed attempt record,
not a completed label source. Tests use fake backends; no paid API/GPU execution is
implied by modifying this repository.

## Shared labeling model selection

Keep API_MODELS and VLLM_MODELS in shells/common/models.sh. Release labeling
wrappers source shells/common/select_label_model.sh for interactive choices and
explicit CLI overrides. The default is OpenAI gpt-4o-mini. Noninteractive runs
use the first configured matching model; --help must bypass selection. Model
selection alone must not import SDKs, load GPU models or call APIs.
