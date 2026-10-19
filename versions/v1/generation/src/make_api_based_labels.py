"""Stage 3: resumable OpenAI teacher annotation and anonymous student exports."""

from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import sys
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path
from tqdm.auto import tqdm

from dataset_common import (
    SCHEMA_VERSION, SPLITS, VARIANTS, canonical_json, configured_path, digest,
    file_digest, load_environment, read_json, read_jsonl, render_student_prompt, write_json, write_jsonl,
    CATEGORY_NAMES, result_directory, MODEL_CHOICES, configure_model_args, resolve_model,
)

LABEL_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "label": {"type": "integer", "enum": [0, 1]},
    },
    "required": ["label"],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_annotation(value: dict) -> dict:
    if not isinstance(value, dict) or set(value) != set(LABEL_SCHEMA["required"]):
        raise ValueError("Annotation must contain exactly label")
    label = value["label"]
    if type(label) is not int or label not in (0, 1):
        raise ValueError("Annotation label must be integer 0 or 1")
    return value


def load_inputs(directory: Path) -> tuple[dict, list[dict], list[dict], dict, dict]:
    manifest = read_json(directory / "manifest.json")
    if manifest["schema_version"] != SCHEMA_VERSION:
        raise ValueError("Unsupported input schema version")
    if digest({key: value for key, value in manifest.items() if key != "dataset_fingerprint"}) != manifest["dataset_fingerprint"]:
        raise ValueError("Input manifest fingerprint mismatch")
    for name in ("instances.jsonl", "pairs.jsonl", "specifications.json", "schedules.json"):
        if file_digest(directory / name) != manifest["files"][name]:
            raise ValueError(f"Input file changed since generation: {name}. Regenerate stage 1.")
    instances, pairs = read_jsonl(directory / "instances.jsonl"), read_jsonl(directory / "pairs.jsonl")
    if len(instances) != manifest["num_instances"] or len(pairs) != manifest["num_pairs"]:
        raise ValueError("Input record count mismatch")
    if len({pair["pair_id"] for pair in pairs}) != len(pairs):
        raise ValueError("Duplicate pair_id in inputs")
    return manifest, instances, pairs, read_json(directory / "specifications.json"), read_json(directory / "schedules.json")


def teacher_settings(args: argparse.Namespace) -> dict:
    return {"model": args.model, "temperature": args.temperature,
            "max_output_tokens": args.max_output_tokens, "reasoning_effort": args.reasoning_effort,
            "prompt_version": "paperpack_appendix_a2_binary_label_v4", "response_schema": LABEL_SCHEMA,
            "store": False}


def load_cache(path: Path, pairs: list[dict], fingerprint: str) -> dict[str, dict]:
    cache = {}
    lookup = {pair["pair_id"]: pair for pair in pairs}
    if not path.exists():
        return cache
    for row in read_jsonl(path):
        pair = lookup.get(row.get("pair_id"))
        if pair is None or row.get("input_hash") != pair["input_hash"]:
            raise ValueError("Cached annotation does not match current inputs; use another --output-dir")
        if row.get("run_fingerprint") != fingerprint:
            raise ValueError("Cached annotation uses different teacher settings; use another --output-dir")
        if row.get("status") not in ("resolved", "unresolved", "error"):
            raise ValueError("Unknown annotation status in cache")
        if row["status"] == "resolved":
            validate_annotation({key: row[key] for key in LABEL_SCHEMA["required"]})
            expected = "resolved"
            if row["status"] != expected:
                raise ValueError("Cached annotation status disagrees with label")
        elif row.get("label") is not None:
            raise ValueError("Error annotations cannot carry a label")
        cache[row["pair_id"]] = row
    return cache


