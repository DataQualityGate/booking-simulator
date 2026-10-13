import json
import tempfile
import unittest
from pathlib import Path
from booking_simulator.cli import generate, save

class SimulatorTests(unittest.TestCase):
    def test_seed_is_deterministic(self):
        self.assertEqual(generate(42, 100), generate(42, 100))
        self.assertNotEqual(generate(42, 100), generate(43, 100))

    def test_event_integrity_and_truth(self):
        events, truth = generate(42, 1000)
        self.assertEqual(len(truth), 1000)
        self.assertEqual(
            {row["scenario"] for row in truth},
            {"success", "payment_failed", "supplier_timeout", "message_delay"},
        )
        self.assertEqual(events, sorted(events, key=lambda e: (e["observed_at"], e["event_id"])))
        self.assertEqual({e["booking_id"] for e in events}, {t["booking_id"] for t in truth})
        self.assertTrue(all(e["attributes"]["synthetic"] for e in events))
        self.assertEqual(
            sum(t["status"] == "pending" for t in truth),
            sum(t["scenario"] == "supplier_timeout" for t in truth),
        )

    def test_byte_reproducible_and_separated(self):
        with tempfile.TemporaryDirectory() as root:
            a, b = Path(root) / "a", Path(root) / "b"
            save(a, 42, 25)
            save(b, 42, 25)
            for name in [
                "dataset/events.jsonl", "dataset/topology.json",
                "dataset/manifest.json", "reference/truth.jsonl",
            ]:
                self.assertEqual((a / name).read_bytes(), (b / name).read_bytes())
            manifest = json.loads((a / "dataset/manifest.json").read_text())
            self.assertNotIn("truth", manifest)
            self.assertFalse((a / "dataset/truth.jsonl").exists())

if __name__ == "__main__":
    unittest.main()
