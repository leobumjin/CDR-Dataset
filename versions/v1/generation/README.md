# v1 generation pipeline

This directory archives the generation, feature annotation, label export, assembly,
and split code from the AISTATS workspace. `src/` and `configs/` are byte-for-byte
copies of the workspace files at import. `run.py` is the release-specific runner.

## Exact experimental data

The released v1 is an assembled snapshot: birds/legal came from the workspace's
`data/v2-bird-legal`, while other domains came from earlier runs. Some label runs
used features estimated by another teacher. Historical paths in saved manifests
are provenance, not paths to resolve in this repository.

The archived assembly script depends on those historical source directories and
is retained for audit only. Do not run it as a standalone reproduction recipe.
The exact snapshot is restored offline, without re-querying a teacher:

```bash
python shells/release.py verify v1
python shells/release.py restore v1 --output runs/v1/exact-copy
```

## Fresh generation

Run these commands from the repository root with Python 3.10+:

```bash
python -m pip install -r versions/v1/generation/requirements.txt
python versions/v1/generation/run.py inputs --run trial-001
python versions/v1/generation/run.py features --run trial-001 --model gpt-5.4 --dry-run
# Export OPENAI_API_KEY in your shell before either API stage.
python versions/v1/generation/run.py features --run trial-001 --model gpt-5.4
python versions/v1/generation/run.py labels --run trial-001 --model gpt-5.4
python versions/v1/generation/run.py split --run trial-001
```

API stages incur API usage; they are not run as part of importing or verifying a
release. The runner accepts credentials from the environment, not the root `.env`.
Split is the finalization step: the runner refuses further generation in a finalized
run because historical input fingerprints no longer describe pre-split inputs.
The final split stage applies the instance-based 40/20/20/20 partition with seed
2027. A fresh generation uses the archived design across all five domains and
one feature/label model. It does **not** reproduce the mixed historical assembly
or guarantee the same teacher responses as v1.

To develop v2, copy this directory to `versions/v2/generation`, update its runner's version
paths, and edit that copy. Keep v1 unchanged. See `docs/versioning.md` for release
steps. Dependencies are archived compatible ranges, not a historical lockfile.
