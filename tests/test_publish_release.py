from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from tools.publish_release import ELIGIBLE_STATUSES, publish


def sample(run_id, track="direct_model", **fields):
    return {
        "run_id": run_id, "track": track,
        "task": {"id": "sample", "version": "0.2.0-candidate", "manifest_sha256": "a" * 64,
                 "input_sha256": "b" * 64, "source_sha256": "c" * 64},
        "subject": {"id": "qwen3.8-sample"},
        "model": {"declared": "Qwen3.6 sample", "full_prompt": "private sample prompt"},
        "verifier": {"name": "verified", "revision": "0.2.0", "entry_point": "example:verify"},
        "execution": {"status": "completed", "started_at": "2026-11-10T09:00:00Z"},
        "result": {"score": 0, "strict_pass": False, "critical_failures": ["case/1/field"],
                   "critical_failure_details": [{"id": "case/1/field", "dimension": "schema",
                                                  "reasons": ["Incorrect value", "private reason details"]}]},
        "runtime": {"system_fingerprint": "private fingerprint"},
        "server": {"raw_timings": {"draft_n": 7, "unused": 17}},
        "local_path": r"C:\Users\private\archive",
        **fields,
    }


class PublisherTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.registry = root / "registry.json"
        self.out = root / "public"
        self.audit_path = root / "review" / "audit.json"
        self.generation = datetime(2026, 11, 23, tzinfo=timezone.utc)

    def source(self, records):
        self.registry.write_text(json.dumps({"kind": "replaybench_registry", "format_version": 1,
                                             "records": records, "issues": [{"reason": "invalid_archive"}]}),
                                 encoding="utf-8")

    def run_release(self, day=None, hardware_overlay=None):
        return publish(self.registry, self.out, self.audit_path, day or self.generation,
                       hardware_overlay=hardware_overlay)

    def overlay(self, runs, source_hash=None):
        path = self.registry.parent / "hardware-overlay.json"
        path.write_text(json.dumps({"source_registry_sha256": source_hash or hashlib.sha256(self.registry.read_bytes()).hexdigest(),
                                    "runs": runs}), encoding="utf-8")
        return path

    def release_files(self):
        return {path.relative_to(self.out): path.read_bytes() for path in self.out.rglob("*") if path.is_file()}

    def test_allowlist_and_execution_results(self):
        failed = sample("two", "pi_agent", execution={"status": "timeout"}, result={"score": None})
        self.source([sample("one"), failed, sample("test", "self_test")])
        source_before = self.registry.read_bytes()
        audit = self.run_release()
        latest = self.out / "data" / "latest.json"
        raw = latest.read_bytes()
        records = json.loads(raw)["records"]
        manifest_path = latest.parent / "snapshots" / audit["snapshot_id"] / "manifest.json"
        manifest = json.loads(manifest_path.read_bytes())
        self.assertEqual(raw, manifest_path.with_name("benchmark.json").read_bytes())
        self.assertEqual(audit["published_record_count"], 2)
        self.assertEqual(audit["excluded_track_distribution"], {"self_test": 1})
        self.assertEqual(audit["excluded_invalid_archive_count"], 1)
        self.assertEqual(manifest["track_distribution"], {"direct_model": 1, "pi_agent": 1})
        self.assertEqual(manifest["data_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(manifest["source_registry_sha256"], hashlib.sha256(source_before).hexdigest())
        self.assertEqual(self.registry.read_bytes(), source_before)
        self.assertEqual(records[0]["result"]["score"], 0)
        self.assertFalse(records[0]["result"]["strict_pass"])
        self.assertTrue(records[0]["task"]["candidate"])
        self.assertEqual(records[0]["metadata_flags"], ["subject_model_version_mismatch"])
        self.assertEqual(records[0]["result"]["critical_failure_details"][0]["summary"], "Incorrect value")
        self.assertEqual(records[0]["server"]["draft_tokens"], 7)
        self.assertEqual(records[1]["execution"]["status"], "timeout")
        self.assertIsNone(records[1]["result"]["score"])
        self.assertNotIn(b"private", raw)
        self.assertNotIn(b"unused", raw)
        self.assertNotIn(b"entry_point", raw)
        self.assertEqual(audit["privacy_violations"], [])

    def test_duplicate_and_missing_identity_are_rejected(self):
        self.source([sample("duplicate"), sample("duplicate", "self_test")])
        with self.assertRaisesRegex(ValueError, "Duplicate Run ID"):
            self.run_release()
        self.source([sample("missing", subject={})])
        with self.assertRaisesRegex(ValueError, "missing required"):
            self.run_release()
        self.assertFalse(self.out.exists())

    def test_privacy_failure_preserves_current_release(self):
        self.source([sample("one")])
        self.run_release()
        data = self.out / "data"
        before = (data / "latest.json").read_bytes()
        for text in (r"C:\Users\private\archive", "/home/private/run", "192.168.1.20", "127.0.0.1", "8.8.8.8",
                     "relay.1.1.1.1-west", "Model relay 8.8.4.4.", "Bearer private-credential",
                     "person@example.com", "sk-fakecredential12345"):
            with self.subTest(text=text):
                self.source([sample("bad", model={"declared": text})])
                with self.assertRaisesRegex(ValueError, "Privacy audit failed"):
                    self.run_release()
                audit = json.loads(self.audit_path.read_bytes())
                self.assertEqual(audit["published_record_count"], 0)
                self.assertIsNone(audit["public_data_sha256"])
                self.assertEqual(audit["privacy_violations"], [
                    {"field": "model.declared", "reason": "Possible private value", "record_index": 1}
                ])
                self.assertNotIn(text, self.audit_path.read_text(encoding="utf-8"))
                self.assertEqual((data / "latest.json").read_bytes(), before)
        self.assertEqual(len(list((data / "snapshots").iterdir())), 1)

    def test_backend_version_wrapper_checks_extracted_value(self):
        def version(label):
            return f"0.00.000.127 I srv  llama_server: initializing ...\nversion: {label} (build 5, commit abc123)"

        self.source([sample("safe", backend={"version": version("1.2.3")})])
        self.run_release()
        records = json.loads((self.out / "data" / "latest.json").read_bytes())["records"]
        self.assertEqual(records[0]["backend"]["version"], "1.2.3 (build 5, commit abc123)")
        self.source([sample("bad", backend={"version": version("8.8.8.8")})])
        with self.assertRaisesRegex(ValueError, "Privacy audit failed"):
            self.run_release()
        audit = json.loads(self.audit_path.read_bytes())
        self.assertEqual(audit["privacy_violations"], [
            {"field": "backend.version", "reason": "Possible private value", "record_index": 1}
        ])

    def test_empty_and_self_test_only_registries_preserve_release(self):
        self.source([sample("one")])
        self.run_release()
        self.source([sample("two", "pi_agent")])
        self.run_release(self.generation.replace(day=24))
        before = self.release_files()
        audit_before = self.audit_path.read_bytes()
        for records in ([], [sample("self-test", "self_test")],
                        [sample("failed", execution={"status": "adapter_error"})]):
            with self.subTest(records=len(records)):
                self.source(records)
                with self.assertRaisesRegex(ValueError, "No eligible Direct Model or Pi Agent records"):
                    self.run_release()
                self.assertEqual(self.release_files(), before)
                self.assertEqual(self.audit_path.read_bytes(), audit_before)

    def test_repeat_history_and_immutable_snapshot_collision(self):
        self.source([sample("one")])
        first = self.run_release()["snapshot_id"]
        next_day = self.generation.replace(day=24)
        self.assertEqual(self.run_release(next_day)["snapshot_id"], first)
        self.source([sample("two")])
        second = self.run_release(next_day)["snapshot_id"]
        data = self.out / "data"
        catalog = json.loads((data / "catalog.json").read_bytes())
        self.assertEqual(catalog["latest_snapshot_id"], second)
        self.assertEqual([entry["snapshot_id"] for entry in catalog["snapshots"]], [second, first])
        snapshot_file = data / "snapshots" / first / "benchmark.json"
        snapshot_file.write_bytes(b"changed")
        self.source([sample("one")])
        with self.assertRaisesRegex(ValueError, "differs"):
            self.run_release()
        self.assertEqual(snapshot_file.read_bytes(), b"changed")
        self.assertEqual((data / "catalog.json").read_bytes(), json.dumps(catalog, indent=2, sort_keys=True).encode() + b"\n")

    def test_reused_snapshot_rejects_corrupt_manifest_metadata(self):
        self.source([sample("one")])
        first = self.run_release()["snapshot_id"]
        self.source([sample("two")])
        self.run_release(self.generation.replace(day=24))
        manifest_path = self.out / "data" / "snapshots" / first / "manifest.json"
        original = json.loads(manifest_path.read_bytes())
        self.source([sample("one")])
        for field, value in {
            "task_coverage": [], "verifier_coverage": [], "track_distribution": {"pi_agent": 1},
            "record_count": 2, "snapshot_id": "2026-11-23-abcdef123456", "data_sha256": "d" * 64,
            "generated_at_utc": "2026-11-23T01:00:00Z",
        }.items():
            with self.subTest(field=field):
                manifest_path.write_text(json.dumps({**original, field: value}), encoding="utf-8")
                before = self.release_files()
                message = "manifest and catalog disagree" if field == "generated_at_utc" else f"invalid manifest {field}"
                with self.assertRaisesRegex(ValueError, message):
                    self.run_release(self.generation.replace(day=25))
                self.assertEqual(self.release_files(), before)

    def test_reused_snapshot_preserves_original_source_digest(self):
        self.source([sample("one")])
        first = self.run_release()
        before = self.release_files()
        self.source([sample("one"), sample("new-self-test", "self_test")])
        second = self.run_release(self.generation.replace(day=24))
        self.assertEqual(second["snapshot_id"], first["snapshot_id"])
        self.assertNotEqual(second["source_registry_sha256"], first["source_registry_sha256"])
        self.assertEqual(self.release_files(), before)

    def test_public_execution_eligibility(self):
        self.source([sample(status, execution={"status": status}) for status in
                     ("completed", "incomplete", "timeout", "output_limit", "adapter_error", "future_status")]
                    + [sample("self-test", "self_test", execution={"status": "adapter_error"})])
        audit = self.run_release()
        records = json.loads((self.out / "data" / "latest.json").read_bytes())["records"]
        self.assertEqual({r["execution"]["status"] for r in records}, ELIGIBLE_STATUSES)
        self.assertEqual(audit["excluded_status_distribution"], {"adapter_error": 1, "future_status": 1})
        self.assertEqual(audit["excluded_track_distribution"], {"self_test": 1})

    def test_hardware_overlay_fills_only_missing_fields(self):
        self.source([sample("one", hardware={"gpu": "RTX 4070", "source": "declared"}), sample("two")])
        before = self.registry.read_bytes()
        baseline = self.run_release()
        original = {r["run_id"]: r for r in json.loads((self.out / "data" / "latest.json").read_bytes())["records"]}
        overlay = self.overlay({"one": {"gpu": "RTX 4070", "cpu": "Intel Core i7-13700KF", "ram_gb": 32}})
        overlay_before = overlay.read_bytes()
        audit = self.run_release(hardware_overlay=overlay)
        records = json.loads((self.out / "data" / "latest.json").read_bytes())["records"]
        self.assertNotEqual(audit["snapshot_id"], baseline["snapshot_id"])
        self.assertEqual(records[0]["hardware"], {"gpu": "RTX 4070", "cpu": "Intel Core i7-13700KF",
                         "ram_gb": 32, "vram_gb": None, "memory_type": None, "source": "declared",
                         "operator_confirmed_fields": ["cpu", "ram_gb"]})
        self.assertEqual(records[1], original["two"])
        self.assertEqual({k: v for k, v in records[0].items() if k != "hardware"},
                         {k: v for k, v in original["one"].items() if k != "hardware"})
        self.assertEqual(audit["operator_confirmed_hardware_fields"], {"one": ["cpu", "ram_gb"]})
        self.assertEqual(audit["hardware_overlay_sha256"], hashlib.sha256(overlay_before).hexdigest())
        self.assertEqual(self.registry.read_bytes(), before)
        self.assertEqual(overlay.read_bytes(), overlay_before)

    def test_hardware_overlay_rejects_conflicts_and_invalid_mapping(self):
        self.source([sample("one", hardware={"gpu": "RTX 4070", "ram_gb": 32}),
                     sample("failed", execution={"status": "adapter_error"})])
        self.run_release()
        before = self.release_files()
        audit_before = self.audit_path.read_bytes()
        cases = [({"one": {"ram_gb": 64}}, None, "overlay conflict"),
                 ({"unknown": {"ram_gb": 32}}, None, "unknown or ineligible"),
                 ({"failed": {"ram_gb": 32}}, None, "unknown or ineligible"),
                 ({"one": {"host": "machine"}}, None, "Invalid hardware overlay fields"),
                 ({"one": {"cpu": None}}, None, "Invalid hardware overlay value"),
                 ({"one": {"ram_gb": True}}, None, "Invalid hardware overlay value"),
                 ({"one": {"ram_gb": 32}}, "0" * 64, "hash mismatch")]
        for mapping, digest, error in cases:
            with self.subTest(error=error):
                overlay = self.overlay(mapping, digest)
                with self.assertRaisesRegex(ValueError, error):
                    self.run_release(hardware_overlay=overlay)
                self.assertEqual(self.release_files(), before)
                self.assertEqual(self.audit_path.read_bytes(), audit_before)

    def test_overlay_privacy_failure_preserves_release(self):
        self.source([sample("one")])
        self.run_release()
        before = self.release_files()
        overlay = self.overlay({"one": {"cpu": "person@example.com"}})
        with self.assertRaisesRegex(ValueError, "Privacy audit failed"):
            self.run_release(hardware_overlay=overlay)
        self.assertEqual(self.release_files(), before)
        audit = json.loads(self.audit_path.read_bytes())
        self.assertEqual(audit["privacy_violations"], [
            {"field": "hardware.cpu", "reason": "Possible private value", "record_index": 1}])
        self.assertNotIn(b"person@example.com", self.audit_path.read_bytes())

    @unittest.skipUnless(os.environ.get("REPLAYBENCH_ACCEPTANCE_EXPORT"), "Set REPLAYBENCH_ACCEPTANCE_EXPORT to run")
    def test_frozen_acceptance_export(self):
        self.registry = Path(os.environ["REPLAYBENCH_ACCEPTANCE_EXPORT"])
        raw = self.registry.read_bytes()
        source = json.loads(raw)
        audit = self.run_release()
        data = self.out / "data"
        latest = (data / "latest.json").read_bytes()
        records = json.loads(latest)["records"]
        expected = {r["run_id"]: r for r in source["records"] if r["track"] in ("direct_model", "pi_agent")
                    and r["execution"]["status"] in ELIGIBLE_STATUSES}
        self.assertEqual(set(expected), {r["run_id"] for r in records})
        self.assertEqual(audit["input_record_count"], 61)
        self.assertEqual(audit["excluded_invalid_archive_count"], 1)
        self.assertEqual(audit["excluded_track_distribution"], {"self_test": 16})
        self.assertEqual(audit["excluded_status_distribution"], {"adapter_error": 5})
        self.assertEqual(Counter(r["track"] for r in records), {"direct_model": 33, "pi_agent": 7})
        self.assertEqual(Counter(r["execution"]["status"] for r in records),
                         {"completed": 30, "incomplete": 4, "output_limit": 3, "timeout": 3})
        scores = [r["result"]["score"] for r in records]
        self.assertEqual((len(scores) - scores.count(None), scores.count(None), scores.count(0)), (30, 10, 4))
        self.assertEqual(Counter(r["result"]["strict_pass"] for r in records), {True: 5, False: 25, None: 10})
        for run in records:
            original = expected[run["run_id"]]
            self.assertEqual(run["result"]["score"], original["result"]["score"])
            self.assertEqual(run["result"]["strict_pass"], original["result"]["strict_pass"])
            self.assertEqual(run["execution"]["status"], original["execution"]["status"])
        self.assertEqual(sum(r["task"]["candidate"] for r in records), 18)
        self.assertEqual(sum("subject_model_version_mismatch" in r["metadata_flags"] for r in records), 0)
        self.assertEqual(self.registry.read_bytes(), raw)
        self.assertEqual(audit["public_data_sha256"], hashlib.sha256(latest).hexdigest())
        overlay_path = os.environ.get("REPLAYBENCH_ACCEPTANCE_HARDWARE_OVERLAY")
        if overlay_path:
            enriched = self.run_release(hardware_overlay=Path(overlay_path))
            revised = json.loads((data / "latest.json").read_bytes())["records"]
            self.assertEqual(Counter(r["hardware"]["cpu"] for r in revised),
                             {"Intel Core i7-13700KF": 38, "Intel Core i5-12400": 2})
            self.assertEqual(Counter((r["hardware"]["ram_gb"], r["hardware"]["memory_type"]) for r in revised),
                             {(32, "DDR5"): 38, (64, "DDR4"): 2})
            self.assertEqual({(r["hardware"]["gpu"], r["hardware"]["vram_gb"]) for r in revised},
                             {("RTX 4070", 12)})
            self.assertEqual([{k: v for k, v in r.items() if k != "hardware"} for r in revised],
                             [{k: v for k, v in r.items() if k != "hardware"} for r in records])
            self.assertEqual(enriched["privacy_violations"], [])
            self.assertEqual(len(enriched["operator_confirmed_hardware_fields"]), 40)
            self.assertEqual(self.registry.read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
