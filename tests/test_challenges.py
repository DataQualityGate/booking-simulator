"""Public challenges reproduce the shipped baseline without solving the tasks."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from booking_simulator.challenges import challenges, get_challenge
from booking_simulator.cli import generate
from booking_simulator.incidents import SERVICES, _labels


class ChallengeTests(unittest.TestCase):
    def test_catalog_and_baselines(self):
        catalog = challenges()
        self.assertEqual(len(catalog), 2)
        self.assertEqual(len({c['challenge_id'] for c in catalog}), 2)
        for challenge in catalog:
            self.assertEqual(challenge['schema_version'], '1.0')
            for name in ('baseline', 'requested_change', 'target', 'fixture_contract', 'impact_rationale'):
                self.assertTrue(challenge[name])
            _labels(challenge['impact'], set(SERVICES), reference=True)
            self.assertTrue(challenge['post_change_fixtures'])
            self.assertTrue(challenge['regression_fixtures'])
            for fixture in challenge['baseline_fixtures'] + challenge['regression_fixtures']:
                events, truth = generate(fixture['input']['seed'], fixture['input']['count'])
                self.assertEqual([e['event_type'] for e in events], fixture['expected']['event_types'])
                self.assertEqual(truth[0], fixture['expected']['truth'])

    def test_indirect_impact_and_changed_outcome(self):
        challenge = get_challenge('supplier-recovery-v1')
        self.assertIn('notification', challenge['impact']['affected_services'])
        before = challenge['baseline_fixtures'][0]['expected']
        after = challenge['post_change_fixtures'][0]['expected']
        self.assertEqual(before['truth']['status'], 'pending')
        self.assertEqual(after['truth']['status'], 'confirmed')
        self.assertNotIn('NotificationSent', before['event_types'])
        self.assertIn('NotificationSent', after['event_types'])

    def test_fresh_manifests(self):
        first = get_challenge('supplier-recovery-v1')
        first['baseline_fixtures'].clear()
        self.assertTrue(get_challenge('supplier-recovery-v1')['baseline_fixtures'])
        with self.assertRaises(ValueError):
            get_challenge('../../intent.md')

    def test_cli_export_and_errors(self):
        command = [sys.executable, '-m', 'booking_simulator.challenges']
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [c['challenge_id'] for c in challenges()])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'challenge.json'
            args = command + ['--challenge', 'supplier-recovery-v1', '--output', str(output)]
            self.assertEqual(subprocess.run(args, capture_output=True).returncode, 0)
            original = output.read_bytes()
            self.assertEqual(subprocess.run(args, capture_output=True).returncode, 2)
            self.assertEqual(output.read_bytes(), original)
        for args in (['--challenge', 'unknown'], ['--output', 'unused.json']):
            self.assertEqual(subprocess.run(command + args, capture_output=True).returncode, 2)
