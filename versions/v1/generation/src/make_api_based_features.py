"""Stage 2: resumable model estimates of bird, mammal, and plant features."""
from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import sys
from pathlib import Path

from dataset_common import (CATEGORY_NAMES, canonical_json, configured_path, digest,
                            is_feature_value, load_environment, read_json, read_jsonl,
                            result_directory, write_json, MODEL_CHOICES, configure_model_args)
from make_api_based_labels import collect_annotations, load_inputs, utc_now

FEATURE_DOMAINS = ("birds", "mammals", "plants")


def feature_schema(names):
    judgment = {"type": "number", "enum": [0, 0.5, 1]}
    return {"type": "object", "additionalProperties": False,
            "properties": {"features": {"type": "object", "additionalProperties": False,
                                       "properties": {name: judgment for name in names}, "required": names}},
            "required": ["features"]}


def validate_features(value, names):
    if not isinstance(value, dict) or set(value) != {"features"}:
        raise ValueError("Expected exactly features")
    features = value["features"]
    if not isinstance(features, dict) or set(features) != set(names):
        raise ValueError("Feature names must exactly match the specification")
    if any(not is_feature_value(judgment) for judgment in features.values()):
        raise ValueError("Feature values must be numeric 0, 0.5, or 1")
    return {name: features[name] for name in names}



def feature_task(instance, spec):
    names = spec["feature_names"]
    prompt = "\n".join([
        "For the following organism, provide a value for every listed feature using its name and stipulated state.",
        "Use your biological knowledge for species properties. Do not infer a target label.",
        "Respect the stipulated state; do not replace it with a typical healthy adult.",
        "Return 0 for false, 1 for true, and 0.5 for ambiguous or insufficient knowledge.",
        "Return values only, without explanations. Do not use 0.5 as a probability.",
        f"Category: {spec['category']}", f"Identity: {instance['original_identity']}",
        f"Stipulated individual state: {canonical_json(instance['state'])}",
        "Feature definitions: " + canonical_json({name: spec["feature_definitions"][name]["description"] for name in names}),
        'Return only JSON: {"features": {"feature_name": 0, ...}}. Include every listed feature.', 
    ])
    # Catalog attributes and precomputed judgments are intentionally absent: the model estimates them.
    return {"pair_id": instance["instance_id"], "instance_id": instance["instance_id"],
            "domain": instance["domain"], "original_identity": instance["original_identity"],
            "species_id": instance["species_id"], "teacher_prompt": prompt,
            "feature_names": names, "input_hash": digest(prompt)}


def annotate_features(client, task, settings, fingerprint):
    row = {"pair_id": task["pair_id"], "instance_id": task["instance_id"],
           "input_hash": task["input_hash"], "run_fingerprint": fingerprint,
           "requested_model": settings["model"], "created_at": utc_now(),
           "feature_values": None, "feature_vector": None}
    request = {"model": settings["model"], "input": [{"role": "user", "content": task["teacher_prompt"]}],
               "text": {"format": {"type": "json_schema", "name": "feature_judgments", "strict": True,
                                    "schema": feature_schema(task["feature_names"])}},
               "max_output_tokens": settings["max_output_tokens"], "store": False}
    if settings["temperature"] is not None:
        request["temperature"] = settings["temperature"]
    if settings["reasoning_effort"]:
        request["reasoning"] = {"effort": settings["reasoning_effort"]}
    try:
        response = client.responses.create(**request)
        row.update(response_id=response.id, response_model=response.model,
                   usage=response.usage.model_dump() if response.usage else None,
                   raw_output_text=response.output_text)
        if response.status != "completed":
            row.update(status="error", error_type="IncompleteResponse")
            return row
        if any(content.type == "refusal" for item in response.output if item.type == "message" for content in item.content):
            row.update(status="unresolved", reason="Model refused feature estimation.")
            return row
        value = json.loads(response.output_text)
        features = validate_features(value, task["feature_names"])
        row.update(status="resolved", feature_values=features,
                   feature_vector=[features[name] for name in task["feature_names"]])
    except Exception as exc:
        status = getattr(exc, "status_code", None)
        row.update(status="error", error_type=type(exc).__name__, http_status=status,
                   fatal=status in (400, 401, 403, 404, 429))
    return row