def load_reviews(path: Path | None, pairs: list[dict]) -> dict[str, dict]:
    if path is None:
        return {}
    lookup = {pair["pair_id"]: pair for pair in pairs}
    result = {}
    for review in read_jsonl(path):
        pair = lookup.get(review.get("pair_id"))
        if pair is None or pair["input_hash"] != review.get("input_hash"):
            raise ValueError("Review pair_id/input_hash does not match these inputs")
        if review["pair_id"] in result:
            raise ValueError("Duplicate review pair_id")
        if "label" not in review:
            raise ValueError("Review must explicitly include label")
        for key in ("reason", "reviewed_by"):
            if not isinstance(review.get(key), str) or not review[key].strip():
                raise ValueError(f"Review {key} must be a nonempty string")
        validate_annotation({"label": review.get("label")})
        result[review["pair_id"]] = review
    return result


def annotate_pair(client, pair: dict, settings: dict, fingerprint: str) -> dict:
    row = {"pair_id": pair["pair_id"], "input_hash": pair["input_hash"],
           "run_fingerprint": fingerprint, "requested_model": settings["model"],
           "created_at": utc_now(), "reason": "", "missing_information": []}
    request = {
        "model": settings["model"], "input": [{"role": "user", "content": pair["teacher_prompt"]}],
        "text": {"format": {"type": "json_schema", "name": "reference_label", "strict": True, "schema": LABEL_SCHEMA}},
        "max_output_tokens": settings["max_output_tokens"], "store": False,
    }
    if settings["temperature"] is not None:
        request["temperature"] = settings["temperature"]
    if settings["reasoning_effort"]:
        request["reasoning"] = {"effort": settings["reasoning_effort"]}
    try:
        response = client.responses.create(**request)
        row.update({"response_id": response.id, "response_model": response.model,
                    "usage": response.usage.model_dump() if response.usage else None,
                    "raw_output_text": response.output_text})
        if response.status != "completed":
            row.update({"status": "error", "error_type": "IncompleteResponse",
                        "reason": "Response did not complete; increase output-token budget or retry."})
            return row
        refusal = [content.refusal for item in response.output if item.type == "message"
                   for content in item.content if content.type == "refusal"]
        if refusal:
            row.update({"status": "unresolved", "reason": "Teacher refused this annotation.",
                        "refusal": refusal, "missing_information": ["Annotation requires review."]})
            return row
        annotation = validate_annotation(json.loads(response.output_text))
        row.update(annotation)
        row["status"] = "resolved"
    except Exception as exc:
        # API error bodies can echo credentials. Store type/status, never str(exc).
        status = getattr(exc, "status_code", None)
        row.update({"status": "error", "error_type": type(exc).__name__, "http_status": status,
                    "reason": "API request or annotation validation failed; review error_type/http_status and retry.",
                    "fatal": status in (400, 401, 403, 404, 429)})
    return row


