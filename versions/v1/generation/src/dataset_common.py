"""Shared file, configuration, and serialization helpers for the three stages."""

from __future__ import annotations

import hashlib
import json
import os
import random
import tempfile
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 3
SPLITS = ("train", "validation", "test")
VARIANTS = (
    "feature_present",
    "feature_absent",
    "feature_present_context_description",
    "feature_absent_context_description",
)

CATEGORY_NAMES = {"birds": "bird", "mammals": "mammal", "plants": "plant",
                  "humans": "human", "legal_cases": "legal"}

MODEL_CHOICES = ("gpt-4o", "gpt-5.4", "gpt-6.1-sol")


def resolve_model(model: str) -> str:
    model = model.strip()
    if not model:
        raise ValueError("Model must not be empty")
    if model == "gpt-6.1":
        print("Model: gpt-6.1 -> gpt-6.1-sol (API model ID)")
        return "gpt-6.1-sol"
    return model


def configure_model_args(args) -> None:
    args.model = resolve_model(args.model)
    reasoning_model = args.model.startswith(("gpt-5", "gpt-6", "o1", "o3", "o4"))
    if args.omit_temperature or reasoning_model:
        args.temperature = None
    if not reasoning_model:
        args.reasoning_effort = None


def model_directory(model: str) -> str:
    # A model identifier must never escape the result root.
    from urllib.parse import quote
    name = quote(model.strip(), safe="-_.")
    if not name or name in (".", ".."):
        raise ValueError("Invalid model name")
    return name


def result_directory(stage: str, model: str) -> Path:
    variable = "DATASET_FEATURE_DIR" if stage == "features" else "DATASET_LABEL_DIR"
    override = os.getenv(variable, "").strip()
    return configured_path(variable, override) if override else ROOT / "data" / "current" / stage / model_directory(model)


def load_environment() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        if (ROOT / ".env").exists():
            raise RuntimeError("Install dependencies: python -m pip install -r requirements.txt")
        return
    load_dotenv(ROOT / ".env", override=False)


def configured_path(variable: str, default: str) -> Path:
    path = Path(os.getenv(variable, default)).expanduser()
    return path if path.is_absolute() else ROOT / path


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seeded_random(seed: int, namespace: str) -> random.Random:
    return random.Random(digest([seed, namespace]))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path.name}, line {line_number}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"Expected an object in {path.name}, line {line_number}")
            records.append(row)
    return records


def atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path: Path, value: Any) -> None:
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    atomic_text(path, "".join(canonical_json(row) + "\n" for row in rows))


def is_feature_value(value: Any) -> bool:
    return type(value) in (int, float) and value in (0, 0.5, 1)


def feature_items(instance: dict, specification: dict) -> list[tuple[str, int | float]]:
    vector = instance.get("feature_vector", [])
    names = specification.get("feature_names")
    if names is None:
        names = [f"feature_{index:03d}" for index in range(1, len(vector) + 1)]
    if len(names) != len(vector):
        raise ValueError("Feature names and vector have different dimensions")
    if any(not is_feature_value(value) for value in vector):
        raise ValueError("Feature vector must contain only numeric 0, 0.5, or 1")
    return list(zip(names, vector))


def feature_marker(value: int | float) -> str:
    if not is_feature_value(value):
        raise ValueError("Feature value must be numeric 0, 0.5, or 1")
    return "1/2" if value == 0.5 else "1" if value == 1 else "0"


def render_student_prompt(instance: dict, domain: dict, context: dict, variant: str) -> str:
    lines = [
        "Predict the target label.",
        "Return only 0 or 1.",
        f"Target: {domain['target']}",
        f"Target definition: {domain['target_definition']}",
        f"Instance: {instance['anonymous_id']}",
    ]
    if variant.startswith("feature_present"):
        lines.extend(["Features:", "Feature judgments: 0 = false, 1/2 = ambiguous, 1 = true.",
                      "1/2 is an ambiguous judgment, not a calibrated probability or target label."])
        lines.extend(f"  [{feature_marker(value)}] {name}" for name, value in feature_items(instance, domain))
    selected_context = (
        context["description"] if variant.endswith("context_description") else context["context_id"]
    )
    if variant.endswith("context_description") and context.get("rule"):
        selected_context += f" Applicable rule: {context['rule']}"
    lines.extend([f"Context: {selected_context}", "Label:"])
    return "\n".join(lines)


def render_teacher_prompt(instance: dict, domain: dict, context: dict) -> str:
    # Appendix A.2. Sources and constructed states are explicitly distinguished.
    return "\n".join([
        "You are assigning reference labels for a binary prediction dataset.",
        "Judge the target under exactly the supplied conditions.",
        "Do not treat missing information as a negative fact.",
        f"Category: {domain['category']}",
        f"Target: {domain['target']}",
        f"Target definition: {domain['target_definition']}",
        f"Instance: {instance['original_identity']}",
        f"Attributes: {canonical_json(instance['attributes'])}",
        f"Attribute provenance: {canonical_json(instance['sources'])}",
        f"Individual state / stipulated facts: {canonical_json(instance['state'])}",
        "Individual states and fictional profile facts are constructed experimental conditions.",
        f"Context: {context['description']}",
        f"Applicable rule: {context.get('rule') or 'Not applicable'}",
        "Return 1 if the target holds and 0 if it does not.",
        "When evidence is uncertain, choose the better-supported binary judgment under the supplied conditions. Do not invent missing facts or use a soft label.",
        "For legal cases, use only the supplied rule and facts.",
        'Return only JSON with one field: {"label": 0} or {"label": 1}.',
        "Do not include reasons, explanations, or additional fields.",
    ])
