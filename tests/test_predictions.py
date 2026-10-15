"""Public prediction contract validation and CLI regression tests."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from booking_simulator.cli import generate
from booking_simulator.predictions import (
    FIELDS, SERVICES, STATUSES, VERSION, booking_ids_from_events, validate_predictions,
)

ROOT = Path(__file__).resolve().parents[1]


def prediction(**updates):
    """Build a structurally valid prediction independent of generator answers."""
    return {"schema_version": "1.0", "booking_id": "BOOK-000001", "status": "confirmed",
            "root_cause_service": None, "affected_services": [], **updates}


class PredictionTests(unittest.TestCase):
    def test_public_examples_and_coverage(self):
        """Validate the public fixture without instructor truth or grading code."""
        examples = ROOT / 'examples/predictions'
        ids = booking_ids_from_events((examples / 'events.jsonl').read_text())
        report = validate_predictions((examples / 'submission.jsonl').read_text(), booking_ids=ids)
        self.assertTrue(report['valid'])
        self.assertEqual(report['row_count'], 3)
        self.assertEqual(report['errors'], [])

    def test_shape_vocabulary_and_types(self):
        """Reject wrong types, versions, names and ambiguous service lists."""
        invalid = [None, [], 7, 'text']
        for field, values in {
            'schema_version': ['2.0', 1, None],
            'booking_id': ['BOOK-1', 'BOOK-000001\n', 'BOOK-１２３４５６', None, 1],
            'status': ['success', None, [], {}],
            'root_cause_service': ['unknown', [], {}, False],
            'affected_services': ['booking', None, [None], [{}], ['ghost'], ['booking', 'booking']],
        }.items():
            invalid.extend(prediction(**{field: value}) for value in values)
        missing = prediction()
        del missing['status']
        invalid += [missing, prediction(extra='unexpected')]
        for row in invalid:
            with self.subTest(row=row):
                self.assertFalse(validate_predictions(json.dumps(row))['valid'])
        for status in STATUSES:
            for root in (None, *SERVICES):
                self.assertTrue(validate_predictions(json.dumps(prediction(status=status, root_cause_service=root)))['valid'])

    def test_json_errors_and_physical_line_numbers(self):
        """Reject invalid JSON, duplicate keys and nonstandard constants reliably."""
        for bad in ['{', '{"booking_id":"a","booking_id":"b"}', 'NaN', 'Infinity']:
            report = validate_predictions('\n' + bad + '\n' + json.dumps(prediction()))
            self.assertFalse(report['valid'])
            self.assertEqual(report['row_count'], 2)
            self.assertEqual(report['errors'][0]['line'], 2)
            self.assertEqual(report['errors'][0]['code'], 'invalid_json')
        self.assertEqual(validate_predictions('  \n')['errors'][0]['code'], 'empty_submission')

    def test_duplicates_unknown_and_missing_bookings(self):
        """Check exact ID coverage while tolerating repeated event deliveries."""
        row = json.dumps(prediction())
        report = validate_predictions(row + '\n' + row, booking_ids={'BOOK-000002'})
        self.assertEqual([e['code'] for e in report['errors']],
                         ['unknown_booking', 'duplicate_booking', 'unknown_booking', 'missing_booking'])
        ids = booking_ids_from_events(row + '\n' + row)
        self.assertEqual(ids, {'BOOK-000001'})
        self.assertTrue(validate_predictions(row, booking_ids=ids)['valid'])
        self.assertFalse(validate_predictions(row, booking_ids=set())['valid'])

    def test_event_input_errors(self):
        """Fail clearly when coverage cannot be established from student input."""
        for text in ['', '\n', '{', '[]', '{}', '{"booking_id":"wrong"}']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                booking_ids_from_events(text)

    def test_excessive_json_nesting(self):
        """Convert parser recursion failures to documented diagnostics and exit codes."""
        depth = max(10000, sys.getrecursionlimit() + 100)
        nested = '[' * depth + '0' + ']' * depth
        report = validate_predictions(nested)
        self.assertEqual(report['errors'][0]['code'], 'invalid_json')
        self.assertFalse(report['valid'])
        with self.assertRaisesRegex(ValueError, 'nesting'):
            booking_ids_from_events(nested)
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'nested.jsonl'
            path.write_text(nested, encoding='utf-8')
            command = [sys.executable, '-m', 'booking_simulator.predictions',
                       '--predictions', str(path)]
            invalid = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(invalid.returncode, 1)
            self.assertEqual(json.loads(invalid.stdout)['errors'][0]['code'], 'invalid_json')
            bad_events = subprocess.run(command + ['--events', str(path)], capture_output=True, text=True)
            self.assertEqual(bad_events.returncode, 2)
            self.assertIn('nesting', bad_events.stderr)
            self.assertNotIn('Traceback', bad_events.stderr)

    def test_schema_and_validator_vocabulary(self):
        """Keep the published schema aligned with the dependency-free validator."""
        schema = json.loads((ROOT / 'schemas/booking-prediction-v1.schema.json').read_text())
        self.assertEqual(set(schema['required']), FIELDS)
        self.assertEqual(set(schema['properties']), FIELDS)
        self.assertFalse(schema['additionalProperties'])
        props = schema['properties']
        self.assertEqual(props['schema_version']['const'], VERSION)
        self.assertEqual(props['status']['enum'], list(STATUSES))
        self.assertEqual(props['root_cause_service']['enum'], [None, *SERVICES])
        self.assertEqual(props['affected_services']['items']['enum'], list(SERVICES))
        self.assertTrue(props['affected_services']['uniqueItems'])

    def test_generated_predictions_and_cli_exit_codes(self):
        """Exercise generated ID coverage and distinguish invalid rows from input errors."""
        events, truth = generate(42, 30)
        # Use only public IDs; these arbitrary predictions are not a student solution.
        rows = [prediction(booking_id=row['booking_id']) for row in truth]
        text = '\n'.join(json.dumps(row) for row in rows)
        ids = booking_ids_from_events('\n'.join(json.dumps(row) for row in events))
        self.assertTrue(validate_predictions(text, booking_ids=ids)['valid'])
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'submission.jsonl'
            command = [sys.executable, '-m', 'booking_simulator.predictions', '--predictions', str(path)]
            path.write_text(text, encoding='utf-8')
            valid = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(valid.returncode, 0)
            self.assertTrue(json.loads(valid.stdout)['valid'])
            path.write_text('{}', encoding='utf-8')
            invalid = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(invalid.returncode, 1)
            self.assertFalse(json.loads(invalid.stdout)['valid'])
            path.unlink()
            missing = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(missing.returncode, 2)
            self.assertNotIn('Traceback', missing.stderr)
