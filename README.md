<div align="center">

# CDR-Dataset

### Contextual Default Retraction Dataset

Evaluating how language models reason with defaults and revise beliefs.

**Latest version: [v1](https://leobumjin.github.io/CDR-Dataset/v1/)**

[Project Page](https://leobumjin.github.io/CDR-Dataset/) · [🤗 Hugging Face](https://huggingface.co/datasets/leo-bjpark/CDR-Dataset) · [Code](https://github.com/leobumjin/CDR-Dataset)

</div>

## Overview

CDR-Dataset evaluates context-dependent conclusions while keeping the query and entity features fixed. Changing the context can preserve or defeat a conclusion, supporting comparisons of contextual default reasoning and belief retraction.

**Query + Domain + Context + Features → Label**

| Domain | Query |
| :--- | :--- |
| **Birds** | Can this bird fly? |
| **Legal Cases** | Is this person guilty? |
| **Humans** | Can this person run? |
| **Mammals** | Can this mammal survive? |
| **Plants** | Can this plant survive? |

Explore all five domains through the [interactive examples](https://leobumjin.github.io/CDR-Dataset/#examples). Choose a context to see how the question and answer change for the same entity.

## Dataset statistics

| Version | # Domains | # Queries / domain | # Contexts / domain | # Entities / domain | # Features / entity | Total samples |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| [**v1 ↗**](https://leobumjin.github.io/CDR-Dataset/v1/) | 5 | 1 | 5 | 100 | 7 | **2,500** |

Each domain contains **100 entities × 5 contexts = 500 samples**. Across five domains, v1 contains **500 entities and 2,500 samples**. The homepage examples show four selected contexts; the dataset contains five per domain.

The feature count refers to seven experimental judgments per entity. Their encoding is **0 = False · 0.5 = Ambiguous · 1 = True**; 0.5 is not a probability. Public records also preserve raw profile attributes.

| Split | Entities / domain | Samples / domain | Total samples |
| :--- | ---: | ---: | ---: |
| `train` | 40 | 200 | 1,000 |
| `test` | 20 | 100 | 500 |
| `revision_1` | 20 | 100 | 500 |
| `revision_2` | 20 | 100 | 500 |

Splitting uses seed 2027 and keeps all five contexts of an entity together. Revision splits add entities while retaining the same context set. There is no validation split; entity separation does not guarantee unseen species or feature vectors.

## Load the dataset

[**🤗 Explore v1 on Hugging Face ↗**](https://huggingface.co/datasets/leo-bjpark/CDR-Dataset/viewer/v1/train)

```python
from datasets import load_dataset

train = load_dataset("leo-bjpark/CDR-Dataset", "v1", split="train")
test = load_dataset("leo-bjpark/CDR-Dataset", "v1", split="test")
revision_1 = load_dataset("leo-bjpark/CDR-Dataset", "v1", split="revision_1")
revision_2 = load_dataset("leo-bjpark/CDR-Dataset", "v1", split="revision_2")
```

Versions are Hugging Face **configs** (`v1`, `v2`, …). To pin an exact dataset snapshot, additionally pass `revision="<commit SHA>"`.

### Sample format

Each Hugging Face record contains eight fields:

| Fields | Contents |
| :--- | :--- |
| `query_id`, `query_str` | Query identifier and question |
| `context_id`, `context_str` | Context identifier and definition |
| `entity_id`, `entity_name` | Entity identifier and source name |
| `feature_values` | Raw profile attributes and experimental feature judgments |
| `label` | String `"true"` or `"false"` |

Definitions are stored separately in [query](versions/v1/metadata/queries.json), [context](versions/v1/metadata/contexts.json), and [feature](versions/v1/metadata/features.json) metadata. Local canonical records additionally retain `domain` and `split` for auditing. See the [public schema](versions/v1/SCHEMA.md) for field mappings.

## Data generation

v1 preserves the AISTATS experimental snapshot with **GPT-5.4 teacher reference labels**. Domains, queries, contexts, and feature predicates are specified in the generation code. Entity profiles combine source catalogs and constructed individual states; human and legal profiles are fictional.

Experimental features are derived from the constructed profiles for Humans and Legal Cases, and annotated with GPT-5.4 for Birds, Mammals, and Plants. Query labels assess each entity under each stipulated context. These generated references are not independently verified ground truth; legal examples use a supplied hypothetical offence and exceptions.

The [v1 details page](https://leobumjin.github.io/CDR-Dataset/v1/) documents domains and queries, entities, feature categories and labeling, context categories, and query labeling. Version-specific [generation instructions](versions/v1/generation/README.md), [release notes](versions/v1/README.md), and [statistics](versions/v1/statistics.json) are retained in this repository.

## Repository and versioning

```text
CDR-Dataset/
├── versions/
│   ├── registry.json          # Current version registry
│   └── v1/
│       ├── generation/        # Version-specific source and configuration
│       ├── metadata/          # Query, context, and feature definitions
│       ├── SCHEMA.md
│       ├── statistics.json
│       └── manifest.json      # Provenance and checksums
├── shells/                    # Local preview, HF publication, release checks
├── evaluation/                # Dataset integrity and distribution audits
├── docs/                      # GitHub Pages and version detail pages
├── data/                      # Local dataset payloads — Git ignored
└── runs/                      # Local generation and audit outputs — Git ignored
```

Generation code and metadata remain tracked in Git. Dataset payloads are distributed through Hugging Face. Future versions get their own `versions/v2/`, `versions/v3/`, and corresponding Hugging Face configs, keeping each version's generation code and definitions together. Only v1 is currently released. See the [versioning guide](docs/versioning.md).

### Download and audit locally

```bash
python -m pip install -r requirements-huggingface.txt
bash shells/huggingface.sh download --version v1

python evaluation/evaluate.py --data data/v1 --output runs/v1/evaluation.json
python shells/release.py verify v1
```

Fresh generation runs are kept under `runs/`; follow the [v1 generation guide](versions/v1/generation/README.md) for dependencies and API stages. The evaluation command above audits the dataset rather than running language-model experiments.

### Publish to Hugging Face

```bash
hf auth login

# Prepare and check the payload locally.
bash shells/huggingface.sh --version v1 --dry-run

# Prepare and upload the public v1 config.
bash shells/huggingface.sh --version v1
```

The default destination is `leo-bjpark/CDR-Dataset`. Uploads update the selected version and preserve other version configs. See the [Hugging Face workflow](docs/huggingface.md) for staging, authentication, and download details.

### Preview the project page

```bash
bash shells/serve.sh
```

Open [localhost:8000](http://127.0.0.1:8000/) for the project page or [localhost:8000/v1/](http://127.0.0.1:8000/v1/) for v1 details. An optional port can be supplied with `bash shells/serve.sh 8080`.
