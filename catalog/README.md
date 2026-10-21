# Catalog

Catalog definitions are YAML; source-run results in `labels/` are JSON.
The active classes are bird, human, legal_case, mammal and plant.
Each class has `class.yaml`, `list.yaml` and `features.yaml`.

## Authored instances

```bash
bash shells/catalog/manual.sh
```

This generates IDs 0001–0100 for all five classes using the checked-in
`src/catalog/manual_instances.yaml`. Bird, mammal and plant each have 100 authored
names. Human uses 10 roles × 10 situations; legal_case uses 10 actions × 10
situations. These are fictional examples, not sourced observations or feature labels.
Bird includes common birds and exceptions such as penguins, ostrich, kiwi and kakapo.
Edit the seeds, then run the shell script. Preserve existing ID meanings and ordering.
The generator validates 100 unique names per class and preserves IDs above 100.

## CUB bird instances

```yaml
id: bird
name: Bird
revision: 6
collections:
- source: manual
  indices: [1, 100]
  script: shells/catalog/manual.sh
- source: cub_200_2011
  indices: [101, 300]
  script: shells/catalog/classes_bird_cub.sh
```

Collection indices are inclusive catalog slots, not source row numbers.
CUB original classes 1–200 map to bird_0101–bird_0300. Collection ranges must not overlap.
CUB and manual may contain the same display name; IDs distinguish their source collections.

```bash
bash shells/catalog/classes_bird_cub.sh
python -m src.catalog validate
```

The importer uses the complete small classes.txt file from the pinned public mirror
`pawlo2013/CUB` (commit 8a8486039c718e33d87b96ed42c0f457e6a7d939), validates its
SHA256 and uses the local cache when available. No images are downloaded.
Source-run sources.json retains original IDs/names, the catalog offset, checksum,
retrieval metadata and both original-project and mirror URLs. Manual slots are preserved.
Use `--classes /path/to/classes.txt` for a complete local input; this records local provenance.
Neither generator reads v1 at runtime or generates feature/group/task labels.

## List format

```yaml
class_id: bird
instances:
  bird_0001:
    name: House sparrow
  bird_0101:
    name: Black footed Albatross
```

Each key is the stable instance ID and each entry contains only name.
The source and slot range belong in class.yaml; detailed source-run metadata belongs
in labels. The current catalog contains 700 instances and 35 feature definitions.
Previous class JSON and the pre-migration bird list are archived locally under
runs/archive/manual-catalog-migration. Historical CUB runs retain their old bindings;
they are not provenance for the new manual slots. Frozen v1 releases remain unchanged.

## The seven experimental features

`features.yaml` preserves the original seven feature names:

- `is_large`
- `has_flight_wings`
- `has_developed_flight_plumage`
- `has_intact_wings`
- `is_rested`
- `has_unhealed_fracture`
- `has_severe_fatigue`

Definitions use stable feature IDs as keys, with explicit name and description:

```yaml
class_id: bird
features:
  bird_f_001:
    name: is_large
    description: How large the bird's body is relative to birds in general.
```

The seven features use stable IDs `bird_f_001` through `bird_f_007` in the order above.
Labels reference those IDs, not the names. Keep IDs stable when renaming a feature;
never reassign an ID to a different meaning. Duplicate IDs are rejected.

**The value encoding is undecided.** No numeric 0/0.5/1 scale, boolean encoding,
null policy or category set is imposed. Define `values` or `type` explicitly when
choosing the encoding. Until then the catalog can be loaded, but annotation writes
for these features are rejected rather than accepting an arbitrary scale.
Descriptions express the general meaning of each feature, without encoding a label
scale or a task-specific rule. Define any operational labeling criteria separately
when generating labels. Do not add implementation reminders to descriptions.

Measured body mass, developmental stage, fatigue, wing condition and other facts
are inputs for these judgments, not replacements for the seven features. Source
facts and constructed states retain their provenance in source-run metadata.
There is no separate state-definition layer or assumed default individual state.

Feature history belongs in Git; pin the catalog commit in source/release metadata.
Existing annotation revision fields remain supported with compatibility feature
revision 1, which alone does not identify a historical definition. Definition
snapshot/commit checks still need to be connected to future label generation and
release export.

## Source-specific labels and releases

Each real collection or execution gets a source folder. Create only the categories
it produces:

```text
labels/generated/<source_run>/
  sources.json
  features/bird.json
  tasks_per_context/fly.json
  groups/bird.json
```

Feature files map instance ID → feature ID → value; task files map instance ID →
context ID → value. Source and execution metadata live once in sources.json.
Generation scripts record selected classes, ID ranges, tasks, contexts and seed there.
New judgments or factual checks get a new source-run directory. Missing keys mean
uncollected values. See [label examples and generator options](../labels/README.md).

Groups are ID-to-membership mappings allowing multiple groups. CUB class-name
import does not invent taxonomic or ecological groups. Add those from an actual
separate source or inference run. The current import creates no feature labels,
no group claims and no context-specific task judgments. The seven experimental feature definitions are schemas,
not measurements imported from CUB. The five contexts have no generated task judgments.

Source-run results coexist without a preferred-model or latest-value rule. Release
preparation must choose exact sources, profiles, labels and groups, pin catalog
history and record sampling/splits. Release generation, HF upload and the website
are not yet connected to this structure. Existing release files are untouched.

## Alternative ConceptNet collection

The earlier ConceptNet collector remains available but is not the active source.
It requires source `conceptnet` and its script in class.yaml. Its initial selection
ranks positive English IsA bird children by unique direct child count, breaking
ties by URI. It supports complete cached API replay or a local official assertions
dump via `--offline` / `--assertions`. Its actual URI bindings and evidence stay in
source-run metadata. Do not run it against the current CUB IDs and reinterpret
them as different concepts. API 502 failures previously prevented its collection.

## Checks

```bash
python -m src.catalog validate
python -m src.catalog stats
python -m src.catalog feature-sources bird --output /tmp/bird-source-view.json
python -m unittest discover -s tests -v
bash -n shells/catalog/classes_bird_cub.sh
```

Only bird/fly use the new format. Other classes, tasks and legacy labels are
unchanged. Active collection does not read old v1 payloads; a local backup of the
former bird import remains under `runs/archive/bird-v1-import/`.

Original project: https://www.vision.caltech.edu/datasets/cub_200_2011/
Dataset report: https://authors.library.caltech.edu/records/cvm3y-5hh21
Public mirror: https://huggingface.co/datasets/pawlo2013/CUB
