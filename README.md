<div align="center">

# CDR-Dataset

### Contextual Default Retraction Dataset

A dataset for evaluating contextual default reasoning and belief retraction in language models.

[![GitHub](https://img.shields.io/badge/GitHub-Code-181717?logo=github)](https://github.com/leobumjin/CDR-Dataset)
[![Project Page](https://img.shields.io/badge/Project-Page-537448)](https://leobumjin.github.io/CDR-Dataset/)
[![Hugging Face](https://img.shields.io/badge/🤗%20Hugging%20Face-Dataset-FFD21E)](https://huggingface.co/datasets/leo-bjpark/CDR-Dataset)
![Task](https://img.shields.io/badge/Task-Default%20Reasoning-2563EB)
![Focus](https://img.shields.io/badge/Focus-Belief%20Retraction-7C3AED)

---

**Reason with defaults. Reconsider with context.**

</div>

| Resource | Link | What you’ll find |
| :--- | :--- | :--- |
| 🌐 **Project Page** | [CDR-Dataset](https://leobumjin.github.io/CDR-Dataset/) | Overview and interactive Bird / Guilty examples |
| 🤗 **Hugging Face** | [leo-bjpark/CDR-Dataset](https://huggingface.co/datasets/leo-bjpark/CDR-Dataset) | Dataset files and version configs |
| 📦 **Dataset v1** | [View v1](https://huggingface.co/datasets/leo-bjpark/CDR-Dataset/tree/main/v1) | 500 instances · 2,500 context pairs |
| 💻 **GitHub** | [leobumjin/CDR-Dataset](https://github.com/leobumjin/CDR-Dataset) | Versioned generation code, statistics, and documentation |

## Overview

Language models often need to draw reasonable conclusions from incomplete information. Those conclusions should remain open to revision when new context introduces an exception.

**CDR-Dataset** (Contextual Default Retraction Dataset) is designed to evaluate this ability, with a focus on two connected aspects of reasoning:

| Capability | Evaluation focus |
| :--- | :--- |
| **Contextual default reasoning** | Drawing defeasible conclusions from the available context. |
| **Belief retraction** | Withdrawing a previously supported conclusion when new context defeats its justification. |

## Motivation

A plausible default is useful only when a model can recognize its limits. Evaluating both the initial inference and its subsequent retraction helps assess whether a model can adapt its conclusions to changing evidence.

> **Illustrative example — not a dataset record**
>
> **Default:** Birds typically fly.
>
> **Initial context:** Pip is a bird.
>
> **Default conclusion:** Pip can fly.
>
> **New context:** Pip is a penguin, and penguins cannot fly.
>
> **Retraction:** The default conclusion that Pip can fly no longer holds.

## Repository

The dataset repository is hosted at [**leobumjin/CDR-Dataset**](https://github.com/leobumjin/CDR-Dataset).

```bash
git clone https://github.com/leobumjin/CDR-Dataset.git
cd CDR-Dataset
```

## Repository structure

```text
versions/v1/                 # Git-tracked version metadata
├── README.md                # Release notes
├── manifest.json            # Provenance and checksums
├── statistics.json
├── metadata/                # Query, context, and feature definitions
└── generation/              # Generation source, configs, requirements, runner
shells/                      # HF entrypoint and release verification
evaluation/                  # Local integrity and distribution checks
data/v1/                    # Local dataset, Git ignored
runs/                        # Local working results, Git ignored
```

Version 2 and later get their own `versions/v2`, `versions/v3`, etc. Generation
code remains tracked; payloads are distributed through Hugging Face configs.
See the [layout and versioning guide](docs/versioning.md).

## Dataset v1

The first version preserves the existing AISTATS experimental snapshot: **500
instances × 5 contexts = 2,500 instance–context pairs**, across birds, humans,
mammals, plants, and legal cases. Each domain has seven features.

| Version | # Query Type | # Domain / Query | # Context / Query | # Entity / Query | Total / Query |
| :--- | ---: | ---: | ---: | ---: | ---: |
| **v1** | **5** | **1** | **5** | **100** | **500** |

Query Type counts the five distinct `query_id` values. All remaining columns
are **per query**: 1 domain × 5 contexts × 100 entities = 500 samples.
Mammal and plant survival are separate queries. The full v1 release has 2,500 samples.

| Split | Instances | Pairs |
| :--- | ---: | ---: |
| Train | 200 | 1,000 |
| Revision 1 | 100 | 500 |
| Revision 2 | 100 | 500 |
| Test | 100 | 500 |

Preserved experimental reference: `data/v1/source/labels/gpt-5.4/dataset.jsonl`.
GPT-5.4 annotations, raw responses, inputs, run settings, and four student
prompt variants are preserved. These are teacher-generated references,
not independently verified ground truth. v1 has one default dataset configuration, generated with GPT-5.4.

- [v1 release notes](versions/v1/README.md)
- [Detailed statistics](versions/v1/statistics.json)
- [v1 generation instructions](versions/v1/generation/README.md)

## Local work and Hugging Face

```bash
python evaluation/evaluate.py --data data/v1 --output runs/v1/evaluation.json
python shells/release.py verify v1
bash shells/huggingface.sh prepare --version v1
```

Publish explicitly after reviewing the prepared payload:

```bash
python -m pip install -r requirements-huggingface.txt
hf auth login
bash shells/huggingface.sh --version v1
```

Download on another machine with `download --version v1 --repo-id leo-bjpark/CDR-Dataset`.
See [local evaluation, publication, and download instructions](docs/huggingface.md).

```python
from datasets import load_dataset
train = load_dataset("leo-bjpark/CDR-Dataset", "v1", split="train")
test = load_dataset("leo-bjpark/CDR-Dataset", "v1", split="test")
```

## Public sample format

v1 exposes `data/v1/samples.jsonl`; its Git-tracked definitions live in
`versions/v1/metadata/{queries,contexts,features}.json`.
Each sample has query/context/entity IDs and text, feature values, a string
`"true"`/`"false"` label, domain, and the original split. Feature definitions
are stored once in metadata. See the [v1 schema](versions/v1/SCHEMA.md).

HF publishes separate `train` (1,000), `test` (500), `revision_1` (500), and
`revision_2` (500) splits under `v1/splits/`. Each HF record has only the eight
query/context/entity/feature/label fields; local canonical rows retain domain and
split for audit. Source revision-1/revision-2 map to HF revision_1/revision_2.

## v2 development

The `v2` branch is used for the next dataset version. Its separate project page
is maintained in [`docs/v2/index.html`](docs/v2/index.html), linked from the main
page. v2 dataset contents and results have not been released yet.

## Local project page

```bash
bash shells/serve.sh
# Optional port and bind address:
# bash shells/serve.sh 8080 0.0.0.0
```

Open http://127.0.0.1:8000/ for the main page or
http://127.0.0.1:8000/v2/ for v2. Stop the server with Ctrl+C.
