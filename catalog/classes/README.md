# Classes

`bird`, `human`, `legal_case`, `mammal`, and `plant` use:

- `class.yaml`: collection sources, catalog ID ranges and scripts.
- `list.yaml`: class_id and instances keyed by ID, with name only.
- `features.yaml`: seven v1 experimental feature names with stable class_f_001 IDs; value encoding undecided.

Run `bash shells/catalog/manual.sh` to generate the authored 1–100 slots in all five classes.
Run `bash shells/catalog/classes_bird_cub.sh` to populate bird 101–300 from all 200 CUB classes.
Source-specific metadata and labels belong under `labels/`.

See [catalog storage](../README.md).