def load_feature_cache(path, tasks, fingerprint):
    lookup = {task["pair_id"]: task for task in tasks}
    cache = {}
    for row in read_jsonl(path) if path.exists() else []:
        task = lookup.get(row.get("pair_id"))
        if task is None or row.get("input_hash") != task["input_hash"] or row.get("run_fingerprint") != fingerprint:
            raise ValueError("Feature cache does not match inputs/settings; use another --output-dir")
        if row.get("status") not in ("resolved", "unresolved", "error"):
            raise ValueError("Invalid feature cache status")
        if row["status"] == "resolved":
            values = validate_features({"features": row["feature_values"]}, task["feature_names"])
            if values != row["feature_values"] or row["feature_vector"] != [values[name] for name in task["feature_names"]]:
                raise ValueError("Feature cache values disagree")
        cache[row["pair_id"]] = row
    return cache


def export_features(output, manifest, tasks, specs, settings, fingerprint, cache):
    for domain in dict.fromkeys(task["domain"] for task in tasks):
        members = [task for task in tasks if task["domain"] == domain]
        write_json(output / f"{CATEGORY_NAMES[domain]}_result.json", {
            "category": CATEGORY_NAMES[domain], "domain": domain, "api_model_name": settings["model"],
            "dataset_fingerprint": manifest["dataset_fingerprint"], "run_fingerprint": fingerprint,
            "feature_names": specs[domain]["feature_names"],
            "results": [{**task, **cache.get(task["pair_id"], {"status": "pending", "feature_values": None,
                                                               "feature_vector": None})} for task in members],
        })


def apply_feature_results(directory, manifest, instances, specs):
    """Replace student judgments only; teacher raw facts remain independent."""
    payloads = {}
    for domain in FEATURE_DOMAINS:
        members = [row for row in instances if row["domain"] == domain]
        if not members:
            continue
        path = directory / f"{CATEGORY_NAMES[domain]}_result.json"
        if not path.is_file():
            raise ValueError(f"Missing stage 2 features: {path}. Run make_dataset_2_api_based_features.sh first.")
        payload = read_json(path)
        if payload["dataset_fingerprint"] != manifest["dataset_fingerprint"] or payload["domain"] != domain:
            raise ValueError("Feature results belong to different inputs")
        if payload["feature_names"] != specs[domain]["feature_names"]:
            raise ValueError("Feature result definitions differ from inputs")
        rows = payload["results"]
        lookup = {row["instance_id"]: row for row in rows}
        if len(lookup) != len(rows) or set(lookup) != {row["instance_id"] for row in members}:
            raise ValueError("Feature result instance IDs differ from inputs")
        for instance in members:
            row = lookup[instance["instance_id"]]
            task = feature_task(instance, specs[domain])
            if row["status"] != "resolved" or row["input_hash"] != task["input_hash"]:
                raise ValueError(f"Incomplete or stale stage 2 features for {instance['instance_id']}")
            values = validate_features({"features": row["feature_values"]}, payload["feature_names"])
            if values != row["feature_values"] or row["feature_vector"] != [values[name] for name in payload["feature_names"]]:
                raise ValueError("Feature result values disagree")
            instance["feature_values"] = values
            instance["feature_vector"] = row["feature_vector"]
            instance["feature_source"] = {"kind": "model_estimate", "model": payload["api_model_name"]}
        payloads[domain] = payload
    return digest(payloads)


