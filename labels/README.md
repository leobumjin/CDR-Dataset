# Generated labels

```text
labels/
  generated/
    random_label/
      sources.json
      features/<class>.json
      tasks_per_context/<task>.json
    classes_bird_cub/
      sources.json
      raw/classes.txt
```

Generated outputs are grouped by script name. Shared execution settings and
provenance belong in sources.json once. Feature JSON maps instance ID to feature ID
to value; task JSON maps instance ID to context ID to value. Missing keys mean
uncollected values. Labels remain separate from catalog YAML definitions.

```bash
bash shells/labels/random_label.sh --seed 0
bash shells/labels/random_label.sh --classes human --instance-range 1 100 --feature-range 1 7 --tasks run
```

The default generated directory is random_label, without a date. Re-running
regenerates it. Use --source-id for an independent run; other existing names are
not overwritten. The random generator is restricted to manual instances 1–100
and features 1–7. Task/context defaults are explicit. It creates 3,500 feature values
and 2,500 task values. These are synthetic placeholders, not release labels.

Track labels/generated/random_label as the repository example. Other generated
results are ignored. Catalog source collectors also store provenance under generated/.

Release selections live separately in releases/<version>/meta_info.json, with
selected values under releases/<version>/labels/. The website only reads release
values, filtered to the release metadata scope; missing values display NA. It does
not substitute generated values. See [release selection](../releases/README.md)
and [generator options](../docs/label_generation_script.md).
