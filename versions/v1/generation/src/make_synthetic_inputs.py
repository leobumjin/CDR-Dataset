"""Stage 1: reproducible hybrid inputs, without making API calls."""

from __future__ import annotations

import argparse
import itertools
import math
import os
import sys
from pathlib import Path

from dataset_common import (
    ROOT, SCHEMA_VERSION, VARIANTS, configured_path, digest,
    file_digest, load_environment, read_json, render_student_prompt,
    render_teacher_prompt, seeded_random, write_json, write_jsonl,
)
from dataset_design import BIRD_STATES, DOMAINS, HUMAN_STATES, LEGAL_STATES, PLANT_STATES, MAMMAL_STATES
from dataset_features import FEATURE_DEFINITIONS, project_features


def combinations(options: dict) -> list[dict]:
    keys = list(options)
    return [dict(zip(keys, values)) for values in itertools.product(*options.values())]


def balanced_sample(pools, weights, count, rng):
    """Allocate largest-remainder quotas; repeat stipulated profiles when necessary."""
    quotas = [int(count * weight) for weight in weights]
    order = sorted(range(len(weights)), key=lambda i: (count * weights[i] - quotas[i], -i), reverse=True)
    for i in order[:count - sum(quotas)]:
        quotas[i] += 1
    selected = []
    for pool, quota in zip(pools, quotas):
        pool = pool.copy()
        rng.shuffle(pool)
        selected.extend(pool[i % len(pool)] for i in range(quota))
    rng.shuffle(selected)
    return selected


def sample_candidates(domain: str, count: int, seed: int, catalog: dict) -> list[dict]:
    rng = seeded_random(seed, f"sample:{domain}")
    if domain in ("humans", "legal_cases"):
        states = combinations(HUMAN_STATES if domain == "humans" else LEGAL_STATES)
        rng.shuffle(states)
        if domain == "legal_cases":
            def base_offence(state):
                return (state["property_damage"] and state["intentional_damage"]
                        and state["property_belongs_to_another"] and not state["owner_consent"])
            states = balanced_sample([[s for s in states if base_offence(s)],
                                      [s for s in states if not base_offence(s)]], [0.6, 0.4], count, rng)
        if count > len(states):
            raise ValueError(f"{domain}: maximum {len(states)} distinct constructed profiles")
        return [
            {"species_id": None, "original_identity": f"Fictional {domain} profile {index + 1}",
             "attributes": {}, "state": state, "feature_values": state.copy(),
             "sources": [{"kind": "constructed", "fields": list(state),
                          "description": "Seeded fictional profile / stipulated facts, not an observed person or case."}]}
            for index, state in enumerate(states[:count])
        ]

    species = catalog[domain].copy()
    rng.shuffle(species)
    if domain == "mammals":
        if count > len(species):
            raise ValueError(f"mammals: catalog has {len(species)} distinct species; extend --catalog first")
        states = combinations(MAMMAL_STATES)
        rng.shuffle(states)
        choices = [(row, states[index % len(states)]) for index, row in enumerate(species[:count])]
    else:
        states = combinations(BIRD_STATES if domain == "birds" else PLANT_STATES)
        pools = []
        for row in species:
            variants = states.copy()
            rng.shuffle(variants)
            pools.append([(row, state) for state in variants])
        # Round-robin coverage, then independently randomize identifier assignments.
        choices = [pair for batch in zip(*pools) for pair in batch]
        if count > len(choices):
            raise ValueError(f"{domain}: maximum {len(choices)} distinct species/state profiles")
        if domain == "birds":
            def severity(state):
                if (state["developmental_stage"] == "nestling" or state["wing_condition"] == "unhealed_fracture"
                        or state["fatigue"] == "severe"):
                    return 2
                return int(state["wing_condition"] != "intact" or state["fatigue"] != "rested")
            choices = balanced_sample([[pair for pair in choices if severity(pair[1]) == level]
                                       for level in range(3)], [0.4, 0.4, 0.2], count, rng)
        else:
            choices = choices[:count]
    rng.shuffle(choices)
    return [
        {"species_id": row["species_id"],
         "original_identity": f"{row['name']} ({row['scientific_name']})",
         "attributes": row["attributes"], "state": state,
         "feature_values": {**row["student_features"], **state},
         "sources": row["sources"] + ([{"kind": "constructed", "fields": list(state),
                                         "description": "Specified individual state; not a claim about a wild specimen."}] if state else [])}
        for row, state in choices
    ]


