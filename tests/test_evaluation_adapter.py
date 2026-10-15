"""Local evaluator handoff tests; all reference fixtures are public synthetic data."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from booking_simulator.cli import save
from booking_simulator.evaluation_adapter import prepare_evaluation, write_request

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'examples/evaluation'
SUBMISSION = ROOT / 'examples/predictions/submission.jsonl'


class AdapterTests(unittest.TestCase):
    def setUp(self):
        """Copy public inputs so invalid-input tests cannot mutate tracked fixtures."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(FIXTURE, self.root / 'fixture')
        self.dataset = self.root / 'fixture/dataset'
        self.reference = self.root / 'fixture/reference'
        self.predictions = self.root / 'submission.jsonl'
        shutil.copy(SUBMISSION, self.predictions)

    def request(self):
        """Prepare a request from the isolated public fixture."""
        return prepare_evaluation(self.dataset, self.reference, self.predictions)

    def test_public_fixture_and_normalization(self):
        """Pin the complete wire contract, stable provenance and sorted service sets."""
        self.assertEqual(self.request(), json.loads((FIXTURE / 'request.json').read_text()))
        lines = self.predictions.read_text().splitlines()
        self.predictions.write_text('\n'.join(reversed(lines)) + '\n')
        request = self.request()
        self.assertEqual(request['records'], json.loads((FIXTURE / 'request.json').read_text())['records'])
        self.assertNotEqual(request['input_sha256']['predictions'], json.loads((FIXTURE / 'request.json').read_text())['input_sha256']['predictions'])
        self.assertNotIn('scenario', json.dumps(request))
        self.assertEqual(request['records'][1]['expected']['affected_services'], ['booking', 'payment'])

    def test_invalid_manifest_and_paths(self):
        """Reject unsupported metadata, count mismatches and path escapes."""
        path = self.dataset / 'manifest.json'
        original = json.loads(path.read_text())
        for changes in ({'schema_version': '2.0'}, {'dataset_id': ''}, {'booking_count': True},
                        {'booking_count': 4}, {'events_path': '../reference/truth.jsonl'},
                        {'events_path': str(self.predictions)}, {'events_path': None}):
            path.write_text(json.dumps({**original, **changes}))
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.request()
        path.write_text(json.dumps(original))
        event_link = self.dataset / 'outside.jsonl'
        event_link.symlink_to(self.predictions)
        path.write_text(json.dumps({**original, 'events_path': event_link.name}))
        with self.assertRaises(ValueError):
            self.request()

    def test_invalid_submissions_and_references(self):
        """Never pass malformed, incomplete or duplicate rows to a grader."""
        for invalid in ('{}\n', self.predictions.read_text() * 2, ''):
            self.predictions.write_text(invalid)
            with self.assertRaises(ValueError):
                self.request()
        shutil.copy(SUBMISSION, self.predictions)
        truth_path = self.reference / 'truth.jsonl'
        original = truth_path.read_text()
        for text in ('{}\n', original * 2, '', '[]\n', original.replace('"pending"', '"unknown"')):
            truth_path.write_text(text)
            with self.subTest(text=text[:40]), self.assertRaises(ValueError):
                self.request()

    def test_output_and_reference_separation(self):
        """Block public answer exports, symlink escapes and overwriting any file."""
        with self.assertRaises(ValueError):
            write_request(self.dataset, self.reference, self.predictions, self.dataset / 'answers.json')
        public_link = self.root / 'public-link'
        public_link.symlink_to(self.dataset, target_is_directory=True)
        with self.assertRaises(ValueError):
            write_request(self.dataset, self.reference, self.predictions, public_link / 'answers.json')
        with self.assertRaises(ValueError):
            write_request(self.dataset, self.reference, self.predictions, self.predictions)
        output = self.root / 'private/request.json'
        write_request(self.dataset, self.reference, self.predictions, output)
        before = output.read_bytes()
        with self.assertRaises(FileExistsError):
            write_request(self.dataset, self.reference, self.predictions, output)
        self.assertEqual(output.read_bytes(), before)
        shutil.copy(self.reference / 'truth.jsonl', self.dataset / 'truth.jsonl')
        with self.assertRaises(ValueError):
            prepare_evaluation(self.dataset, self.dataset, self.predictions)

    def test_generated_dataset_and_cli(self):
        """Package a real generated dataset without importing a grader or executing code."""
        run = self.root / 'generated'
        save(run, 42, 25, incidents=True)
        truth = [json.loads(line) for line in (run / 'reference/truth.jsonl').read_text().splitlines()]
        # Instructor-side smoke fixture only, not an inference implementation.
        predictions = [{key: row[key] for key in ('booking_id', 'status', 'root_cause_service', 'affected_services')}
                       for row in truth]
        self.predictions.write_text(''.join(json.dumps({'schema_version': '1.0', **row}) + '\n' for row in predictions))
        output = self.root / 'private.json'
        command = [sys.executable, '-m', 'booking_simulator.evaluation_adapter',
                   '--dataset', str(run / 'dataset'), '--reference', str(run / 'reference'),
                   '--predictions', str(self.predictions), '--output', str(output)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(output.read_text())['records']), 25)
        again = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(again.returncode, 2)
        self.assertNotIn('Traceback', again.stderr)