def run(args):
    manifest, instances, _, specs, _ = load_inputs(args.input_dir)
    domains = [domain for domain in args.domains if domain in specs]
    if not domains:
        raise ValueError("No selected bird/mammal/plant domains in inputs")
    tasks = [feature_task(row, specs[row["domain"]]) for row in instances if row["domain"] in domains]
    settings = {"model": args.model, "temperature": args.temperature, "reasoning_effort": args.reasoning_effort,
                "max_output_tokens": args.max_output_tokens, "prompt_version": "feature_estimation_values_only_v2",
                "schemas": {domain: feature_schema(specs[domain]["feature_names"]) for domain in domains}, "store": False}
    fingerprint = digest([manifest["dataset_fingerprint"], settings])
    path = args.output_dir / "annotations.jsonl"
    run_path = args.output_dir / "run_manifest.json"
    if run_path.exists() and read_json(run_path)["run_fingerprint"] != fingerprint:
        raise ValueError("Feature directory belongs to different inputs/settings; use another --output-dir")
    cache = load_feature_cache(path, tasks, fingerprint)
    def pending():
        rows = [task for task in tasks if task["pair_id"] not in cache or cache[task["pair_id"]]["status"] == "error"
                or (args.retry_unresolved and cache[task["pair_id"]]["status"] == "unresolved")]
        return rows if args.limit is None else rows[:args.limit]
    print(f"Feature model={args.model}; instances={len(tasks)}; cached={len(cache)}; selected={len(pending())}; output={args.output_dir}")
    if args.dry_run:
        return 0
    selected = pending()
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if selected and (not key or key.startswith(("YOUR_", "your-", "sk-your"))):
        raise ValueError("Set OPENAI_API_KEY before feature estimation, or use --dry-run")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / ".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("Another feature process is using this directory") from exc
        if run_path.exists() and read_json(run_path)["run_fingerprint"] != fingerprint:
            raise ValueError("Feature directory settings changed before lock acquisition")
        cache = load_feature_cache(path, tasks, fingerprint)
        selected = pending()
        write_json(run_path, {"dataset_fingerprint": manifest["dataset_fingerprint"], "run_fingerprint": fingerprint,
                              "feature_settings": settings})
        errors = 0
        if selected:
            from openai import OpenAI
            with OpenAI(api_key=key, base_url="https://api.openai.com/v1", timeout=args.timeout, max_retries=args.max_retries) as client:
                errors = collect_annotations(client, selected, settings, fingerprint, cache, path, args.workers, annotate_features)
        export_features(args.output_dir, manifest, tasks, specs, settings, fingerprint, cache)
        return 1 if errors else 0


def parse_args(argv=None):
    load_environment()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=configured_path("DATASET_INPUT_DIR", "data/current/inputs"))
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--model", default=os.getenv("OPENAI_FEATURE_MODEL", "").strip() or os.getenv("OPENAI_LABEL_MODEL", "gpt-4.1"),
                        help="API model ID; examples: " + ", ".join(MODEL_CHOICES))
    parser.add_argument("--list-models", action="version", version="\n".join(MODEL_CHOICES))
    parser.add_argument("--domains", nargs="+", choices=(*FEATURE_DOMAINS, "bird", "mammal", "plant"), default=list(FEATURE_DOMAINS))
    raw_temperature = os.getenv("OPENAI_FEATURE_TEMPERATURE", "0").strip()
    parser.add_argument("--temperature", type=float, default=float(raw_temperature) if raw_temperature else None)
    parser.add_argument("--omit-temperature", action="store_true")
    parser.add_argument("--reasoning-effort", default=os.getenv("OPENAI_FEATURE_REASONING_EFFORT", "").strip() or None)
    parser.add_argument("--max-output-tokens", type=int, default=int(os.getenv("OPENAI_FEATURE_MAX_OUTPUT_TOKENS", "2048")))
    parser.add_argument("--timeout", type=float, default=float(os.getenv("OPENAI_FEATURE_TIMEOUT_SECONDS", "60")))
    parser.add_argument("--max-retries", type=int, default=int(os.getenv("OPENAI_FEATURE_MAX_RETRIES", "3")))
    parser.add_argument("--workers", type=int, default=int(os.getenv("OPENAI_FEATURE_WORKERS", "4")))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--retry-unresolved", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if not args.model.strip():
        parser.error("--model must not be empty")
    configure_model_args(args)
    args.output_dir = args.output_dir or result_directory("features", args.model)
    aliases = {CATEGORY_NAMES[domain]: domain for domain in FEATURE_DOMAINS}
    args.domains = [aliases.get(domain, domain) for domain in args.domains]
    if len(set(args.domains)) != len(args.domains):
        parser.error("Duplicate domains")
    if args.omit_temperature:
        args.temperature = None
    if args.workers < 1 or args.max_output_tokens < 1 or args.max_retries < 0 or not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("workers, max-output-tokens, timeout must be positive; retries nonnegative")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.temperature is not None and (not math.isfinite(args.temperature) or not 0 <= args.temperature <= 2):
        parser.error("temperature must be finite and between 0 and 2")
    if args.input_dir.resolve() == args.output_dir.resolve():
        parser.error("input and output directories must differ")
    return args


def main(argv=None):
    try:
        return run(parse_args(argv))
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print(f"Stage 2 failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
