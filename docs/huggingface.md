# Local generation, evaluation, and Hugging Face releases

Git tracks version-specific generation code, configs, requirements, release notes,
statistics, checksums, and HF commit receipts. `data/` and `runs/` are local and
ignored. The HF dataset repository contains the data; tags v1, v2, v3 identify
releases within that one repository.

## Local work

Run commands from the CDR-Dataset repository root. Generation code remains in
`versions/v1/generation`; its README describes fresh API generation into `runs/v1/<name>`.
The imported experimental v1 remains in local `data/v1`.

```bash
# Evaluate an experimental working directory, independently of uploading.
python shells/evaluate.py --data runs/v1/my-run --output runs/v1/my-run-evaluation.json
# Or evaluate the imported release.
python shells/evaluate.py --data data/v1 --output runs/v1/release-evaluation.json
python shells/release.py verify v1
```

Evaluation here means offline data integrity/distribution checks, not model
benchmark evaluation. Training and model evaluation can consume local data
without contacting Hugging Face. Accepted future datasets need their own local
`data/v2`, generation pipeline, manifest, registry entry, and release statistics.
Never replace the frozen v1 snapshot with new generation results.

## Prepare without a token or network

```bash
bash shells/huggingface.sh
bash shells/huggingface.sh prepare --version v1
# Equivalent offline upload preview:
bash shells/huggingface.sh upload --version v1 --dry-run
```

The script verifies all release data/pipeline checksums and evaluates the dataset,
then stages a clean payload in `runs/huggingface/v1/`: data, dataset card,
manifest, statistics, evaluation, and release notes. It excludes credentials,
working runs, and generation source. Generation source stays in GitHub.

The HF dataset card explicitly selects each teacher's canonical `dataset.jsonl`,
so auxiliary raw annotations and student exports are not loaded as extra examples.
Each teacher config has one `all` split and retains the original `split` column.

## Default repository and versions

The default dataset repository is `leo-bjpark/CDR-Dataset`:
https://huggingface.co/datasets/leo-bjpark/CDR-Dataset

`bash shells/huggingface.sh upload --version v1` publishes tag `v1` there.
Future `--version v2` and `--version v3` publish new tags in that same repository,
after local version metadata and data have been prepared. Existing tags are not
replaced. Override the repository with `--repo-id` or `HF_REPO_ID`.

## Prepare and upload in one command

```bash
bash shells/huggingface.sh --version v1
# Offline preparation only:
bash shells/huggingface.sh --version v1 --dry-run
```

The short form runs the same upload workflow: verify, evaluate, prepare, upload,
then tag the exact commit. Authentication is required for actual upload.
Explicit `prepare`, `upload`, and `download` subcommands remain supported.

## Upload explicitly

```bash
python -m pip install -r requirements-huggingface.txt
hf auth login
bash shells/huggingface.sh --version v1
# For a newly created public repository, add --public.
```

Alternatively set `HF_TOKEN` and `HF_REPO_ID` in the shell environment. Tokens
are never command-line arguments or written into generated artifacts. The root
`.env` is not automatically sourced. No API generation happens during upload.

New repositories default to private; existing repository visibility is preserved.
The upload replaces the managed `data/`, `metadata/`, and README on HF `main`,
removing stale files within the first two paths. Other remote paths are untouched.
It then creates the version tag pointing to the exact upload commit. Previous
release tags are never moved or overwritten. If upload succeeds but tagging fails,
inspect the remote commit and finish tagging that commit before retrying publication.

A successful upload writes `versions/v1/huggingface.json` with the repository,
version, commit SHA, and URL. Commit this receipt with the matching generation
code and manifest. The receipt is written only after successful tagging.

## Download a frozen release

From a clone with no local `data/v1`:

```bash
bash shells/huggingface.sh download --version v1 --repo-id leo-bjpark/CDR-Dataset
```

Download pins the receipt's commit SHA when available, otherwise the version tag.
It validates the payload against the Git-tracked release checksums before copying
it into local `data/v1`. Existing destinations are never overwritten. The HF cache
is managed by huggingface_hub; large files are not added to GitHub.

After publication, users can also load a teacher config directly:

```python
from datasets import load_dataset
rows = load_dataset('leo-bjpark/CDR-Dataset', 'gpt-5.4', revision='v1', split='all')
train = rows.filter(lambda row: row['split'] == 'train')
```
