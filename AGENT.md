# Data management guide

Keep repository documentation in English. Separate catalog definitions, source-run
results and release exports. The active classes are bird, human, legal_case, mammal
and plant; the active tasks are fly, run, guilt and survive.

## Concepts and storage

- Class and instance describe a category and its entries. A species name does not
  establish the fatigue, injury or other state of an observed individual.
- Task is independent of class: Flying is a task, while Bird–Flying is a binding.
- Features define characteristics; labels store values and judgments separately.
- Context specifies the conditions under which a task is evaluated.
- A source directory represents one collection, inference or verification run.
- A release explicitly selects results from source runs. Do not automatically prefer
  the latest source or a particular model.

```text
catalog/                         # YAML definitions; tracked
  classes/<class>/
    class.yaml                   # collection sources, ID ranges, scripts
    list.yaml                    # class_id and instances keyed by ID
    features.yaml                # feature IDs with name and description
  tasks/<task>/
    task.yaml                    # task and class bindings
    contexts.yaml                # class-specific task conditions
src/catalog/                     # catalog validation and collection code
src/labels/random_label.py       # random template generator
shells/catalog/                  # catalog generation entrypoints
shells/labels/random_label.sh    # label generation entrypoint
labels/generated/<source_run>/             # source-specific JSON results
  sources.json                   # shared source metadata and selection settings
  features/<class>.json          # instance ID -> feature ID -> value
  tasks_per_context/<task>.json   # instance ID -> context ID -> value
  groups/<class>.json            # item ID -> group membership list
releases/<version>/               # future selected, clean exports
runs/                            # local execution and archive files; ignored
data/                            # source caches and frozen payloads; ignored
```

There is no active catalog/labels directory. Create result categories only when
that source actually produces them. Preserve missing values as missing keys;
absence does not mean false, ambiguous or an explicit unknown.

## Catalog IDs and generation

Instance definitions contain only their display name:

```yaml
class_id: bird
instances:
  bird_0001:
    name: House sparrow
```

The key is the stable ID. Never reuse an existing ID for a different meaning or
reorder authored seeds in a way that reassigns IDs. Source and range declarations
belong in class.yaml; detailed provenance belongs in sources.json, not list.yaml.

Each class reserves 0001–0100 for authored instances. Edit the checked-in seeds in
src/catalog/manual_instances.yaml, then run:

```bash
bash shells/catalog/manual.sh
```

Bird, mammal and plant each have 100 named examples. Human uses ten roles crossed
with ten situations; legal_case uses ten actions crossed with ten situations.
These are authored examples, not verified observations. Include ordinary cases and
exceptions. Manual generation preserves slots above 100 and creates no labels.

Bird also reserves 0101–0300 for CUB-200-2011 original classes 1–200:

```bash
bash shells/catalog/classes_bird_cub.sh
```

Collection indices are inclusive catalog ID ranges. Ranges within a class must not
overlap. The CUB collector adds 100 to original class IDs, preserves manual slots,
checks the pinned source checksum and records original IDs, names, mirror revision,
URLs and offset in source metadata. Local input files retain local provenance.
Do not describe CUB class names as verified feature or ecological observations.

The current definitions have 700 instances and 35 features. Previous class JSON
and the pre-migration bird list are archived in runs/archive/manual-catalog-migration.
Historical CUB bindings for IDs 1–100 do not describe the new manual entries.
The inactive ConceptNet collector remains an alternative implementation; it must
not reinterpret existing CUB or manual IDs.

## Features

Each class has seven experimental features from v1. Feature keys use the
<class>_f_001 format, with three digits. Keep IDs stable when names change.
Each feature contains name and description; do not repeat its ID or revision inside.
Duplicate IDs/names and missing names/descriptions are validation errors.

Descriptions explain general characteristics rather than temporary label encoding
or reminders about future implementation. Keep definitions separate from values.
The formal feature encoding is undecided: do not impose a 0/0.5/1, boolean or null
policy on the catalog. Add values or type only after the encoding is chosen.
Normal feature annotation remains blocked until that schema is configured.

Species traits and individual states have different scopes. Preserve that scope
and evidence in source metadata. Do not invent observations, fill missing facts
from similarly named species, or infer flight ability solely from taxonomy.
There is no separate states.yaml layer or automatic default individual state.

Definition history belongs in Git. Record the catalog commit used by inference
and release workflows when implementing those workflows. Existing compatibility
revision fields alone do not identify a historical feature definition.

