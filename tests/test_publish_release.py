from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from tools.publish_release import publish


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

    def run_release(self, day=None):
        return publish(self.registry, self.out, self.audit_path, day or self.generation)

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
        for text in (r"C:\Users\private\archive", "192.168.1.20", "Bearer private-credential",
                     "person@example.com", "sk-fakecredential12345", "/home/private/run"):
            with self.subTest(text=text):
                self.source([sample("bad", model={"declared": text})])
                with self.assertRaisesRegex(ValueError, "Privacy audit failed"):
                    self.run_release()
                audit = json.loads(self.audit_path.read_bytes())
                self.assertEqual(audit["published_record_count"], 0)
                self.assertIsNone(audit["public_data_sha256"])
                self.assertEqual(audit["privacy_violations"][0]["field"], "model.declared")
                self.assertNotIn(text, self.audit_path.read_text(encoding="utf-8"))
                self.assertEqual((data / "latest.json").read_bytes(), before)
        self.assertEqual(len(list((data / "snapshots").iterdir())), 1)

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

    @unittest.skipUnless(os.environ.get("REPLAYBENCH_ACCEPTANCE_EXPORT"), "Set REPLAYBENCH_ACCEPTANCE_EXPORT to run")
    def test_frozen_acceptance_export(self):
        self.registry = Path(os.environ["REPLAYBENCH_ACCEPTANCE_EXPORT"])
        raw = self.registry.read_bytes()
        source = json.loads(raw)
        audit = self.run_release()
        data = self.out / "data"
        latest = (data / "latest.json").read_bytes()
        records = json.loads(latest)["records"]
        expected = {r["run_id"]: r for r in source["records"] if r["track"] in ("direct_model", "pi_agent")}
        self.assertEqual(set(expected), {r["run_id"] for r in records})
        self.assertEqual(audit["input_record_count"], 61)
        self.assertEqual(audit["excluded_invalid_archive_count"], 1)
        self.assertEqual(audit["excluded_track_distribution"], {"self_test": 16})
        self.assertEqual(Counter(r["track"] for r in records), {"direct_model": 38, "pi_agent": 7})
        self.assertEqual(Counter(r["execution"]["status"] for r in records),
                         {"completed": 30, "adapter_error": 5, "incomplete": 4, "output_limit": 3, "timeout": 3})
        for run in records:
            original = expected[run["run_id"]]
            self.assertEqual(run["result"]["score"], original["result"]["score"])
            self.assertEqual(run["result"]["strict_pass"], original["result"]["strict_pass"])
            self.assertEqual(run["execution"]["status"], original["execution"]["status"])
        self.assertEqual(sum(r["task"]["candidate"] for r in records), 18)
        self.assertEqual(sum("subject_model_version_mismatch" in r["metadata_flags"] for r in records), 1)
        self.assertEqual(self.registry.read_bytes(), raw)
        self.assertEqual(audit["public_data_sha256"], hashlib.sha256(latest).hexdigest())


if __name__ == "__main__":
    unittest.main()