def observe_features(rows: list[dict], names: list[str], seed: int, ambiguity_rate: float,
                     unique_configurations: bool) -> None:
    rng = seeded_random(seed, f"feature_observations:{rows[0]['domain']}")
    preferences = []
    for row in rows:
        complete = project_features(row["domain"], row["raw_feature_values"])
        row["complete_feature_values"] = complete
        decisive = [index for index, name in enumerate(names) if complete[name] != 0.5]
        candidates = []
        for mask in range(1 << len(decisive)):
            count = mask.bit_count()
            if (ambiguity_rate == 0 and count) or (ambiguity_rate == 1 and count != len(decisive)):
                continue
            vector = [complete[name] for name in names]
            for bit, index in enumerate(decisive):
                if mask & (1 << bit):
                    vector[index] = 0.5
            weight = ambiguity_rate ** count * (1 - ambiguity_rate) ** (len(decisive) - count)
            # Weighted selection favors the target rate. Enforcing distinct
            # vectors can increase the realized rate; statistics record it.
            priority = -math.log(max(rng.random(), 1e-300)) / max(weight, 1e-300)
            candidates.append((priority, tuple(vector)))
        candidates.sort(key=lambda item: item[0])
        preferences.append([vector for _, vector in candidates])

    selected = [None] * len(rows)
    owners = {}

    def assign(index, visited):
        if index in visited:
            return False
        visited.add(index)
        for vector in preferences[index]:
            owner = owners.get(vector)
            if owner is None or assign(owner, visited):
                owners[vector] = index
                selected[index] = vector
                return True
        return False

    for index, row in enumerate(rows):
        if unique_configurations:
            # Reassign earlier rows when a partially ambiguous profile has few
            # possible vectors, rather than exhausting its options greedily.
            if not assign(index, set()):
                raise ValueError(f"{row['domain']}: not enough distinct feature configurations; use --allow-duplicate-configurations")
        else:
            selected[index] = preferences[index][0]

    for row, selected_vector in zip(rows, selected):
        vector = list(selected_vector)
        complete = row["complete_feature_values"]
        missing = [name for name in names if complete[name] == 0.5 and
                   any(row["raw_feature_values"].get(field) is None for field in FEATURE_DEFINITIONS[row["domain"]][name]["fields"])]
        row["feature_vector"] = vector
        row["feature_values"] = dict(zip(names, vector))
        row["feature_ambiguity"] = {
            "induced_features": [name for name, value in zip(names, vector) if value == 0.5 and complete[name] != 0.5],
            "source_missing_features": missing,
            "source_ambiguous_features": [name for name in names if complete[name] == 0.5 and name not in missing],
        }


def assign_splits(instances: list[dict], seed: int, split_unit: str, fractions: tuple) -> None:
    groups: dict[str, list] = {}
    for row in instances:
        group = row["species_id"] if split_unit == "species" and row["species_id"] else row["instance_id"]
        row["split_group"] = group
        groups.setdefault(group, []).append(row)
    ordered = sorted(groups)
    seeded_random(seed, f"split:{instances[0]['domain']}").shuffle(ordered)
    # Largest-remainder allocation; positive fractions get one group if possible.
    raw = [len(ordered) * fraction for fraction in fractions]
    counts = [math.floor(value) for value in raw]
    for index in sorted(range(3), key=lambda i: raw[i] - counts[i], reverse=True)[:len(ordered) - sum(counts)]:
        counts[index] += 1
    if len(ordered) >= sum(fraction > 0 for fraction in fractions):
        for index, fraction in enumerate(fractions):
            if fraction > 0 and counts[index] == 0:
                donor = max(range(3), key=lambda i: counts[i])
                counts[donor] -= 1
                counts[index] = 1
    cursor = 0
    for split, number in zip(("train", "validation", "test"), counts):
        for group in ordered[cursor:cursor + number]:
            for row in groups[group]:
                row["split"] = split
        cursor += number
    seen = {tuple(row["feature_vector"]) for row in instances if row["split"] == "train"}
    for row in instances:
        row["configuration_status"] = (
            "training" if row["split"] == "train" else
            "seen_configuration" if tuple(row["feature_vector"]) in seen else "new_configuration"
        )


def make_schedules(instances: list[dict], seed: int, initial_fraction: float) -> dict:
    result = {}
    for domain in dict.fromkeys(row["domain"] for row in instances):
        training = [row["instance_id"] for row in instances if row["domain"] == domain and row["split"] == "train"]
        seeded_random(seed, f"schedule:{domain}").shuffle(training)
        cut = max(1, math.ceil(len(training) * initial_fraction)) if training else 0
        phase = {key: "initial" if i < cut else "expansion" for i, key in enumerate(training)}
        instance_wise = []
        interleaved = []
        for key in training:
            introduction = {"event": "introduce", "instance_id": key, "phase": phase[key]}
            instance_wise.append(introduction)
            interleaved.append(introduction)
            for context in DOMAINS[domain]["contexts"]:
                instance_wise.append({"event": "observe", "pair_id": f"{key}/{context['context_id']}", "phase": phase[key]})
            interleaved.append({"event": "observe", "pair_id": f"{key}/c_1", "phase": phase[key]})
        for context in (item["context_id"] for item in DOMAINS[domain]["contexts"][1:]):
            interleaved.extend({"event": "observe", "pair_id": f"{key}/{context}", "phase": "delayed_observation"} for key in training)
        observations = [f"{key}/{context['context_id']}" for key in training for context in DOMAINS[domain]["contexts"]]
        seeded_random(seed, f"joint:{domain}").shuffle(observations)
        result[domain] = {
            "initial_instances": training[:cut], "expansion_instances": training[cut:],
            "instance_wise": instance_wise, "context_interleaved": interleaved,
            "joint_shuffled": ([{"event": "introduce", "instance_id": key, "phase": "joint"} for key in training]
                               + [{"event": "observe", "pair_id": key, "phase": "joint"} for key in observations]),
        }
    return result