## Label generation

Read [the label generation guide](docs/label_generation_script.md) before
changing a generator, ID selection or template format. It documents all sample
(instance) ID ranges, feature ID ranges, task/context IDs, CLI options and examples.
Keep that guide synchronized with scripts and catalog definitions.

Successful generation scripts write website metadata to separate JSON registries:

- `docs/assets/catalog_generation_scripts.json`: manual and cub entries.
- `docs/assets/label_generation_scripts.json`: random_label and future label generators.

Each script updates only its own entry after validation succeeds. Keep entries
concise, with script paths and execution selections. Do not combine catalog and
label metadata or hand-maintain large catalog snapshots. Failed runs leave the
registries unchanged. Null range filters mean all available IDs. Label metadata contexts maps task IDs
to actual generated context ID lists, even when the CLI context filter was omitted. Keep metadata in
English. Prose guides belong under docs/; page assets belong under docs/assets/.

```bash
bash shells/labels/random_label.sh \
  --classes human \
  --instance-range 1 100 \
  --feature-range 1 7 \
  --tasks run \
  --seed 0
```

The default output is labels/generated/random_label, with no date suffix. Re-running
regenerates that template. Other --source-id values must be new and are not
silently overwritten. Filters use inclusive numeric ID suffixes. Omitted filters
use the generator’s explicit manual scope (instances 1–100, features 1–7, and
configured task/context IDs); --tasks with no IDs selects features only.

Store class/range/task/context selections and seed once in sources.json. Feature
JSON maps instance ID to feature ID to value; task JSON maps instance ID to context
ID to value. Do not repeat source, record ID, revision, status, timestamp or provenance
for every value. Source and class/task are resolved from directories and filenames.
Legacy assertion arrays remain readable; the legacy append API must not modify
compact source snapshots.

Random templates independently sample feature values from 0, 0.5 and 1, and task
values from the strings true, false and ambiguous. This encoding is local to the
synthetic template source; it does not set the formal catalog encoding. Random
values are not observations, model inference, factual checks or inferred task answers.
The same seed, selection and catalog reproduce values. The default manual selection produces
3,500 feature values and 2,500 task values.

## Sources, updates and groups

Create a source folder only for an actual collection or execution. sources.json.id
must match its directory. Store available URLs, versions, checksums, retrieval times,
raw snapshots, transformation settings and selection rules there. For model runs,
record actual model identity, prompt/input references and execution settings.
Keep imported facts, constructed examples, model judgments and factual reviews distinct.
Do not manufacture provenance or mark imports as fact-checked automatically.

New judgments or factual checks belong in new source-run directories. Select the
needed sources at release time; do not silently choose the latest value. Preserve
actual evidence and verification details in source metadata.

Group results map each item to a list of objects containing group_id. Multiple
memberships are allowed. Declare referenced groups in the same file; duplicate
memberships, unknown groups and cycles are invalid. A catalog ID-to-concept binding
is distinct from an observed ConceptNet IsA edge.

Task definitions belong in task.yaml, with class-specific bindings and questions.
Context definitions belong in contexts.yaml as an ID-keyed mapping with description
only. Do not repeat class_id or revision in context definitions. A single-class task
applies all its contexts to that binding. For multi-class tasks such as survive,
each task.yaml binding lists its context IDs in contexts; do not infer applicability
from an ID prefix. Reject unknown or unbound context IDs. Definition history belongs
in Git. Keep task and context identities stable.
Changing definitions must not automatically transfer old judgments to new meanings.

## Releases and scope

Keep existing versions/v1 and data/v1 exports unchanged. Runtime catalog generators
must not depend on v1 imports. Release preparation should explicitly record catalog
history, selected source IDs/checksums, selected profiles/results, sampling and splits.
The new release exporter and hosting integrations are not implemented yet.
Do not claim they exist or publish/upload without a corresponding user request.
When only schemas or documentation are requested, do not run source collection,
model inference or large downloads. Report validation failures without replacing
missing evidence with invented data.

## Git tracking

Track catalog/, labels/README.md and labels/generated/random_label/. Ignore other generated
labels/ directories and write locks. Keep runs/ and data/ local. Use a new source ID
for separate executions while retaining random_label as the checked-in example.

## Validation and references

Run checks appropriate to the change from the repository root. Documentation-only
changes do not require regenerating catalogs or labels.

