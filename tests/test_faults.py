"""Fault injection coverage, business invariants and byte compatibility."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from booking_simulator.cli import generate, save
from booking_simulator.faults import FAULTS, configuration, inject


class FaultTests(unittest.TestCase):
    def test_each_fault_and_originals(self):
        """Each rate-one fault changes its field and retains an exact original."""
        events, _ = generate(42, 100)
        original = copy.deepcopy(events)
        for fault in FAULTS:
            mutated, truth = inject(events, 42, configuration({fault: 1}))
            self.assertEqual(len(truth), len(events))
            for entry in truth:
                event = mutated[entry['line'] - 1]
                self.assertEqual(entry['faults'], [fault])
                if fault == 'missing_correlation':
                    self.assertNotIn('trace_id', event)
                elif fault == 'malformed_envelope':
                    self.assertEqual(event['attributes'], [])
                else:
                    self.assertGreater(event['observed_at'], entry['original']['observed_at'])
                    self.assertEqual(event['occurred_at'], entry['original']['occurred_at'])
        self.assertEqual(events, original)

    def test_determinism_independence_and_duplicates(self):
        """Rates use independent deterministic selection and preserve duplicate identity."""
        events, _ = generate(42, 100)
        config = configuration({name: 0.4 for name in FAULTS})
        first = inject(events, 42, config)
        self.assertEqual(first, inject(events, 42, config))
        self.assertNotEqual(first, inject(events, 43, config))
        missing_only = inject(events, 42, configuration({'missing_correlation': 0.4}))[1]
        selected = {r['event_id'] for r in missing_only}
        self.assertEqual(selected, {r['event_id'] for r in first[1] if 'missing_correlation' in r['faults']})
        self.assertGreater(len(selected), 0)
        self.assertLess(len(selected), len(events))
        by_id = {}
        for event in first[0]:
            flags = ('trace_id' not in event, event['attributes'] == [])
            self.assertEqual(by_id.setdefault(event['event_id'], flags), flags)
        times = [e['observed_at'] for e in first[0]]
        self.assertEqual(times, sorted(times))
        occurred = [e['occurred_at'] for e in first[0]]
        self.assertNotEqual(occurred, sorted(occurred))

    def test_export_reproduction_and_business_truth(self):
        """Opt-in files are reproducible, separated, identified and removable."""
        with tempfile.TemporaryDirectory() as root:
            a, b, clean = (Path(root) / name for name in ('a', 'b', 'clean'))
            rates = {name: 0.5 for name in FAULTS}
            save(clean, 42, 50)
            save(a, 42, 50, incidents=True, fault_rates=rates)
            save(b, 42, 50, incidents=True, fault_rates=rates)
            for path in a.rglob('*'):
                if path.is_file():
                    self.assertEqual(path.read_bytes(), (b / path.relative_to(a)).read_bytes())
            self.assertEqual((a / 'reference/truth.jsonl').read_bytes(), (clean / 'reference/truth.jsonl').read_bytes())
            student = '\n'.join(p.read_text() for p in (a / 'dataset').iterdir())
            self.assertNotIn('original_trace_id', student)
            self.assertNotIn('"original"', student)
            self.assertFalse((a / 'dataset/data-quality-truth.jsonl').exists())
            metadata = json.loads((a / 'reference/generation.json').read_text())
            self.assertEqual(metadata['data_quality']['rates'], rates)
            corrupted_id = json.loads((a / 'dataset/manifest.json').read_text())['dataset_id']
            save(a, 42, 50)
            self.assertFalse((a / 'reference/data-quality-truth.jsonl').exists())
            self.assertNotEqual(corrupted_id, json.loads((a / 'dataset/manifest.json').read_text())['dataset_id'])

    def test_zero_rates_preserve_v1_bytes(self):
        """Disabled faults preserve existing output bytes and RNG choices."""
        with tempfile.TemporaryDirectory() as root:
            a, b = Path(root) / 'a', Path(root) / 'b'
            save(a, 42, 25)
            save(b, 42, 25, fault_rates={name: 0 for name in FAULTS})
            for path in a.rglob('*'):
                if path.is_file():
                    self.assertEqual(path.read_bytes(), (b / path.relative_to(a)).read_bytes())
            events = (a / 'dataset/events.jsonl').read_bytes()
            # Frozen hash of the v1 generator before fault support.
            self.assertEqual(hashlib.sha256(events).hexdigest(), '8dc19ddc990f58538ed2885c253721553943e4f50d2d5603ce3fe4e73c23e0d4')

    def test_invalid_configuration_and_cli(self):
        """Reject invalid configuration without creating partial output."""
        for rates in ({'unknown': 1}, {'late_delivery': -1}, {'late_delivery': 1.1},
                      {'late_delivery': float('nan')}, {'late_delivery': float('inf')},
                      {'late_delivery': True}, {'late_delivery': '0.1'}, []):
            with self.subTest(rates=rates), self.assertRaises(ValueError):
                configuration(rates)
        for seconds in (0, -1, 1.5, True):
            with self.assertRaises(ValueError):
                configuration({}, seconds)
        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / 'output'
            result = subprocess.run([sys.executable, '-m', 'booking_simulator', '--output', str(output),
                                     '--late-delivery-rate', 'nan'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(output.exists())
            self.assertNotIn('Traceback', result.stderr)
