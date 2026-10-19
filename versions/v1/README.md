# CDR-Dataset v1

Imported on 2026-10-19 from the AISTATS experimental snapshot `data/current`.
This release numbering is independent of the workspace's historical `data/v1`
and `data/v2-bird-legal` directories.

- Primary reference: `data/v1/labels/gpt-5.4/dataset.jsonl`.
- v1 uses GPT-5.4 references only: 500 instances and 2,500 context pairs.
- Hugging Face exposes one dataset configuration named `v1`; no teacher name is needed.
- Five domains; 100 instances per domain; 5 contexts and 7 features per domain.
- Split: train 1,000; revision-1 500; revision-2 500; test 500 pairs.
  Each instance's five contexts stay together. Validation exports are empty.
- Target labels: 0/1. Feature judgments: 0/0.5/1.
- Four student prompt variants are preserved. Main experiments used
  `feature_present` and the GPT-5.4 reference.
- Teacher-generated reference labels; recorded human reviews: 0.
- Test contains some feature vectors also present in train; the split holds out
  instances, not necessarily species or feature configurations.

`manifest.json` inventories the release data and its pipeline with SHA-256 hashes.
`statistics.json` contains the computed GPT-5.4 statistics, context counts,
feature overlap, export consistency checks..

Input definitions, feature annotations, teacher responses, run settings, assembly
provenance, and all student exports are retained under `data/v1`. No labels or
split assignments were changed during import. Empty historical exports and
historical paths are preserved intentionally.

No dataset-wide license is inferred from this import. The archived config license
applies to its referenced source material; choose a dataset license before
claiming a general reuse grant.
