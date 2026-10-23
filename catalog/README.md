# Feature catalog

CDR samples are feature combinations. Catalog definitions describe their meanings
and evaluation conditions; they do not enumerate named objects or store samples.

```text
<version>/classes/<class>.yaml            # ID, display name and feature definitions
<version>/tasks/<task>.yaml               # task, feature-group bindings and context descriptions
```

Classes are feature groups. A feature name identifies a predicate, not an object.
There is no list.yaml, instance ID registry, class/feature R/N grounding or universal
feature scale. A source run records its own value encoding and provenance.

```yaml
id: bird
name: Bird
features:
  bird_f_001:
    name: is_large
    description: How large the bird's body is relative to birds in general.
    labeling: null
```

Keep feature IDs stable when names change; do not assign an existing ID to a new
meaning. Contexts are keyed by ID with a description only. Task bindings explicitly
select applicable contexts for multi-class tasks. Missing evidence stays missing.

Source-run samples live under labels/generated/<source>/samples/<class>.json:

```json
{"sample_0001": {"bird_f_001": 0.8, "bird_f_002": true}}
```

This illustrates the storage shape, not a prescribed feature encoding. A sample
has no display name. Features absent from its map remain unknown. Provenance can
retain external identities for auditing, but those identities do not define the
sample and are excluded from task inference.

Run `python -m src.catalog validate` and `python -m src.catalog.web_assets` after
editing definitions. See [source generation](../docs/label_generation_script.md)
and [release management](../releases/README.md). Retired named catalogs and their collectors have been removed; historical frozen
v1 is unchanged.

Task labels use subjective-logic masses with exactly `yes`, `no` and `unknown`,
each in [0, 1] and summing to 1. Unknown is uncommitted uncertainty, separate from
an absent, ungenerated judgment. The schema is independent of feature encodings.

## Versions

Current definitions are in v1/classes/ and v1/tasks/. Keep future catalog changes
in separate v2/, v3/, etc. Only v1 exists today. Choose --catalog-version explicitly
when generating or exporting; omitted selection defaults to v1, never the latest.
Source runs freeze the selected version and record catalog_version, and label
runs use their sample source's frozen definitions. The catalog version is separate
from the historical versions/v1 dataset publication.

```bash
python -m src.catalog --catalog-version v1 validate
python -m src.catalog.web_assets --catalog-version v1
bash releases/v1/shells/run1_prepare_samples.sh --count 100 --seed 0
PYTHON=python bash releases/v1/shells/run1_prepare_labels.sh --backend vllm --model google/gemma-3-27b-it --dry-run
```