def collect_annotations(client, pending: list[dict], settings: dict, fingerprint: str,
                        cache: dict, path: Path, workers: int, annotate=None) -> int:
    annotate = annotate or annotate_pair
    errors = 0
    counts = {"resolved": 0, "unresolved": 0, "error": 0}
    iterator = iter(pending)
    stopping = False
    # Bound in-flight work so a bad key/model/quota cannot fan out over the dataset.
    stage = "Features" if annotate.__name__ == "annotate_features" else "Labels"
    with path.open("a", encoding="utf-8") as stream, ThreadPoolExecutor(max_workers=workers) as executor, \
            tqdm(total=len(pending), desc=f"{stage} [{settings['model']}]", unit="request", dynamic_ncols=True) as progress:
        futures = {}

        def submit_next() -> None:
            pair = next(iterator, None)
            if pair is not None:
                futures[executor.submit(annotate, client, pair, settings, fingerprint)] = pair

        for _ in range(min(workers, len(pending))):
            submit_next()
        while futures:
            done, _ = wait(futures, return_when=FIRST_COMPLETED)
            for future in done:
                futures.pop(future)
                row = future.result()
                stream.write(canonical_json(row) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
                cache[row["pair_id"]] = row
                errors += row["status"] == "error"
                stopping = stopping or row.get("fatal", False)
                counts[row["status"]] += 1
                progress.set_postfix(ok=counts["resolved"], unresolved=counts["unresolved"], errors=counts["error"], refresh=False)
                progress.update(1)
            if not stopping:
                for _ in done:
                    submit_next()
    if stopping:
        print("Stopped new requests after an API configuration/rate-limit error. Completed results were saved.", file=sys.stderr)
    return errors


def export_dataset(output: Path, manifest: dict, instances: list[dict], pairs: list[dict],
                   specifications: dict, schedules: dict, cache: dict, reviews: dict) -> dict:
    effective = {key: row.copy() for key, row in cache.items()}
    for key, review in reviews.items():
        effective[key] = {**effective.get(key, {}), **review, "annotation_source": "human_review",
                          "status": "resolved"}
    by_instance = {}
    for pair in pairs:
        by_instance.setdefault(pair["instance_id"], []).append(pair)
    retained = {
        key for key, rows in by_instance.items()
        if {row["context_id"] for row in rows} == {context["context_id"] for context in specifications[rows[0]["domain"]]["contexts"]} and all(effective.get(row["pair_id"], {}).get("status") == "resolved" for row in rows)
    }
    accepted = [pair for pair in pairs if pair["instance_id"] in retained]
    lookup = {row["instance_id"]: row for row in instances}
    context_lookup = {(domain, context["context_id"]): context
                      for domain, spec in specifications.items() for context in spec["contexts"]}
    # Configuration status must be recomputed after filtering can remove training instances.
    seen = {}
    for row in instances:
        if row["instance_id"] in retained and row["split"] == "train":
            seen.setdefault(row["domain"], set()).add(tuple(row["feature_vector"]))
    student_rows = []
    for pair in accepted:
        instance = lookup[pair["instance_id"]]
        annotation = effective[pair["pair_id"]]
        status = ("training" if pair["split"] == "train" else "seen_configuration"
                  if tuple(instance["feature_vector"]) in seen.get(pair["domain"], set()) else "new_configuration")
        # Render from the saved vector and specification so older input snapshots
        # also export every false/ambiguous/true feature using the current format.
        prompts = {variant: render_student_prompt(instance, specifications[pair["domain"]],
                                                  context_lookup[(pair["domain"], pair["context_id"])], variant)
                   for variant in VARIANTS}
        student_rows.append({
            "pair_id": pair["pair_id"], "instance_id": instance["anonymous_id"],
            "domain": pair["domain"], "target": pair["target"], "context_id": pair["context_id"],
            "split": pair["split"], "configuration_status": status,
            "feature_values": instance["feature_values"], "feature_vector": instance["feature_vector"],
            "feature_source": instance.get("feature_source", {"kind": "stage_1_projection"}),
            "label": annotation["label"], "student_prompts": prompts,
        })
    write_jsonl(output / "dataset.jsonl", student_rows)
    for variant in VARIANTS:
        for split in SPLITS:
            write_jsonl(output / "student" / variant / f"{split}.jsonl", (
                {"pair_id": row["pair_id"], "domain": row["domain"], "instance_id": row["instance_id"],
                 "context_id": row["context_id"], "configuration_status": row["configuration_status"],
                 "prompt": row["student_prompts"][variant], "completion": str(row["label"])}
                for row in student_rows if row["split"] == split
            ))
    matrices = {}
    for domain in manifest["domains"]:
        members = [row for row in instances if row["domain"] == domain and row["instance_id"] in retained]
        contexts = [row["context_id"] for row in specifications[domain]["contexts"]]
        matrices[domain] = {"target": specifications[domain]["target"], "contexts": contexts,
                            "instances": [row["anonymous_id"] for row in members],
                            "labels": [[effective[f"{row['instance_id']}/{context}"]["label"] for row in members]
                                       for context in contexts]}
    write_json(output / "label_matrices.json", matrices)
    filtered_schedules = {}
    retained_pairs = {pair["pair_id"] for pair in accepted}
    for domain, value in schedules.items():
        filtered_schedules[domain] = {
            key: ([item for item in items if item in retained] if key.endswith("instances") else
                  [event for event in items if (event.get("instance_id") in retained if event["event"] == "introduce"
                                               else event.get("pair_id") in retained_pairs)])
            for key, items in value.items()
        }
    write_json(output / "schedules.json", filtered_schedules)
    unresolved = []
    for pair in pairs:
        annotation = effective.get(pair["pair_id"])
        if annotation and annotation["status"] != "resolved":
            unresolved.append({"pair_id": pair["pair_id"], "input_hash": pair["input_hash"],
                               "domain": pair["domain"], "status": annotation["status"], 
                               "reason": annotation["reason"], "missing_information": annotation.get("missing_information", []),
                               "reviewed_by": ""})
    write_jsonl(output / "unresolved.jsonl", unresolved)
    summary = {
        "dataset_fingerprint": manifest["dataset_fingerprint"],
        "planned_instances": len(instances), "planned_pairs": len(pairs),
        "annotated_pairs": len(effective), "pending_pairs": len(pairs) - len(effective),
        "unresolved_pairs": sum(row["status"] == "unresolved" for row in effective.values()),
        "error_pairs": sum(row["status"] == "error" for row in effective.values()),
        "retained_instances": len(retained), "retained_pairs": len(accepted),
        "excluded_instances": len(instances) - len(retained),
        "filter_policy": "Retain an instance only when all specified context labels are resolved (0 or 1).",
        "human_reviews": len(reviews), "label_source": "Teacher-generated references, with any explicit human reviews; not automatically verified ground truth.",
        "domains": {},
        "mammal_context_disagreements": [row["anonymous_id"] for row in instances
                                        if row["domain"] == "mammals" and row["instance_id"] in retained
                                        and len({effective[pair["pair_id"]]["label"] for pair in by_instance[row["instance_id"]]}) > 1],
    }
    for domain in manifest["domains"]:
        rows = [row for row in student_rows if row["domain"] == domain]
        summary["domains"][domain] = {"instances": len({row["instance_id"] for row in rows}), "pairs": len(rows),
                                      "label_counts": {str(label): sum(row["label"] == label for row in rows) for label in (0, 1)},
                                      "split_pairs": {split: sum(row["split"] == split for row in rows) for split in SPLITS}}
    write_json(output / "summary.json", summary)
    # Copy only the public feature/context definitions, never original identities.
    write_json(output / "specifications.json", specifications)
    for domain in manifest["domains"]:
        write_json(output / f"{CATEGORY_NAMES[domain]}_result.json", {
            "category": CATEGORY_NAMES[domain], "domain": domain,
            "api_model_name": (read_json(output / "run_manifest.json")["teacher_settings"]["model"]
                               if (output / "run_manifest.json").exists() else None),
            "dataset_fingerprint": manifest["dataset_fingerprint"],
            "results": [{**{key: value for key, value in pair.items() if key != "teacher_prompt"},
                         **{key: value for key, value in effective.get(pair["pair_id"], {
                             "status": "pending", "reason": "", "missing_information": []}).items()
                            if key != "raw_output_text"},
                         "feature_values": lookup[pair["instance_id"]]["feature_values"],
                         "feature_vector": lookup[pair["instance_id"]]["feature_vector"],
                         "feature_source": lookup[pair["instance_id"]].get("feature_source", {"kind": "stage_1_projection"}),
                         "student_prompts": {
                             variant: render_student_prompt(lookup[pair["instance_id"]], specifications[domain],
                                                            context_lookup[(domain, pair["context_id"])], variant)
                             for variant in VARIANTS}}
                        for pair in pairs if pair["domain"] == domain],
        })
    return summary


def run(args: argparse.Namespace) -> int:
    manifest, instances, pairs, specs, schedules = load_inputs(args.input_dir)
    settings = teacher_settings(args)
    if not args.skip_api_features:
        from make_api_based_features import apply_feature_results
        feature_dir = args.feature_dir or result_directory("features", args.feature_model)
        if args.dry_run and not feature_dir.exists():
            print(f"Stage 2 features not generated yet: {feature_dir}")
        else:
            settings["feature_results_fingerprint"] = apply_feature_results(feature_dir, manifest, instances, specs)
    run_path = args.output_dir / "run_manifest.json"
    if run_path.exists():
        previous = read_json(run_path)
        if previous["dataset_fingerprint"] != manifest["dataset_fingerprint"]:
            raise ValueError("Label directory belongs to different inputs; use another --output-dir")
        if args.export_only:
            if previous["teacher_settings"].get("feature_results_fingerprint") != settings.get("feature_results_fingerprint"):
                raise ValueError("Feature results changed since labeling; use the original feature directory for export")
            settings = previous["teacher_settings"]
        elif previous["teacher_settings"] != settings:
            raise ValueError("Teacher settings changed; use another --output-dir to keep reference labels consistent")
    fingerprint = digest([manifest["dataset_fingerprint"], settings])
    cache = load_cache(args.output_dir / "annotations.jsonl", pairs, fingerprint)
    reviews = load_reviews(args.reviews, pairs)
    pending = [pair for pair in pairs if pair["pair_id"] not in reviews and (
        pair["pair_id"] not in cache or cache[pair["pair_id"]]["status"] == "error"
        or (args.retry_unresolved and cache[pair["pair_id"]]["status"] == "unresolved")
    )]
    selected = pending if args.limit is None else pending[:args.limit]
    print(f"Label model={settings['model']}; output={args.output_dir}")
    print(f"Inputs: {len(instances)} instances / {len(pairs)} pairs. Cached: {len(cache)}. Pending requests: {len(pending)}. Selected: {len(selected)}.")
    if args.dry_run:
        print(f"Dry run: model={settings['model']}; no API calls or output changes.")
        return 0
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if selected and not args.export_only and (not key or key.startswith(("YOUR_", "your-", "sk-your"))):
        raise ValueError("Set OPENAI_API_KEY in aistats-2027/.env before API labeling, or use --dry-run / --export-only")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / ".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("Another label process is using this output directory") from exc
        if run_path.exists():
            locked_manifest = read_json(run_path)
            if locked_manifest["run_fingerprint"] != fingerprint:
                raise ValueError("Label directory settings changed before the lock was acquired; use another --output-dir")
        # Reload inside the lock so a concurrently finishing process cannot cause duplicate requests.
        cache = load_cache(args.output_dir / "annotations.jsonl", pairs, fingerprint)
        selected = [pair for pair in selected if pair["pair_id"] not in cache
                    or cache[pair["pair_id"]]["status"] == "error"
                    or (args.retry_unresolved and cache[pair["pair_id"]]["status"] == "unresolved")]
        if not run_path.exists():
            write_json(run_path, {"schema_version": SCHEMA_VERSION, "created_at": utc_now(),
                                 "dataset_fingerprint": manifest["dataset_fingerprint"],
                                 "run_fingerprint": fingerprint, "teacher_settings": settings,
                                 "runtime": {"workers": args.workers, "timeout_seconds": args.timeout, "max_retries": args.max_retries},
                                 "api_documentation": "https://developers.openai.com/api/docs/guides/structured-outputs"})
        errors = 0
        if selected and not args.export_only:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise RuntimeError("Install dependencies: python -m pip install -r requirements.txt") from exc
            # Calls use the official endpoint; do not inherit an unrelated proxy/base URL.
            with OpenAI(api_key=key, base_url="https://api.openai.com/v1", timeout=args.timeout, max_retries=args.max_retries) as client:
                errors = collect_annotations(client, selected, settings, fingerprint, cache,
                                             args.output_dir / "annotations.jsonl", args.workers)
        summary = export_dataset(args.output_dir, manifest, instances, pairs, specs, schedules, cache, reviews)
        print(f"Retained {summary['retained_instances']} complete instances / {summary['retained_pairs']} pairs: {args.output_dir}")
        print(f"Pending={summary['pending_pairs']}, unresolved={summary['unresolved_pairs']}, errors={summary['error_pairs']}")
        return 1 if errors else 0


def parse_args(argv=None) -> argparse.Namespace:
    load_environment()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=configured_path("DATASET_INPUT_DIR", "data/current/inputs"))
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--model", default=os.getenv("OPENAI_LABEL_MODEL", "gpt-4.1"),
                        help="API model ID; examples: " + ", ".join(MODEL_CHOICES))
    parser.add_argument("--list-models", action="version", version="\n".join(MODEL_CHOICES))
    parser.add_argument("--feature-dir", type=Path, help="Stage 2 results directory; default: data/current/features/<feature-model>")
    parser.add_argument("--feature-model", help="Stage 2 model; defaults to --model unless OPENAI_FEATURE_MODEL is set")
    parser.add_argument("--skip-api-features", action="store_true", help="Use stage 1 features instead of stage 2 estimates")
    raw_temperature = os.getenv("OPENAI_LABEL_TEMPERATURE", "0").strip()
    parser.add_argument("--temperature", type=float, default=float(raw_temperature) if raw_temperature else None)
    parser.add_argument("--omit-temperature", action="store_true")
    parser.add_argument("--reasoning-effort", default=os.getenv("OPENAI_LABEL_REASONING_EFFORT", "").strip() or None)
    parser.add_argument("--max-output-tokens", type=int, default=int(os.getenv("OPENAI_LABEL_MAX_OUTPUT_TOKENS", "512")))
    parser.add_argument("--timeout", type=float, default=float(os.getenv("OPENAI_LABEL_TIMEOUT_SECONDS", "60")))
    parser.add_argument("--max-retries", type=int, default=int(os.getenv("OPENAI_LABEL_MAX_RETRIES", "3")))
    parser.add_argument("--workers", type=int, default=int(os.getenv("OPENAI_LABEL_WORKERS", "4")))
    parser.add_argument("--limit", type=int, help="Maximum number of pending API requests for this invocation")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs/settings/cache without making requests or writing files")
    parser.add_argument("--export-only", action="store_true", help="Export saved annotations and reviews without API calls")
    parser.add_argument("--retry-unresolved", action="store_true", help="Retry previously refused annotations; errors always retry")
    parser.add_argument("--reviews", type=Path, help="Reviewed JSONL with pair_id, input_hash, label, reason, reviewed_by")
    args = parser.parse_args(argv)
    if not args.model.strip():
        parser.error("--model must not be empty")
    configure_model_args(args)
    args.feature_model = resolve_model(args.feature_model or os.getenv("OPENAI_FEATURE_MODEL", "").strip() or args.model)
    args.output_dir = args.output_dir or result_directory("labels", args.model)
    if args.omit_temperature:
        args.temperature = None
    if args.workers < 1 or args.max_output_tokens < 1 or not math.isfinite(args.timeout) or args.timeout <= 0 or args.max_retries < 0:
        parser.error("workers, max-output-tokens, and timeout must be positive; max-retries must be nonnegative")
    if args.temperature is not None and (not math.isfinite(args.temperature) or not 0 <= args.temperature <= 2):
        parser.error("temperature must be finite and between 0 and 2")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if not args.model.strip():
        parser.error("--model must not be empty")
    if args.input_dir.resolve() == args.output_dir.resolve():
        parser.error("--input-dir and --output-dir must be different directories")
    return args


def main(argv=None) -> int:
    try:
        return run(parse_args(argv))
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print(f"Stage 3 failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
