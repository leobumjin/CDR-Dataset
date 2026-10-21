# Label generation script

Use `shells/labels/random_label.sh` to generate compact feature and task label templates.
The implementation is `src/labels/random_label.py`. Run commands from the repository root.

## Sample and feature ID ranges

Sample ID means instance ID. All ranges below include both endpoints.

| Class | Manual sample IDs | Additional sample IDs | Feature IDs | Task |
| --- | --- | --- | --- | --- |
| `bird` | `bird_0001`–`bird_0100` | `bird_0101`–`bird_0300` (CUB) | `bird_f_001`–`bird_f_007` | `fly` |
| `human` | `human_0001`–`human_0100` | None | `human_f_001`–`human_f_007` | `run` |
| `legal_case` | `legal_case_0001`–`legal_case_0100` | None | `legal_case_f_001`–`legal_case_f_007` | `guilt` |
| `mammal` | `mammal_0001`–`mammal_0100` | None | `mammal_f_001`–`mammal_f_007` | `survive` |
| `plant` | `plant_0001`–`plant_0100` | None | `plant_f_001`–`plant_f_007` | `survive` |

CUB original class IDs 1–200 map to bird sample IDs 101–300. Manual samples include
ordinary examples and exceptions. Names and scenarios are not feature labels.
The full catalog contains 700 samples. This generator selects only the 500 manual
samples: 3,500 feature values and 2,500 task values. CUB samples are excluded.

## Feature IDs

### bird

| Feature ID | Name |
| --- | --- |
| `bird_f_001` | `is_large` |
| `bird_f_002` | `has_flight_wings` |
| `bird_f_003` | `has_developed_flight_plumage` |
| `bird_f_004` | `has_intact_wings` |
| `bird_f_005` | `is_rested` |
| `bird_f_006` | `has_unhealed_fracture` |
| `bird_f_007` | `has_severe_fatigue` |

### human

| Feature ID | Name |
| --- | --- |
| `human_f_001` | `has_5km_endurance` |
| `human_f_002` | `can_sustain_10kmh` |
| `human_f_003` | `has_unrestricted_mobility` |
| `human_f_004` | `is_rested` |
| `human_f_005` | `has_uphill_training` |
| `human_f_006` | `has_regular_training` |
| `human_f_007` | `has_100m_endurance` |

### legal_case

| Feature ID | Name |
| --- | --- |
| `legal_case_f_001` | `caused_property_damage` |
| `legal_case_f_002` | `intentional_damage` |
| `legal_case_f_003` | `property_belongs_to_another` |
| `legal_case_f_004` | `has_owner_consent` |
| `legal_case_f_005` | `necessary_to_prevent_imminent_harm` |
| `legal_case_f_006` | `has_lawful_authorisation` |
| `legal_case_f_007` | `within_official_scope` |

### mammal

| Feature ID | Name |
| --- | --- |
| `mammal_f_001` | `is_large` |
| `mammal_f_002` | `is_cold_adapted` |
| `mammal_f_003` | `is_heat_adapted` |
| `mammal_f_004` | `is_drought_adapted` |
| `mammal_f_005` | `is_adult` |
| `mammal_f_006` | `is_healthy` |
| `mammal_f_007` | `has_adequate_energy_reserves` |

### plant

| Feature ID | Name |
| --- | --- |
| `plant_f_001` | `is_succulent` |
| `plant_f_002` | `is_fern` |
| `plant_f_003` | `has_established_roots` |
| `plant_f_004` | `is_healthy` |
| `plant_f_005` | `has_moist_soil` |
| `plant_f_006` | `has_succulent_leaves` |
| `plant_f_007` | `is_shrub` |

## Task and context IDs

| Task | Class | Context IDs |
| --- | --- | --- |
| `fly` | `bird` | `dry_20m`, `dry_500m`, `wet_20m`, `dry_5m`, `wet_500m` |
| `run` | `human` | `run_100m_8kmh`, `run_5km_10kmh`, `run_1km_uphill`, `run_100m_12kmh`, `run_10km_8kmh` |
| `guilt` | `legal_case` | `ordinary_situation`, `emergency_necessity`, `official_duties`, `supervisors_order`, `friends_request` |
| `survive` | `mammal` | `mammal_mild_7d`, `mammal_cold_24h`, `mammal_heat_24h`, `mammal_no_water_food_3d`, `mammal_no_food_14d` |
| `survive` | `plant` | `plant_no_water_3d`, `plant_hot_drought_30d`, `plant_freezing_7d`, `plant_watered_7d`, `plant_waterlogged_7d` |

## Command options

| Option | Default | Meaning |
| --- | --- | --- |
| `--source-id NAME` | `random_label` | Output directory `labels/generated/NAME`; no date suffix is added. |
| `--classes CLASS ...` | Five configured classes | Select one or more class IDs from the table above. |
| `--instance-range START END` | `1 100` | Select inclusive numeric sample ID suffixes within each selected class. |
| `--feature-range START END` | `1 7` | Select inclusive numeric feature ID suffixes within each selected class. |
| `--tasks [TASK ...]` | Configured tasks | Select task IDs; passing the option without IDs disables task output. |
| `--contexts [CONTEXT ...]` | Configured context IDs | Select context IDs for the selected classes and tasks; no IDs disables task output. |
| `--seed INTEGER` | `0` | Seed for reproducible random values. |
| `--root PATH` | Repository root | Catalog and output root; primarily useful for isolated runs. |

