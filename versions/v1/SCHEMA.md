# v1 public schema

```text
versions/v1/metadata/        # Git-tracked definitions
├── queries.json
├── contexts.json
└── features.json

data/v1/                    # Local dataset, Git ignored
├── samples.jsonl
└── source/                 # Preserved experimental snapshot

HF: v1/
├── data/                   # samples.jsonl and source snapshot
└── metadata/               # Definitions, manifest, statistics, release notes
```

Each JSONL line contains:

| Field | Meaning |
| --- | --- |
| `query_id`, `query_str` | Stable target ID and natural-language question |
| `context_id`, `context_str` | Descriptive context ID and complete source context |
| `entity_id`, `entity_name` | Anonymous underscore ID and original catalog identity |
| `feature_values` | Raw stipulated profile fields, source species where available, and seven original experimental judgments |
| `label` | String `"true"` or `"false"`, mapped from original 1/0 |
| `domain` | One of the five domains |
| `split` | Original train/revision-1/revision-2/test assignment |

Names and species come from the input catalog, not invented nicknames. Human and
legal-case names describe fictional profiles. Revealing original identities and
raw features makes this public representation richer than the anonymous prompts
used in the experiments. To reproduce those experiments, use the preserved
`source/labels/gpt-5.4/student` exports, not a new prompt built from every public field.

Bird contexts keep distance as well as moisture: `dry_20m`, `dry_500m`, `wet_20m`,
`dry_5m`, `wet_500m`. They must not collapse to one `dry_condition` because the
flight task differs. The source's c_1–c_5 IDs are retained in context metadata.
Wet/dry conditions belong to the context; they are not added to fixed entity
features. Full context wording is preserved, rather than a shortened paraphrase.

Queries and contexts are listed once in their metadata files and their text is
also present in samples as requested. Feature definitions are **only** in
`features.json`, not repeated in each sample. Each feature entry has `feature_id`,
`feature_str`, `possible_values`, and `domain`. Resolve features by domain plus ID.
`possible_values` enumerates observed v1 values, including null where present;
0.5 remains an ambiguous judgment, not a target label or calibrated probability.

```bash
python versions/v1/generation/export_public.py --source data/v1 --output data/v1
python evaluation/evaluate.py --data data/v1 --output runs/v1/evaluation.json
bash shells/huggingface.sh --version v1 --dry-run
```

```python
from datasets import load_dataset
train = load_dataset('leo-bjpark/CDR-Dataset', 'v1', split='train')
test = load_dataset('leo-bjpark/CDR-Dataset', 'v1', split='test')
```

HF publishes separate `train` (1,000), `test` (500), `revision_1` (500), and
`revision_2` (500) splits under `v1/splits/`. Each HF record has only the eight
query/context/entity/feature/label fields; local canonical rows retain domain and
split for audit. Source revision-1/revision-2 map to HF revision_1/revision_2.
