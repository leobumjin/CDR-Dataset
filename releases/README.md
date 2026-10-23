# Feature-sample releases

A release freezes explicitly selected sample feature vectors and optional task
labels. Samples are defined by features, not real object names. N/R/R² release
families are retired. Feature origin and task-label generation/review provenance
are independent; constructed samples may have AI-generated judgments.

```text
releases/<version>/
  shells/                               # version-specific execution entrypoints
  scripts/                              # feature sampling and LLM task labeling
  meta_info.json
  catalog/                              # frozen semantic definitions
  samples/<class>.json                   # sample ID -> feature ID -> value
  labels/tasks_per_context/<task>.json   # optional sample ID -> context ID -> label
```

Current metadata uses format feature_samples_v1 and status planned, in_progress,
ready or released. Ready/released snapshots require a catalog commit, source
checksums, frozen definitions and artifact checksums. There is no required task
label coverage and no assumed feature encoding. Missing labels stay missing.

Assemble a new local release only from explicit source IDs:

```bash
python -m src.catalog.releases \
  --release-id v2 \
  --sample-source sample_run \
  --label-sources task_run \
  --catalog-commit <catalog-commit>
```

The IDs above are placeholders, not existing releases. Omit --label-sources for a
feature-only release. Label sources must resolve to the exact selected sample
vectors; overlapping judgments are rejected instead of implicitly choosing a
source. Source checksums and separate sample/label provenance are retained.
Frozen definitions, rather than later live catalog edits, interpret release data.
Existing release snapshots cannot be overwritten. A directory containing only
scripts/ and shells/ may receive its first snapshot; generation code is preserved. Assembly does not publish or
upload anything. Use `python -m src.catalog releases` to validate snapshots and
`python -m src.catalog.web_assets` to refresh public JSON after assembly.

releases/v1 currently contains generation code, not a published feature-sample snapshot. Historical versions/v1
and data/v1 remain unchanged and are not reinterpreted as feature-sample releases. New source runs are never a fallback for unavailable releases.

Task labels contain exactly three subjective-logic masses: yes (support), no
(opposition), unknown (uncommitted uncertainty). Each is a finite number in [0, 1]
and their sum must be 1 within 1e-9. task_label_schema records this contract.
Invalid opinions are rejected, not silently normalized. Absent labels remain
separate from explicit full uncertainty {yes: 0, no: 0, unknown: 1}.