def feature_statistics(rows: list[dict]) -> dict:
    total = sum(len(row["feature_vector"]) for row in rows)
    source_missing = sum(len(row["feature_ambiguity"]["source_missing_features"]) for row in rows)
    source_ambiguous = sum(len(row["feature_ambiguity"]["source_ambiguous_features"]) for row in rows)
    induced = sum(len(row["feature_ambiguity"]["induced_features"]) for row in rows)
    decisive = total - source_missing - source_ambiguous
    return {"configurations": len({tuple(row["feature_vector"]) for row in rows}),
            "ambiguous_values": source_missing + source_ambiguous + induced,
            "source_missing_values": source_missing, "source_ambiguous_values": source_ambiguous,
            "induced_values": induced, "total_values": total,
            "actual_induced_rate": induced / decisive if decisive else None}


def generate(args: argparse.Namespace) -> dict:
    catalog = read_json(args.catalog)
    instances, pairs, specifications = [], [], {}
    for domain in args.domains:
        spec = DOMAINS[domain]
        feature_names = list(FEATURE_DEFINITIONS[domain])
        rows = sample_candidates(domain, args.num_per_domain, args.seed, catalog)
        for index, row in enumerate(rows, 1):
            row.update({"domain": domain, "target": spec["target"],
                        "instance_id": f"{spec['prefix']}_{index:03d}",
                        "anonymous_id": f"{spec['prefix']} {index:03d}"})
            row["raw_feature_values"] = row["feature_values"]
        observe_features(rows, feature_names, args.seed, args.feature_ambiguity_rate, args.unique_configurations and domain != "mammals")
        assign_splits(rows, args.seed, args.split_unit, (args.train_fraction, args.validation_fraction, 1 - args.train_fraction - args.validation_fraction))
        instances.extend(rows)
        specifications[domain] = {**spec, "feature_encoding": "ternary_judgments",
                                  "feature_definitions": FEATURE_DEFINITIONS[domain],
                                  "feature_vocabulary": {name: [0, 0.5, 1] for name in feature_names},
                                  "feature_ambiguity_semantics": "0=false, 0.5=ambiguous/partial judgment, 1=true. Stored numerically; displayed as 1/2. Not a calibrated probability. Teacher references use the full raw profile.",
                                  "feature_names": feature_names}
        for row in rows:
            for context in spec["contexts"]:
                prompt = render_teacher_prompt(row, spec, context)
                pairs.append({
                    "pair_id": f"{row['instance_id']}/{context['context_id']}",
                    "instance_id": row["instance_id"], "anonymous_id": row["anonymous_id"],
                    "domain": domain, "target": spec["target"], "context_id": context["context_id"],
                    "split": row["split"], "configuration_status": row["configuration_status"],
                    "teacher_prompt": prompt, "input_hash": digest(prompt),
                    "student_prompts": {variant: render_student_prompt(row, specifications[domain], context, variant) for variant in VARIANTS},
                })

    payloads = {
        "instances.jsonl": instances, "pairs.jsonl": pairs,
        "specifications.json": specifications,
        "schedules.json": make_schedules(instances, args.seed, args.initial_fraction),
    }
    for name in (*payloads, "manifest.json"):
        if (args.output_dir / name).exists() and not args.overwrite:
            raise ValueError(f"{args.output_dir / name} exists. Use another --output-dir or --overwrite.")
    for name, payload in payloads.items():
        (write_jsonl if name.endswith(".jsonl") else write_json)(args.output_dir / name, payload)
    manifest = {
        "schema_version": SCHEMA_VERSION, "source_document": "docs/AISTATS2027PaperPack.pdf",
        "design_basis": "Appendix A.1-A.3; specific contexts and species catalog are implementation choices",
        "seed": args.seed, "domains": args.domains, "num_per_domain": args.num_per_domain,
        "feature_encoding": "ternary_judgments", "feature_dimensions": 7,
        "feature_ambiguity_rate": args.feature_ambiguity_rate, "unique_configurations": args.unique_configurations,
        "unique_configurations_by_domain": {domain: args.unique_configurations and domain != "mammals" for domain in args.domains},
        "feature_statistics": {
            domain: feature_statistics([row for row in instances if row["domain"] == domain])
            for domain in args.domains
        },
        "initial_fraction": args.initial_fraction,
        "num_instances": len(instances), "num_pairs": len(pairs), "contexts_per_domain": len(specifications[args.domains[0]]["contexts"]),
        "split_unit": args.split_unit,
        "split_fractions": {"train": args.train_fraction, "validation": args.validation_fraction,
                            "test": round(1 - args.train_fraction - args.validation_fraction, 10)},
        "catalog_sha256": file_digest(args.catalog), "catalog_provenance": catalog["provenance"],
        "files": {name: file_digest(args.output_dir / name) for name in payloads},
        "counts": {domain: {split: sum(row["domain"] == domain and row["split"] == split for row in instances)
                           for split in ("train", "validation", "test")} for domain in args.domains},
        "reference_types": None,
        "notes": ["Teacher-reference dataset; computational reference types are not inferred from labels.",
                  "Unknown attributes remain explicit unknown values, not negative facts.",
                  "Seven feature judgments use 0/0.5/1; 0.5 is displayed as 1/2 and means ambiguous, not a calibrated probability.",
                  "Intermediate raw states, missing source facts, and constructed ambiguity are recorded separately.",
                  "Teacher references use full raw facts; student feature ambiguity does not change the binary target.",
                  "At most 3^7=2187 configurations; predicate dependencies and source coverage restrict achievable combinations.",
                  "Weighted sampling targets the requested ambiguity rate; selecting unique vectors can increase the actual induced rate.",
                  "Mammal taxonomy is source-grounded; uncollected physical attributes are omitted.",
                  "ConceptNet collection is not included in this initial catalog; curated supplementary sources are used."],
    }
    manifest["dataset_fingerprint"] = digest(manifest)
    write_json(args.output_dir / "manifest.json", manifest)
    return manifest