```bash
python -m src.catalog validate
python -m unittest discover -s tests -q
bash -n shells/catalog/manual.sh shells/catalog/classes_bird_cub.sh
bash -n shells/labels/random_label.sh
```

Catalog validation requires the referenced source-run metadata. If CUB metadata is
missing, report the missing binding; do not fabricate a replacement source history.

- [Catalog storage](catalog/README.md)
- [Label storage](labels/README.md)
- [Label generation and ID ranges](docs/label_generation_script.md)
- [Release preparation](releases/README.md)

The random label generator is restricted to manual instance suffixes 1–100 and
feature suffixes 1–7. CUB instances are excluded, including explicit requests above
100. DEFAULT_CLASSES and DEFAULT_CONTEXTS explicitly bound the default selection;
new catalog contexts do not silently enter generation. Website label metadata must
record concrete instance/feature ranges and task-to-context lists, never null ranges.

## Static website

The repository website is served from docs/. Keep the visible interface in English.
The home page shows class/task combination cards and links to docs/instances/index.html and
docs/task-context/index.html pages. Keep instance and context browsing off the home
page. Preserve class and task filters in cross-page URLs. Frozen releases and
illustrative examples are presented separately.
`docs/assets/catalog.json` is exported from YAML definitions by src/catalog/web_assets.py.
Successful manual and CUB catalog generation refresh this asset automatically.
After direct definition edits, run `python -m src.catalog.web_assets`.
The browser reads this snapshot and the separate label/catalog script metadata.
Never display random template judgments as factual answers. Keep legacy example tab
selectors scoped to their own component to avoid interfering with catalog tabs.
Preview locally with `bash shells/serve.sh`; publishing is a separate action.

The Instances page uses a left-hand selectable list and a right-hand feature table
with a separate aligned label-value column. Source selection is explicit. Show NA
for absent or null values and preserve numeric zero as a real value. Display a
synthetic notice for random_label. At narrow widths stack the list above details.
`docs/assets/instance_labels.json` and task_labels.json publish only releases defined
under releases/<version>/meta_info.json and releases/<version>/labels/. Generated
random labels must never appear on the website. Release metadata explicitly selects
classes, instance_range, feature_range and task-to-context IDs; filter website
instances and features to that scope. Current v1 labels are unavailable, so every
value is NA. This is not a migration or reinterpretation of historical v1 payloads.
Running `python -m src.catalog.web_assets` refreshes the public assets.

On the Instances page, keep search above the left-hand instance list. Use labeled
class icon buttons (including All) with aria-pressed selection state. Preserve the
search input DOM while refreshing results so typing focus is retained. Label source
selection stays above the workspace; Task–Context page class filters remain independent.

Keep instance detail rows compact: show feature names and values by default, with
feature IDs/descriptions in hover/focus tooltips. Do not use expandable toggles.
Tooltips must remain hoverable and support Escape dismissal. Keep the instance title and
ID together. Use the global sr-only class for table captions so accessible captions
do not add visible repeated headings.

The dedicated docs/task-context/index.html page selects class, task, context and
source to browse sample judgments. Bind task/context options to the chosen class;
never infer class applicability from context ID prefixes. Show missing judgments
as NA. Hover/focus tooltips show instance identity and source-specific features;
keep tooltips hoverable and dismissible with Escape. Sample links open the selected
instance detail. Mark synthetic template results clearly. The page reads
`docs/assets/task_labels.json` and instance_labels.json, both exported only from releases/, using each version’s explicit scope.

The old docs/contexts/ definitions-only page has been removed. Route context
browsing and task links to docs/task-context/; do not restore the duplicate page.

Keep detailed task definitions, aggregate catalog counts and label-generation
summaries off the home page. Retain the class/task combination cards, links to
Instances and Task–Context, reasoning examples and released dataset information.

## Generated results and release selections

Generated results live under labels/generated/<script_name>/; defaults are
random_label and classes_bird_cub. Separate custom run IDs may be specified.
Release metadata lives at releases/<version>/meta_info.json. Compact selected
feature/task values belong in releases/<version>/labels/features/<class>.json and
labels/tasks_per_context/<task>.json. Do not use labels/released/ or a root release/.
Track the generated random_label example and release definitions; other generated
runs remain ignored. The website selects actual release versions, preserving
release choice across links. Show NA for unavailable or missing values and never
substitute generated templates. Add v2 only when its metadata actually exists.
