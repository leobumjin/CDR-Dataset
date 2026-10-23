# Local work and Hugging Face configs

Generation code, configs, requirements, statistics, checksums, and publication
receipts stay in Git. Dataset payloads in `data/` and working outputs in `runs/`
are ignored. Run commands from the CDR-Dataset repository root.

## Generate and evaluate locally

See `versions/v1/generation/README.md` for the archived generation pipeline.

```bash
python evaluation/evaluate.py --data data/v1 --output runs/v1/evaluation.json
python tools/release.py verify v1
```

Evaluation checks data integrity and distributions, not model performance.

## Prepare and upload

```bash
python -m pip install -r requirements-huggingface.txt
hf auth login
# Offline verification, evaluation, and staging only:
bash tools/huggingface.sh --version v1 --dry-run
# Prepare and publish publicly:
bash tools/huggingface.sh --version v1
```

The default repository is https://huggingface.co/datasets/leo-bjpark/CDR-Dataset.
Override it with `--repo-id` or `HF_REPO_ID`. Authentication can use `hf auth login`
or the `HF_TOKEN` environment variable; the root `.env` is not sourced.
Explicit `prepare`, `upload`, and `download` subcommands remain supported.

Versions are **dataset configs**, not Git tags:

```text
HF: leo-bjpark/CDR-Dataset
├── README.md               # configs: v1, v2, ...
├── v1/
│   ├── data/               # GPT-5.4 data for v1
│   └── metadata/           # Manifest, statistics, evaluation, release notes
└── v2/                     # Added when a v2 release exists
```

Preparation verifies local hashes, evaluates the data, and stages the selected
version in `runs/huggingface/v1`. The card explicitly selects `data/samples.jsonl` records;
raw annotation files are not interpreted as additional dataset examples.

Upload creates or updates the chosen version folder and merges its config into
the existing dataset card. Other configs and version folders remain intact.
Only files under the selected version can be removed as stale payloads.
Uploads use the observed parent commit to reject concurrent remote changes.
Existing old Git tags neither block uploads nor get modified. Legacy teacher/default
configs are replaced by version configs during migration. Old unversioned data
files are left untouched but no longer selected by the card.

The repository is public. The exact resulting commit is recorded in
`versions/v1/huggingface.json`, together with `config: v1`. Commit that receipt
with the matching metadata and code. Running the command again updates that config;
use a new config for substantive future dataset changes. For exact reproducibility,
record the commit SHA as well as the config name.

## Load data

```python
from datasets import load_dataset

train = load_dataset('leo-bjpark/CDR-Dataset', 'v1', split='train')
test = load_dataset('leo-bjpark/CDR-Dataset', 'v1', split='test')
# Future release:
# data = load_dataset('leo-bjpark/CDR-Dataset', 'v2', split='train')
```

`revision` is optional and pins an HF Git commit; it is separate from the v1 config.

## Download local files

```bash
bash tools/huggingface.sh download --version v1
```

Download uses the recorded config publication's commit SHA when available,
otherwise `main`, and reads `v1/data`. It checks every file against the local
Git-tracked manifest before copying to `data/v1`. Existing local data is never
overwritten. Old tag-based receipts are not used to locate config payloads.

The public schema and feature metadata are documented in [v1 schema](../versions/v1/SCHEMA.md).

HF publishes separate `train` (1,000), `test` (500), `revision_1` (500), and
`revision_2` (500) splits under `v1/splits/`. Each HF record has only the eight
query/context/entity/feature/label fields; local canonical rows retain domain and
split for audit. Source revision-1/revision-2 map to HF revision_1/revision_2.