Ranges filter existing IDs and include both endpoints. Instance ranges must stay
within manual suffixes 1–100; feature ranges must stay within 1–7. For example,
--feature-range 2 4 selects feature IDs ending in 002, 003 and 004. Requests for
CUB instance suffixes 101–300 are rejected by this generator.

Feature range affects feature output only; instance range affects both output kinds.
Default classes and task/context IDs are explicitly configured in the script.
New catalog entries outside that scope do not silently expand generation. Context
metadata records the concrete IDs actually generated, grouped by task. Instance and
feature ranges are always concrete numeric pairs, including when CLI flags are omitted.
Selections with no output, unknown IDs and invalid ranges fail before publication.

## Examples

Generate or regenerate the complete checked-in template:

```bash
bash shells/labels/random_label.sh
```

Generate two human samples with three features and one context:

```bash
bash shells/labels/random_label.sh \
  --source-id random_human_example \
  --classes human \
  --instance-range 1 2 \
  --feature-range 1 3 \
  --tasks run \
  --contexts run_100m_8kmh \
  --seed 42
```

Generate feature values for manual samples across all classes, without task values:

```bash
bash shells/labels/random_label.sh \
  --source-id random_manual_features \
  --instance-range 1 100 \
  --feature-range 1 7 \
  --tasks \
  --seed 0
```

## Output format

```text
labels/generated/random_label/
  sources.json
  features/
    bird.json
    human.json
    legal_case.json
    mammal.json
    plant.json
  tasks_per_context/
    fly.json
    run.json
    guilt.json
    survive.json
```

Only files with selected values are created. Feature files map sample IDs to
feature IDs to values:

```json
{
  "human_0001": {
    "human_f_001": 1,
    "human_f_002": 0.5
  }
}
```

Task files map sample IDs to context IDs to values:

```json
{
  "human_0001": {
    "run_100m_8kmh": "true"
  }
}
```

These are illustrative values, not a promised seed result. Source, class and task
are determined by the directory and filename. Do not repeat record metadata for
each value. `sources.json` stores the run ID, seed, creation time, synthetic origin,
temporary value sets and the selected classes, instance/feature ranges, tasks and
contexts. The default instance_range is [1, 100] and feature_range is [1, 7]. The recorded contexts value is a
task-to-context-list mapping of actual output, with an empty object for no task output.

## Regeneration, reproducibility and validation

The default `labels/generated/random_label/` is regenerated in place. A named source other
than random_label must not already exist. Catalog validation runs before
creation and after writing; failed publication restores the previous template.
A filtered regeneration replaces the template with that selection, rather than
merging it with the previous selection.

The same seed, selection and catalog reproduce the values; timestamps may differ.
Task and feature values are sampled independently. Feature values are temporary
0, 0.5 or 1 placeholders; task values are the strings true, false and ambiguous.
They are not factual labels or inferred answers. The formal catalog feature value
encoding remains undecided. Corrections and factual checks should use separate
source runs, with evidence recorded once in source metadata.

The generator requires a valid catalog and its source metadata. A missing CUB
source binding prevents generation even when selecting another class, because the
whole catalog is validated first. Restore genuine source metadata before running;
do not manufacture collection history to bypass this check.

Git tracks `catalog/`, `labels/README.md` and `labels/generated/random_label/`. Other
label source directories are ignored. See [the repository guide](../AGENT.md)
and [label storage](../labels/README.md).

## Website script metadata

Successful catalog generation updates `docs/assets/catalog_generation_scripts.json`
with manual and cub entries. Label generation updates
`docs/assets/label_generation_scripts.json` with a random_label entry. Each script replaces only its
own entry, preserving the others. Failed validation leaves this registry unchanged.
This is an execution summary for the website, not a hand-maintained catalog snapshot.
For example, a successful manual run writes:

```json
{
  "manual": {
    "script": "shells/catalog/manual.sh",
    "classes": ["bird", "human", "legal_case", "mammal", "plant"],
    "instance_range": [1, 100]
  }
}
```

The random_label entry also records source, selected feature range, tasks, contexts
and seed. The contexts field maps task IDs to the actual generated context ID lists;
it is an empty object when no task values are generated. Numeric ranges are explicit and limited to the manual generation scope. Entries describe the latest successful
execution of each script; per-source provenance remains in labels/generated/<source>/sources.json.

## Context definitions

`catalog/tasks/<task>/contexts.yaml` uses context IDs as keys:

```yaml
task_id: fly
contexts:
  dry_20m:
    description: Short flight with dry plumage. Travel 20 metres continuously through the air.
```

Each entry contains description only. Class applicability is defined by task bindings.
For a single-class task all contexts apply to that class. In multi-class tasks,
`task.yaml` lists context IDs under each binding's contexts field. There are no
per-context class_id or revision fields; definition history is tracked in Git.

## Release views

Generated results live under labels/generated/<script_name>/ and are not published
as website label values. A release uses releases/<version>/meta_info.json to select
classes, inclusive instance and feature ranges, and task/context IDs. Selected values
belong in releases/<version>/labels/. The website offers actual release versions
from that metadata. Current v1 has no label values, so all displayed values are NA.
The historical v1 payloads are unchanged and are not matched to the new manual IDs.
