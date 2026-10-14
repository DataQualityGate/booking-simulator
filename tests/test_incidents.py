import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from booking_simulator.cli import save
from booking_simulator.incidents import SERVICES, TOPOLOGY, evaluate, exercises


class IncidentTests(unittest.TestCase):
    def test_reference_partitions_and_topology(self):
        cases, answers = exercises()
        self.assertEqual(len(cases), 6)
        self.assertEqual({c['kind'] for c in cases}, {'service_failure', 'api_change', 'schema_change'})
        self.assertEqual({c['case_id'] for c in cases}, {a['case_id'] for a in answers})
        for answer in answers:
            groups = [answer[key] for key in ('affected_services', 'possibly_affected_services', 'unaffected_services')]
            self.assertEqual(sorted(sum(groups, [])), sorted(SERVICES))
        for edge in TOPOLOGY['dependencies']:
            self.assertIn(edge['from'], SERVICES)
            self.assertIn(edge['to'], SERVICES)
        self.assertEqual({e['mode'] for e in TOPOLOGY['dependencies']}, {'required', 'optional', 'unknown'})

    def test_explicit_scenarios(self):
        _, answers = exercises()
        answers = {a['case_id']: a for a in answers}
        self.assertEqual(answers['notification-outage']['affected_services'], ['notification'])
        self.assertEqual(answers['confirmation-schema-break']['affected_services'], ['notification'])
        self.assertEqual(answers['confirmation-schema-add']['affected_services'], [])
        self.assertIn('supplier', answers['payment-outage']['unaffected_services'])
        self.assertIn('audit', answers['supplier-outage']['possibly_affected_services'])
        self.assertIn('analytics', answers['supplier-outage']['unaffected_services'])
        self.assertNotIn('payment', answers['payment-api-break']['affected_services'])

    def test_exact_scoring_and_missing_cases(self):
        _, truth = exercises()
        result = evaluate(truth, truth)
        self.assertEqual((result['correct'], result['total']), (36, 36))
        self.assertEqual(result['false_positives'], 0)
        empty = evaluate([], truth)
        self.assertEqual(empty['false_positives'], 0)
        self.assertEqual(empty['false_negatives'], 15)
        self.assertLess(empty['correct'], empty['total'])

    def test_false_positives_and_uncertainty(self):
        _, truth = exercises()
        predictions = copy.deepcopy(truth)
        outage = predictions[0]
        outage['affected_services'].append('analytics')
        outage['possibly_affected_services'].remove('audit')
        outage['affected_services'].append('audit')
        outage['affected_services'].remove('booking')
        outage['possibly_affected_services'].append('booking')
        predictions[2]['possibly_affected_services'].append('supplier')
        result = evaluate(predictions, truth)
        self.assertEqual(result['false_positives'], 2)
        self.assertEqual(result['overconfident'], 1)
        self.assertEqual(result['underconfident'], 1)
        self.assertEqual(result['correct'], 32)

    def test_invalid_submissions(self):
        _, truth = exercises()
        bad_rows = [
            [truth[0], truth[0]],
            [{'case_id': 'unknown', 'affected_services': [], 'possibly_affected_services': []}],
        ]
        for field, value in [('affected_services', ['ghost']),
                             ('affected_services', ['payment', 'payment']),
                             ('possibly_affected_services', ['payment']),
                             ('affected_services', 'payment')]:
            row = copy.deepcopy(truth[0])
            row[field] = value
            bad_rows.append([row])
        for rows in bad_rows:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                evaluate(rows, truth)
        with self.assertRaises(ValueError):
            evaluate([], [])

    def test_export_reproducibility_separation_and_cli(self):
        with tempfile.TemporaryDirectory() as root:
            a, b = Path(root) / 'a', Path(root) / 'b'
            save(a, 42, 5, incidents=True)
            save(b, 42, 5, incidents=True)
            for file in a.rglob('*'):
                if file.is_file():
                    self.assertEqual(file.read_bytes(), (b / file.relative_to(a)).read_bytes())
            for file in (a / 'dataset').iterdir():
                self.assertNotIn('affected_services', file.read_text())
                self.assertNotIn('impact-truth', file.read_text())
            manifest = json.loads((a / 'dataset/manifest.json').read_text())
            self.assertTrue((a / 'dataset' / manifest['incidents_path']).exists())
            truth_file = a / 'reference/impact-truth.jsonl'
            result = subprocess.run([sys.executable, '-m', 'booking_simulator.incidents',
                                     '--predictions', str(truth_file), '--truth', str(truth_file)],
                                    capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(result.stdout)['correct'], 36)
            save(a, 42, 5)
            self.assertFalse((a / 'dataset/incidents.jsonl').exists())
            self.assertFalse(truth_file.exists())
            self.assertNotIn('incidents_path', json.loads((a / 'dataset/manifest.json').read_text()))
