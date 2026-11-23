"""Publish the allowlisted projection of a ReplayBench Registry v1 JSON export."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import html
import ipaddress
import json
import math
from pathlib import Path
import re
import sys
import tempfile
from uuid import uuid4


SCHEMA = 1
TRACKS = {"direct_model": "Direct Model", "pi_agent": "Pi Agent"}
SHA256 = re.compile(r"[a-f0-9]{64}")
SNAPSHOT_ID = re.compile(r"\d{4}-\d{2}-\d{2}-[a-f0-9]{12}")
IDENTITY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}")
LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.+ ()-]{0,159}")
VERSION_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.+ (),-]{0,159}")
MODEL = re.compile(r"(?:[A-Za-z0-9][A-Za-z0-9_.-]{0,59}/)?[A-Za-z0-9][A-Za-z0-9_.+ ()-]{0,159}")
CHECK_ID = re.compile(r"(?=.{1,160}$)[A-Za-z0-9_][A-Za-z0-9_.-]*(?:/[A-Za-z0-9_][A-Za-z0-9_.-]*){0,7}")
ENTRY_POINT = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*(?::[A-Za-z_][A-Za-z0-9_]*)?")
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})")
LLAMA_VERSION = re.compile(
    r"(?:\d{1,3}(?:\.\d{2,3}){3} I srv  llama_server: initializing \.\.\.\r?\n)?"
    r"version: (?P<version>[A-Za-z0-9_.+-]+ \(build \d+, commit [a-f0-9]+\))"
    r"(?:\r?\nbuilt with GNU [\d.]+ for [A-Za-z0-9_ -]+\r?\n?)?"
)
PRIVATE = re.compile(
    r"(?:[A-Za-z]:[\\/]|\\\\|(?:^|\s)(?:~/|/)\S|://|"
    r"(?:^|[/\\])(?:Users|home|AppData|private)(?:[/\\]|$)|"
    r"\b(?:localhost|[\w-]+\.local|[\w-]+\.internal)\b|"
    r"[\w.+-]+@[\w.-]+\.[a-z]{2,}|\b(?:Bearer|Authorization|api[_ -]?key|password)[ :=]+|"
    r"\b(?:AKIA[A-Z0-9]{16}|ASIA[A-Z0-9]{16}|gh[pousr]_[A-Za-z0-9]+|github_pat_[A-Za-z0-9_]+|"
    r"sk-[A-Za-z0-9_-]{12,}|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)\b|"
    r"-----BEGIN .*PRIVATE KEY-----|\[?[0-9a-f]{0,4}::[0-9a-f:]+)",
    re.IGNORECASE,
)
IPV4 = re.compile(r"(?<![0-9])(?=((?:[0-9]{1,3}\.){3}[0-9]{1,3})(?![0-9]))")
SAFE_REASONS = (
    "Incorrect value", "Incorrect epistemic status", "Fabricated or noncontiguous quote",
    "Missing relevant evidence", "Missing evidence coverage", "Incomplete evidence chain",
    "Execution or JSON parsing failed", "Check could not be evaluated",
)

# Rules describe source leaves that can be copied. The four derived groups below
# (verifier digest, candidate/metadata flags, failures and timing aliases) are built explicitly.
REASONING = {"enabled": bool, "mode": IDENTITY, "budget_tokens": "number", "effort": IDENTITY}
SETTINGS = {
    **dict.fromkeys(("threads", "temperature", "top_p", "top_k", "seed", "max_tokens",
                     "spec", "spec_min_p", "parallel", "vram_reserve_mib", "arena_pin_gib",
                     "max_context_tokens", "context_window", "kv_resident_tokens", "reasoning_budget"), "number"),
    **dict.fromkeys(("drafting", "esp", "cache_type_k", "cache_type_v", "reasoning_effort"), "setting"),
    "vision": bool,
    "speculative": {"enabled": bool, "mode": IDENTITY, "draft_max": "number", "draft_min": "number", "p_min": "number"},
    "kv_cache": "cache",
    "reasoning": REASONING,
}
ALLOWLIST = {
    "run_id": IDENTITY,
    "track": IDENTITY,
    "task": {"id": IDENTITY, "version": IDENTITY, "manifest_sha256": SHA256,
             "source_sha256": SHA256, "input_sha256": SHA256},
    "verifier": {"name": IDENTITY, "revision": IDENTITY},
    "subject": {"id": IDENTITY},
    "model": {"declared": MODEL, "requested": MODEL, "observed": MODEL, "revision": IDENTITY,
              "quantization": LABEL, "context_window": "number", "reasoning": REASONING},
    "backend": {"name": LABEL, "version": "version"},
    "hardware": {"gpu": LABEL, "vram_gb": "number", "ram_gb": "number"},
    "agent": {"name": LABEL, "version": LABEL, "model_invocation_count": "number",
              "tool_call_count": "number", "tool_error_count": "number", "retry_count": "number"},
    "execution": {"status": IDENTITY, "started_at": TIMESTAMP, "adapter_seconds": "number",
                  "client_wall_seconds": "number", "verification_seconds": "number"},
    "result": {"score": "number", "strict_pass": bool},
    "tokens": dict.fromkeys(("prompt", "completion", "cache_read", "cache_write", "tool_calls"), "number"),
    "server": dict.fromkeys(("prompt_tokens_per_second", "generation_tokens_per_second", "draft_acceptance_rate"), "number"),
    "runtime": {
        "effective_context_window": "number", "effective_reasoning_budget": "number",
        "observed_reasoning_present": bool,
        **dict.fromkeys(("declared_context", "subject_declared_settings", "operator_declared_settings",
                         "requested_parameters"), SETTINGS),
    },
}
CACHE = {"type": IDENTITY, "type_k": IDENTITY, "type_v": IDENTITY, "resident_tokens": "number"}
TIMING_FIELDS = {"cache_n": "cached_tokens", "draft_n": "draft_tokens", "draft_n_accepted": "accepted_draft_tokens"}


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def digest(content):
    return hashlib.sha256(content).hexdigest()


def field_paths(value, prefix=""):
    if isinstance(value, dict) and value:
        return {path for key, item in value.items() for path in field_paths(item, f"{prefix}.{key}" if prefix else key)}
    if isinstance(value, list) and value:
        return {path for item in value for path in field_paths(item, prefix + "[]")}
    return {prefix}


def object_value(value):
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("Expected a Registry object")
    return value


def private_text(text, username):
    if PRIVATE.search(text) or (username and re.search(rf"(?<!\w){re.escape(username)}(?!\w)", text, re.I)):
        return True
    for match in IPV4.finditer(text):
        try:
            ipaddress.IPv4Address(match[1])
        except ipaddress.AddressValueError:
            continue
        return True
    return False


class Projection:
    def __init__(self, records, username, violations):
        self.records = records
        self.username = username
        self.violations = violations
        self.included = set()

    def leaf(self, reading, rule, field):
        if reading is None:
            return None
        if rule == "version":
            wrapper = LLAMA_VERSION.fullmatch(reading) if isinstance(reading, str) else None
            if wrapper:
                reading = wrapper["version"]
            rule = VERSION_LABEL
        if rule == "cache":
            if isinstance(reading, dict):
                return self.fields(reading, CACHE, field)
            rule = IDENTITY
        numeric = type(reading) is int or type(reading) is float and math.isfinite(reading)
        if rule == "setting":
            if numeric or isinstance(reading, bool):
                return reading
            rule = IDENTITY
        if (rule == "number" and numeric) or (rule is bool and type(reading) is bool):
            return reading
        if isinstance(rule, re.Pattern) and isinstance(reading, str):
            # Timestamp zone offsets and digests have their own exact grammars.
            if rule not in (TIMESTAMP, SHA256) and private_text(reading, self.username):
                self.violations.append({"record_index": self.index, "field": field, "reason": "Possible private value"})
                return None
            if rule.fullmatch(reading):
                if rule is TIMESTAMP:
                    try:
                        datetime.fromisoformat(reading.replace("Z", "+00:00"))
                    except ValueError:
                        self.violations.append({"record_index": self.index, "field": field, "reason": "Invalid timestamp"})
                        return None
                return reading
        self.violations.append({"record_index": self.index, "field": field, "reason": "Unexpected public value format"})
        return None

    def fields(self, source, rules, prefix=""):
        source = object_value(source)
        output = {}
        for name, rule in rules.items():
            field = f"{prefix}.{name}" if prefix else name
            reading = source.get(name)
            if isinstance(rule, dict):
                # Top-level groups always exist in public v1. Nested unknowns stay null.
                if reading is not None or not prefix:
                    output[name] = self.fields(reading, rule, field)
                else:
                    output[name] = None
            else:
                output[name] = self.leaf(reading, rule, field)
        return output

    def run(self, source, index):
        self.index = index
        public = self.fields(source, ALLOWLIST)
        task, verifier = public["task"], public["verifier"]
        entry_point = self.leaf(object_value(source.get("verifier")).get("entry_point"), ENTRY_POINT, "verifier.entry_point")
        required = (public["run_id"], public["subject"]["id"], public["execution"]["status"], *task.values(), entry_point)
        if not all(required) and not self.violations:
            raise ValueError(f"Record {index} is missing required Run, Subject, Task, execution, or verifier identity")
        task["candidate"] = bool(task["version"] and task["version"].lower().endswith("-candidate"))
        verifier["identity_sha256"] = digest(json_bytes([entry_point, verifier["name"], verifier["revision"]]))
        result = object_value(source.get("result"))
        critical = result.get("critical_failures")
        details = {item.get("id"): item for item in result.get("critical_failure_details") or []}
        public["result"]["critical_failures"] = None if critical is None else []
        public["result"]["critical_failure_details"] = None if critical is None else []
        for identifier in critical or []:
            safe_id = self.leaf(identifier, CHECK_ID, "result.critical_failures[]")
            if safe_id is None:
                continue
            detail = details.get(identifier, {})
            dimension = self.leaf(detail.get("dimension"), IDENTITY, "result.critical_failure_details[].dimension")
            source_reasons = detail.get("reasons")
            reasons = [reason for reason in SAFE_REASONS if isinstance(source_reasons, list) and reason in source_reasons]
            summary = " · ".join(reasons) if reasons else "Flagged by the verifier."
            public["result"]["critical_failures"].append(safe_id)
            public["result"]["critical_failure_details"].append({"id": safe_id, "dimension": dimension, "summary": summary})
        timings = object_value(object_value(source.get("server")).get("raw_timings"))
        for original, canonical in TIMING_FIELDS.items():
            public["server"][canonical] = self.leaf(timings.get(original), "number", f"server.raw_timings.{original}")
        subject = re.search(r"\bqwen(\d+\.\d+)\b", public["subject"]["id"] or "", re.I)
        declared = re.search(r"\bqwen(\d+\.\d+)\b", public["model"]["declared"] or "", re.I)
        mismatch = subject and declared and subject[1] != declared[1]
        public["metadata_flags"] = ["subject_model_version_mismatch"] if mismatch else []
        self.included.update(field_paths(public))
        return public

    def project(self):
        return sorted((self.run(source, index) for index, source in self.records), key=lambda run: run["run_id"] or "")


def atomic_write(path, content):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temp = Path(stream.name)
        try:
            stream.write(content)
            stream.close()
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)


def coverage(records):
    tasks = {(r["task"]["id"], r["task"]["version"], r["task"]["manifest_sha256"]) for r in records}
    verifiers = {r["verifier"]["identity_sha256"]: r["verifier"] for r in records}
    return {
        "task_coverage": [
            {"id": name, "version": version, "manifest_sha256": sha} for name, version, sha in sorted(tasks)
        ],
        "verifier_coverage": [verifiers[key] for key in sorted(verifiers)],
    }


def markdown(snapshot, records):
    def cell(item):
        if item is None:
            return "—"
        if isinstance(item, bool):
            return "Yes" if item else "No"
        return re.sub(r"([\\|`*_[\]])", r"\\\1", html.escape(str(item), quote=False))

    lines = ["# ReplayBench benchmark results", "", f"Snapshot `{snapshot}` · {len(records)} archived Runs", "",
             "Compare scores within the same track, exact Task and input, and matching verifier identity and revision.",
             "An em dash marks unavailable data. Execution status and strict pass are recorded independently.", ""]
    for track, label in TRACKS.items():
        rows = [r for r in records if r["track"] == track]
        if not rows:
            continue
        lines += [f"## {label}", "",
                  "| Run | Model | Quantization | Backend / GPU | Task | Verifier | Execution | Score | Strict pass |",
                  "| --- | --- | --- | --- | --- | --- | --- | ---: | --- |"]
        for r in rows:
            model, task, verifier = r["model"], r["task"], r["verifier"]
            task_label = f"{task['id']} {task['version']} ({task['manifest_sha256'][:8]})"
            verifier_label = " ".join(filter(None, [verifier["name"], verifier["revision"]])) or None
            hardware = " / ".join(filter(None, [r["backend"]["name"], r["hardware"]["gpu"]])) or None
            name = model["declared"] or model["observed"]
            if r["metadata_flags"]:
                name = f"{name} (Subject metadata under review)"
            values = (r["run_id"], name, model["quantization"], hardware, task_label, verifier_label,
                      r["execution"]["status"], r["result"]["score"], r["result"]["strict_pass"])
            lines.append("| " + " | ".join(map(cell, values)) + " |")
        lines.append("")
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def catalog_entries(path):
    if not path.exists():
        return []
    catalog = json.loads(path.read_bytes())
    if catalog.get("public_schema_version") != SCHEMA or not isinstance(catalog.get("snapshots"), list):
        raise ValueError("Unsupported snapshot catalog")
    entries = []
    for entry in catalog["snapshots"]:
        snapshot, checksum, created, count = (entry[key] for key in
                                               ("snapshot_id", "data_sha256", "generated_at_utc", "record_count"))
        if not (SNAPSHOT_ID.fullmatch(snapshot) and SHA256.fullmatch(checksum)
                and snapshot.endswith(checksum[:12]) and TIMESTAMP.fullmatch(created)
                and type(count) is int and count >= 0):
            raise ValueError("Invalid snapshot catalog entry")
        entries.append({"snapshot_id": snapshot, "data_sha256": checksum,
                        "generated_at_utc": created, "record_count": count})
    return entries


def write_release(data, content, records, checksum, source_checksum, generated):
    data.mkdir(parents=True, exist_ok=True)
    lock = data / ".publish-lock"
    lock.mkdir()
    try:
        catalog_path = data / "catalog.json"
        entries = catalog_entries(catalog_path)
        previous = next((item for item in entries if item["data_sha256"] == checksum), None)
        snapshot = previous["snapshot_id"] if previous else f"{generated.date()}-{checksum[:12]}"
        snapshots = data / "snapshots"
        target = snapshots / snapshot
        timestamp = generated.isoformat(timespec="seconds").replace("+00:00", "Z")
        entry = {"snapshot_id": snapshot, "data_sha256": checksum,
                 "generated_at_utc": timestamp, "record_count": len(records)}
        manifest = {
            "public_schema_version": SCHEMA, **entry, **coverage(records),
            "track_distribution": dict(Counter(r["track"] for r in records)),
            "source_registry_sha256": source_checksum,
        }
        if target.exists() or previous:
            if not target.is_dir() or (target / "benchmark.json").read_bytes() != content:
                raise ValueError(f"Snapshot {snapshot} differs from the generated data")
            saved = object_value(json.loads((target / "manifest.json").read_bytes()))
            for field, expected in manifest.items():
                if field not in ("source_registry_sha256", "generated_at_utc") and (
                    json_bytes(saved.get(field)) != json_bytes(expected)
                ):
                    raise ValueError(f"Snapshot {snapshot} has invalid manifest {field}")
            # The manifest preserves the provenance and timestamp of the original release.
            source_digest = saved.get("source_registry_sha256")
            if not isinstance(source_digest, str) or not SHA256.fullmatch(source_digest):
                raise ValueError(f"Snapshot {snapshot} has invalid manifest source_registry_sha256")
            created = saved.get("generated_at_utc")
            if not isinstance(created, str) or not TIMESTAMP.fullmatch(created):
                raise ValueError(f"Snapshot {snapshot} has invalid manifest generated_at_utc")
            created_at = datetime.fromisoformat(created.replace("Z", "+00:00"))
            if created_at.utcoffset() != timezone.utc.utcoffset(None) or created[:10] != snapshot[:10]:
                raise ValueError(f"Snapshot {snapshot} has invalid manifest generated_at_utc")
            entry["generated_at_utc"] = created
            catalog_entry = next((item for item in entries if item["snapshot_id"] == snapshot), None)
            if catalog_entry is not None and catalog_entry != entry:
                raise ValueError(f"Snapshot {snapshot} manifest and catalog disagree")
        else:
            snapshots.mkdir(exist_ok=True)
            temporary = snapshots / f".snapshot-{uuid4().hex}"
            temporary.mkdir()
            try:
                (temporary / "benchmark.json").write_bytes(content)
                (temporary / "manifest.json").write_bytes(json_bytes(manifest))
                temporary.rename(target)
            finally:
                if temporary.exists():
                    (temporary / "benchmark.json").unlink(missing_ok=True)
                    (temporary / "manifest.json").unlink(missing_ok=True)
                    temporary.rmdir()
        entries = [entry, *(item for item in entries if item["snapshot_id"] != snapshot)]
        entries.sort(key=lambda item: (item["generated_at_utc"], item["snapshot_id"]), reverse=True)
        atomic_write(data / "latest.json", content)
        atomic_write(data / "benchmark.md", markdown(snapshot, records))
        atomic_write(catalog_path, json_bytes({"public_schema_version": SCHEMA, "latest_snapshot_id": snapshot,
                                               "snapshots": entries}))
        return snapshot
    finally:
        lock.rmdir()


def publish(input_path, out, audit_path, generated=None):
    input_path, out, audit_path = (Path(path).resolve() for path in (input_path, out, audit_path))
    data = (out / "data").resolve()
    if input_path.is_relative_to(out) or input_path.is_relative_to(data):
        raise ValueError("Keep the source Registry outside the public output directory")
    if audit_path.is_relative_to(out) or audit_path.is_relative_to(data) or audit_path == input_path:
        raise ValueError("Keep the privacy audit outside the public output directory and source Registry file")
    raw = input_path.read_bytes()
    registry = object_value(json.loads(raw))
    if registry.get("kind") != "replaybench_registry" or registry.get("format_version") != 1:
        raise ValueError("Expected a ReplayBench Registry v1 export")
    source_records, issues = registry["records"], registry["issues"]
    if not isinstance(source_records, list) or not isinstance(issues, list):
        raise ValueError("Expected Registry records and issues arrays")
    seen = set()
    excluded = Counter()
    eligible = []
    for index, record in enumerate(source_records, 1):
        record = object_value(record)
        run_id = record.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            raise ValueError(f"Record {index} is missing a Run ID")
        if run_id in seen:
            raise ValueError(f"Duplicate Run ID at record {index}")
        seen.add(run_id)
        track = record["track"]
        if track in TRACKS:
            eligible.append((index, record))
        else:
            excluded[track] += 1
    if not eligible:
        raise ValueError("No eligible Direct Model or Pi Agent records")
    username = next((item for parent, item in zip(input_path.parts, input_path.parts[1:])
                     if parent.lower() in {"users", "home"}), None)
    violations = []
    projection = Projection(eligible, username, violations)
    records = projection.project()
    content = None if violations else json_bytes({"public_schema_version": SCHEMA, "records": records})
    checksum = digest(content) if content is not None else None
    source_fields = {field for _, record in eligible for field in field_paths(record)}
    audit = {
        "input_record_count": len(source_records), "published_record_count": 0,
        "eligible_record_count": len(records), "excluded_track_count": sum(excluded.values()),
        "excluded_track_distribution": dict(excluded),
        "excluded_invalid_archive_count": sum(issue.get("reason") == "invalid_archive" for issue in issues),
        "included_public_fields": sorted(projection.included),
        "omitted_source_record_fields": sorted(source_fields - projection.included),
        "privacy_violations": violations, "public_data_sha256": checksum, "source_registry_sha256": digest(raw),
    }
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(audit_path, json_bytes(audit))
    if violations:
        raise ValueError(f"Privacy audit failed for {len(violations)} field values. See the local audit report.")
    snapshot = write_release(data, content, records, checksum, audit["source_registry_sha256"],
                             generated or datetime.now(timezone.utc))
    audit["published_record_count"] = len(records)
    audit["snapshot_id"] = snapshot
    atomic_write(audit_path, json_bytes(audit))
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="ReplayBench Registry JSON export")
    parser.add_argument("--out", required=True, type=Path, help="Static output root, such as public")
    parser.add_argument("--audit", default=Path(".review/privacy-audit.json"), type=Path, help="Local audit report")
    args = parser.parse_args()
    try:
        audit = publish(args.input, args.out, args.audit)
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(f"Release failed: {error}", file=sys.stderr)
        return 1
    print(f"{audit['snapshot_id']}: {audit['published_record_count']} of {audit['input_record_count']} records; "
          f"{audit['excluded_track_count']} excluded by track; "
          f"{audit['excluded_invalid_archive_count']} invalid archives reported upstream.")
    print(f"SHA-256: {audit['public_data_sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
