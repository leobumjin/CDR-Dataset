# Tasks and contexts

Each flat <task>.yaml file contains task metadata, bindings and context definitions. Bindings specify how a
feature group is evaluated, with explicit context IDs when a task spans groups.
A task judgment evaluates a sample's feature values under the selected context.
No object name or real-world identity is required or supplied to inference.

Optional labels live in labels/generated/<source>/tasks_per_context/<task>.json,
keyed by sample ID and then context ID. Label-only runs explicitly reference their
sample source and checksums. Missing evidence remains an absent key. AI-generated
and human judgments record their generation method and review status independently
of how sample features were obtained.

The class browser presents task and context definitions through its Task-Context tab. Classes without task bindings have an empty state. There is no
separate Task–Context page. Download Info includes task and context definitions; release_samples.json contains
selected frozen samples/labels.
Regenerate assets with `python -m src.catalog.web_assets`.

Every task judgment is an opinion object, for example
`{"yes": 0.7, "no": 0.2, "unknown": 0.1}`. All three components are required,
finite and in [0, 1], with sum 1. Unknown denotes uncertainty, not a third world
outcome. A completely uncommitted judgment is {yes: 0, no: 0, unknown: 1}; no
judgment produced is an absent key. Scalar yes/no/unknown labels are not accepted.
