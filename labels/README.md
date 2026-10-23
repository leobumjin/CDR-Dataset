# Feature sample sources and task labels

Current source runs explicitly declare `format: feature_samples_v1` in sources.json.
Each sample is an anonymous feature combination, referenced by a source-scoped ID.
There is no catalog instance list and no per-sample name.

```text
labels/generated/<run>/
  sources.json                    # encoding, selections, generation/review provenance
  catalog/                        # frozen feature/task/context definitions
  samples/<class>.json            # sample ID -> feature ID -> value
  tasks_per_context/<task>.json    # optional sample ID -> context ID -> judgment
```

A task-only run references sample_source plus sample_source_sha256 rather than
copying feature values. SourceRun resolves and validates that reference explicitly.
No source is automatically preferred. Source IDs are immutable; use a new ID for
another execution. Sample IDs need only be unique inside the resolved source.

Feature values have no default scale. Source feature_encoding can specify a value
list; missing features must remain absent. Task values contain exactly yes, no and
unknown masses in [0, 1], summing to 1 (tolerance 1e-9). Missing judgments remain
absent; explicit unknown mass 1 represents an opinion with full uncertainty. Constructed samples can receive
AI-generated task labels. Generation method and review status are distinct metadata;
verified labels require evidence references.

Old named source runs remain historical and require explicit migration. Retired named-catalog examples and generators have been removed.
No historical values are silently assigned to new samples. Generated runs remain
ignored and do not appear on the website until explicitly selected into a release.
See [generation](../docs/label_generation_script.md) and [releases](../releases/README.md).

```json
{"sample_0001": {"dry_20m": {"yes": 0.7, "no": 0.2, "unknown": 0.1}}}
```

This task-label schema is mandatory in model prompts, generated sources and
releases; source metadata also records task_label_schema.
