import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from booking_simulator.combined_evaluation import prepare_combined, write_combined
from booking_simulator.smoke import run_smoke

ROOT = Path(__file__).resolve().parent.parent


class CombinedTests(unittest.TestCase):
    def setUp(self):
        """Create independent public inputs and separate instructor reference files."""
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / 'examples/combined', self.root / 'submission')
        shutil.copytree(ROOT / 'examples/evaluation/dataset', self.root / 'dataset')
        shutil.copytree(ROOT / 'examples/evaluation/reference', self.root / 'reference')
        # The legacy public reference contains booking truth only; add the existing incident suite.
        from booking_simulator.incidents import exercises
        _, truth = exercises()
        (self.root / 'reference/impact-truth.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in truth))
        self.dataset = self.root / 'dataset'; self.reference = self.root / 'reference'
        self.submission = self.root / 'submission/submission.json'

    def prepare(self):
        """Build a request from the current isolated fixture directories."""
        return prepare_combined(self.dataset, self.reference, self.submission)

    def mutate(self, path, change):
        """Apply one JSON fixture change without touching repository examples."""
        target = self.root / path; value = json.loads(target.read_text()); change(value)
        target.write_text(json.dumps(value))

    def test_handoff_is_deterministic_and_honest(self):
        """Hash provenance changes with evidence without implying correctness."""
        first = self.prepare()
        self.assertEqual(first, self.prepare())
        self.assertEqual(len(first['impact_records']), 7)
        self.assertEqual(first['assessment']['functional_correctness'], 'not_evaluated')
        self.assertFalse(first['evidence_validation']['correctness_demonstrated'])
        original = first['input_sha256']['evidence']
        self.mutate('submission/sdlc-evidence.json', lambda v: v.update(rationale='Different decision'))
        self.assertNotEqual(original, self.prepare()['input_sha256']['evidence'])

    def test_identity_and_shape_mismatches(self):
        """Submission identity and contract errors fail before handoff."""
        for field, value in [('commit_sha', 'a'*40), ('challenge_id', 'confirmation-context-v1'), ('schema_version', '2.0')]:
            with self.subTest(field=field):
                original = self.submission.read_bytes()
                self.mutate('submission/submission.json', lambda v: v.update({field: value}))
                with self.assertRaises(ValueError): self.prepare()
                self.submission.write_bytes(original)

    def test_paths_and_symlinks(self):
        """Student file references cannot traverse or escape through symlinks."""
        for path in ('../outside.json', '/etc/passwd', 'https://example.org/remote'):
            self.mutate('submission/submission.json', lambda v: v.update(evidence=path))
            with self.assertRaises(ValueError): self.prepare()
        self.mutate('submission/submission.json', lambda v: v.update(evidence='escape.json'))
        (self.root / 'submission/escape.json').symlink_to(self.root / 'reference/truth.jsonl')
        with self.assertRaises(ValueError): self.prepare()

    def test_impact_coverage_duplicates_and_labels(self):
        """Missing, duplicate and unknown impact predictions are invalid."""
        path = self.root / 'submission/impact-predictions.jsonl'; original = path.read_text()
        rows = original.splitlines()
        bad = json.loads(rows[0]); bad['affected_services'] += ['unknown']
        for text in ('\n'.join(rows[1:]), original + rows[0]+'\n', json.dumps(bad)+'\n'+'\n'.join(rows[1:]), 'null\n'):
            path.write_text(text)
            with self.assertRaises(ValueError): self.prepare()
        path.write_text(original)

    def test_protected_output_and_reference_locations(self):
        """Answer requests cannot overwrite inputs or enter public directories."""
        for output in (self.dataset / 'answers.json', self.reference / 'answers.json', self.submission.parent / 'answers.json'):
            with self.assertRaises(ValueError): write_combined(self.dataset, self.reference, self.submission, output)
            self.assertFalse(output.exists())
        destination = self.root / 'request.json'
        write_combined(self.dataset, self.reference, self.submission, destination)
        original = destination.read_bytes()
        with self.assertRaises(FileExistsError): write_combined(self.dataset, self.reference, self.submission, destination)
        self.assertEqual(original, destination.read_bytes())
        with self.assertRaises(ValueError): prepare_combined(self.dataset, self.dataset, self.submission)

    def test_cli_and_smoke(self):
        """Offline public rehearsal and handoff CLI both succeed."""
        result = subprocess.run([sys.executable, '-m', 'booking_simulator.combined_evaluation',
                                 '--dataset', str(self.dataset), '--reference', str(self.reference),
                                 '--submission', str(self.submission), '--output', str(self.root / 'request.json')],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = run_smoke()
        self.assertTrue(report['valid'])
        self.assertFalse(report['student_correctness_demonstrated'])

    def test_incomplete_reference_cannot_reduce_required_coverage(self):
        """Removing the same incident from both sides cannot hide an omitted case."""
        reference = self.reference / 'impact-truth.jsonl'
        original = reference.read_text()
        rows = [json.loads(line) for line in original.splitlines()]
        predictions = self.submission.parent / 'impact-predictions.jsonl'
        prediction_rows = [json.loads(line) for line in predictions.read_text().splitlines()]
        predictions.write_text(''.join(json.dumps(row)+'\n' for row in prediction_rows if row['case_id'] != rows[0]['case_id']))
        reference.write_text(''.join(json.dumps(row)+'\n' for row in rows[1:]))
        with self.assertRaisesRegex(ValueError, 'six public incident IDs'): self.prepare()
        for invalid in ('null\n', original + json.dumps(rows[0])+'\n'):
            reference.write_text(invalid)
            with self.assertRaisesRegex(ValueError, 'six public incident IDs'): self.prepare()

    def test_output_symlink_traversal_in_each_protected_directory(self):
        """Reject student-visible output aliases even if the target is outside inputs."""
        external = self.root / 'external'; external.mkdir()
        for protected in (self.dataset, self.reference, self.submission.parent):
            shared = protected / 'shared'; shared.symlink_to(external, target_is_directory=True)
            for output in (shared / 'answers.json', protected / '..' / protected.name / 'shared/answers.json'):
                with self.assertRaises(ValueError):
                    write_combined(self.dataset, self.reference, self.submission, output)
                self.assertFalse((external / 'answers.json').exists())
        # The inverse alias into a protected directory is forbidden too.
        alias = external / 'student'; alias.symlink_to(self.dataset, target_is_directory=True)
        with self.assertRaises(ValueError):
            write_combined(self.dataset, self.reference, self.submission, alias / 'answers.json')