def parse_args(argv=None) -> argparse.Namespace:
    load_environment()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-per-domain", type=int, default=int(os.getenv("DATASET_NUM_PER_DOMAIN", "100")))
    parser.add_argument("--seed", type=int, default=int(os.getenv("DATASET_SEED", "2027")))
    parser.add_argument("--feature-ambiguity-rate", type=float, default=float(os.getenv("DATASET_FEATURE_AMBIGUITY_RATE", "0.2")),
                        help="Target fraction of definite judgments made ambiguous (default: 0.2); 0 uses source judgments only")
    parser.add_argument("--allow-duplicate-configurations", action="store_true",
                        help="Allow instances to share feature vectors; automatically enabled at ambiguity rate 0 or 1")
    parser.add_argument("--domains", nargs="+", choices=list(DOMAINS), default=list(DOMAINS))
    parser.add_argument("--catalog", type=Path, default=ROOT / "configs/species_catalog.json")
    parser.add_argument("--output-dir", type=Path, default=configured_path("DATASET_INPUT_DIR", "data/current/inputs"))
    parser.add_argument("--split-unit", choices=("species", "instance"), default=os.getenv("DATASET_SPLIT_UNIT", "instance"))
    parser.add_argument("--train-fraction", type=float, default=float(os.getenv("DATASET_TRAIN_FRACTION", "0.8")))
    parser.add_argument("--validation-fraction", type=float, default=float(os.getenv("DATASET_VALIDATION_FRACTION", "0.0")))
    parser.add_argument("--initial-fraction", type=float, default=float(os.getenv("DATASET_INITIAL_FRACTION", "0.5")))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    if not math.isfinite(args.feature_ambiguity_rate) or not 0 <= args.feature_ambiguity_rate <= 1:
        parser.error("--feature-ambiguity-rate must be between 0 and 1")
    args.unique_configurations = not args.allow_duplicate_configurations and 0 < args.feature_ambiguity_rate < 1
    if args.num_per_domain < 1:
        parser.error("--num-per-domain must be positive")
    if not (0 < args.train_fraction <= 1 and 0 <= args.validation_fraction < 1 and args.train_fraction + args.validation_fraction <= 1):
        parser.error("split fractions must be nonnegative, sum to at most 1, and include training data")
    if not 0 < args.initial_fraction <= 1:
        parser.error("--initial-fraction must be in (0, 1]")
    if len(set(args.domains)) != len(args.domains):
        parser.error("--domains must not contain duplicates")
    return args


def main(argv=None) -> int:
    try:
        args = parse_args(argv)
        manifest = generate(args)
        print(f"Generated {manifest['num_instances']} instances / {manifest['num_pairs']} pairs: {args.output_dir}")
        for domain, counts in manifest["counts"].items():
            print(f"  {domain}: {counts}")
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Stage 1 failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
