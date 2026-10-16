import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from booking_simulator.evidence import validate_evidence

EXAMPLES = Path(__file__).resolve().parent.parent / 'examples' / 'evidence'


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        """Load an isolated copy of the synthetic evidence example."""
        self.value = json.loads((EXAMPLES / 'valid.json').read_text())

    def validate(self, value, **kwargs):
        """Serialize a fixture through the public validation entry point."""
        return validate_evidence(json.dumps(value), **kwargs)

    def test_public_fixtures_and_claims(self):
        """Presence validation never asserts functional correctness."""
        for name, valid in [('valid', True), ('missing', False), ('invalid', False)]:
            report = validate_evidence((EXAMPLES / (name + '.json')).read_text())
            self.assertEqual(report['valid'], valid, report)
            self.assertFalse(report['correctness_demonstrated'])
        self.assertEqual(self.validate(self.value)['verification'], 'structure_only')

    def test_invalid_shapes_and_json(self):
        """Malformed JSON, schema values and incomplete evidence fail."""
        for text in ('null', '[]', '{"schema_version":"1.0","schema_version":"1.0"}', 'NaN', '{'):
            report = validate_evidence(text)
            self.assertFalse(report['valid'])
            self.assertEqual(set(report), set(self.validate(self.value)))
            self.assertFalse(report['remote_references_verified'])
        for key, bad in [('commit_sha', 'main'), ('commit_sha', 'a' * 40 + '\n'), ('challenge_id', 'unknown'), ('tests', []),
                         ('rationale', ' '), ('reviews', [None]), ('human_decisions', []),
                         ('limitations', [5])]:
            value = copy.deepcopy(self.value); value[key] = bad
            self.assertFalse(self.validate(value)['valid'], key)
        value = copy.deepcopy(self.value); value['tests'][0]['result'] = 'maybe'
        self.assertFalse(self.validate(value)['valid'])

    def test_relationships(self):
        """Duplicate IDs and dangling finding references fail."""
        value = copy.deepcopy(self.value); value['tests'] *= 2
        self.assertFalse(self.validate(value)['valid'])
        value = copy.deepcopy(self.value); value['human_decisions'][0]['finding_ids'] = ['unknown']
        self.assertFalse(self.validate(value)['valid'])
        value = copy.deepcopy(self.value); value['reviews'][0]['findings'] *= 2
        self.assertFalse(self.validate(value)['valid'])

    def test_reference_safety(self):
        """Traversal and credential-bearing references are rejected."""
        for ref in ('../secret', '/etc/passwd', 'file:///etc/passwd', 'https://user:secret@example.org/a',
                    'https://example.org/?key=secret', '//example.org/a', 'a\\b', 'a\nb', '.', 'docs/'):
            value = copy.deepcopy(self.value); value['intent'] = ref
            self.assertFalse(self.validate(value)['valid'], ref)
        value = copy.deepcopy(self.value); value['intent'] = 'https://example.org/intent#section'
        report = self.validate(value)
        self.assertTrue(report['valid']); self.assertFalse(report['remote_references_verified'])

    def test_pinned_artifacts_and_commands_never_execute(self):
        """Artifact existence follows pinned Git objects without running commands."""
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            def git(*args):
                """Run a trusted Git setup/read operation in a temporary fixture."""
                environment = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
                return subprocess.run(['git', '-C', directory, *args], check=True, capture_output=True, text=True, env=environment).stdout.strip()
            git('init'); git('config', 'user.name', 'Synthetic'); git('config', 'user.email', 'test@example.org')
            (repo / 'artifact.md').write_text('synthetic')
            git('add', '.'); git('commit', '-m', 'fixture')
            value = copy.deepcopy(self.value); value['commit_sha'] = git('rev-parse', 'HEAD')
            value['intent'] = value['spec'] = 'artifact.md'
            for row in value['tests'] + value['reviews']: row['artifact'] = 'artifact.md'
            value['tests'][0]['command'] = f'touch {repo / "MUST_NOT_EXIST"}'
            self.assertTrue(self.validate(value, repository=repo)['valid'])
            self.assertFalse((repo / 'MUST_NOT_EXIST').exists())
            (repo / 'artifact.md').unlink()
            self.assertTrue(self.validate(value, repository=repo)['valid'])  # pinned commit, not working tree
            value['spec'] = 'missing.md'
            self.assertFalse(self.validate(value, repository=repo)['valid'])
            value['commit_sha'] = '0' * 40
            self.assertFalse(self.validate(value, repository=repo)['valid'])

    def test_cli_exit_codes_and_private_values_not_echoed(self):
        """CLI status and redacted diagnostics match the contract."""
        command = [sys.executable, '-m', 'booking_simulator.evidence', '--evidence']
        for name, code in [('valid', 0), ('missing', 1), ('invalid', 1), ('absent', 2)]:
            result = subprocess.run(command + [str(EXAMPLES / (name + '.json'))], capture_output=True, text=True)
            self.assertEqual(result.returncode, code, result.stderr)
            self.assertNotIn('FORBIDDEN-SYNTHETIC-FIELD', result.stdout + result.stderr)

    def test_git_environment_and_replacement_objects(self):
        """Validate the named repository and original tree despite ambient Git redirects."""
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            def git(*args):
                """Keep trusted fixture setup independent from ambient repository selection."""
                environment = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
                return subprocess.run(['git', '-C', directory, *args], env=environment,
                                      check=True, capture_output=True, text=True).stdout.strip()
            # Even fixture setup must ignore an inherited repository/object store.
            poison = {'GIT_DIR': str(repo / 'wrong.git'), 'GIT_WORK_TREE': '/nonexistent',
                      'GIT_OBJECT_DIRECTORY': str(repo / 'wrong-objects'),
                      'GIT_ALTERNATE_OBJECT_DIRECTORIES': str(repo / 'wrong-alternates'),
                      'GIT_CONFIG_COUNT': '1', 'GIT_CONFIG_KEY_0': 'core.bare', 'GIT_CONFIG_VALUE_0': 'true'}
            with patch.dict(os.environ, poison):
                git('init'); git('config', 'user.name', 'Synthetic'); git('config', 'user.email', 'test@example.org')
                (repo / 'artifact.md').write_text('original')
                git('add', '.'); git('commit', '-m', 'original')
                original = git('rev-parse', 'HEAD')
                value = copy.deepcopy(self.value); value['commit_sha'] = original
                value['intent'] = value['spec'] = 'artifact.md'
                for row in value['tests'] + value['reviews']: row['artifact'] = 'artifact.md'
                self.assertTrue(self.validate(value, repository=repo)['valid'])
                (repo / 'new.md').write_text('present only in replacement tree')
                git('add', '.'); git('commit', '-m', 'replacement')
                replacement = git('rev-parse', 'HEAD')
                git('replace', original, replacement)
                self.assertEqual(git('cat-file', '-t', original + ':new.md'), 'blob')
                value['spec'] = 'new.md'
                report = self.validate(value, repository=repo)
                self.assertFalse(report['valid'])
                self.assertTrue(any('missing at pinned commit' in error for error in report['errors']))
