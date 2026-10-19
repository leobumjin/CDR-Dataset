# Repository layout and versioning

Git tracks code and metadata grouped by dataset version. Actual dataset payloads
are local under `data/` and distributed through Hugging Face version tags.

```text
CDR-Dataset/
├── versions/
│   ├── registry.json              # Registered versions and latest stable version
│   └── v1/
│       ├── README.md              # Release notes, provenance, limitations
│       ├── manifest.json          # Data and generator checksums
│       ├── statistics.json
│       ├── huggingface.json       # Created after successful HF publication
│       └── generation/
│           ├── src/               # Version-specific generation source and prompts
│           ├── configs/           # Catalogs and source license
│           ├── requirements.txt
│           ├── run.py
│           └── README.md
├── shells/
│   ├── huggingface.sh              # HF command entrypoint
│   ├── evaluate.py                # Local data integrity and distribution checks
│   ├── release.py                 # Offline checksum verification and restoration
│   └── huggingface.py             # Prepare, upload, and download
├── docs/                          # Website and shared documentation
├── data/v1/                       # Local/downloaded dataset; Git ignored
├── runs/                          # Generation, evaluation, staging; Git ignored
├── requirements-huggingface.txt
└── README.md
```

Only v1 exists today. Future versions use `versions/v2`, `versions/v3`, etc.
Generation source and data do not share a directory: code is tracked, payloads
are not. The HF repository has version tags v1/v2/v3, rather than cumulative
version folders. `huggingface.json` appears only after actual publication.

## Local generation and evaluation

Run from the repository root:

```bash
python -m pip install -r versions/v1/generation/requirements.txt
python versions/v1/generation/run.py inputs --run trial-001
# Continue feature/label generation and final splitting as documented in:
# versions/v1/generation/README.md
python shells/evaluate.py --data data/v1 --output runs/v1/evaluation.json
python shells/release.py verify v1
bash shells/huggingface.sh prepare --version v1
```

Offline verification and restoration need no HF token. Generation into `runs/`
does not modify frozen data or metadata. Dataset evaluation here is an integrity
and distribution audit; model training/evaluation is an independent local task.

## Develop and publish v2 or v3

1. Create `versions/v2/generation` from the previous version's generation code.
   Update its runner's version paths, then change only the new copy. Archive
   prompts, configs, dependency requirements, and generation settings there.
2. Generate into a fresh `runs/v2/<run-name>` and evaluate locally. Record the
   parent version and changes. Never write new output over `data/v1`.
3. Copy accepted data to local `data/v2`. Preserve raw annotations and metadata.
   Add `versions/v2/README.md` and `statistics.json` with changes and limitations.
4. Write `versions/v2/manifest.json` using the v1 schema. Record SHA-256 for
   every file in `data/v2` and `versions/v2/generation` except Python caches;
   paths are relative to the repository root. Record provenance and teacher.
5. Register v2 in `versions/registry.json` with `data`, `pipeline`, `manifest`,
   `primary_teacher`, and status. Verify with `python shells/release.py verify v2`.
6. Run `bash shells/huggingface.sh prepare --version v2`, inspect the payload,
   then explicitly upload with `upload --version v2 --repo-id leo-bjpark/CDR-Dataset`.
7. Commit the code, metadata, and resulting `versions/v2/huggingface.json` receipt.
   Data stays out of Git. Advance the registry's `latest` after acceptance.

Published data, generation code, labels, contexts, splits, and prompt text stay
frozen together. New revisions receive a new version; published HF tags are never
moved. Experiments pin the version and HF commit SHA instead of `main` or `latest`.

See [Hugging Face workflow](huggingface.md) for details.
