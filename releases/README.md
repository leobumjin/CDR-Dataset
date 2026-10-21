# Release selections

```text
releases/
  v1/
    meta_info.json
    labels/
      features/<class>.json
      tasks_per_context/<task>.json
      groups/<class>.json
```

meta_info.json explicitly declares the release ID, classes, inclusive instance_range
and feature_range, and task IDs mapped to context ID lists. Selected values use the
same compact mappings as generated results. Keep source selection and evidence
references here when assembling real release labels.

The current v1 entry defines the manual 1–100 preview scope, with features 1–7,
but its status is labels_unavailable. No values have been released for this new
catalog. The website therefore shows NA. Historical v1 payloads remain unchanged
under versions/v1 and data/v1; their IDs are not reassigned to current catalog IDs.
No v2 entry exists yet. Website version options follow actual release metadata.

Generated script results remain under labels/generated/<script_name>/ and are
never used as a fallback for unavailable release labels. Run
`python -m src.catalog.web_assets` after editing release selections or labels.
