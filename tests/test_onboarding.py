"""Executable onboarding commands and public-CI boundary regressions."""
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class OnboardingTests(unittest.TestCase):
    def test_documented_first_run(self):
        """Execute the actual first-run commands without writing into the checkout."""
        guide = (ROOT / 'docs/student-guide.md').read_text()
        block = re.search(r'```bash\n(.*?)```', guide, re.DOTALL).group(1)
        commands = [shlex.split(line) for line in block.splitlines() if line.strip()]
        self.assertEqual(len(commands), 2)
        with tempfile.TemporaryDirectory() as root:
            for args in commands:
                self.assertEqual(args[0], 'python')
                args[0] = sys.executable
                if '--output' in args:
                    args[args.index('--output') + 1] = root
                try:
                    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=30)
                except subprocess.TimeoutExpired:
                    self.fail(f"Documented command timed out: {shlex.join(args)}")
                self.assertEqual(result.returncode, 0, result.stderr)
                if '--predictions' in args:
                    report = json.loads(result.stdout)
                    self.assertTrue(report['valid'])
                    self.assertEqual(report['row_count'], 3)
            manifest = json.loads((Path(root) / 'dataset/manifest.json').read_text())
            self.assertEqual(manifest['booking_count'], 25)
            self.assertTrue((Path(root) / 'reference/truth.jsonl').exists())
            self.assertFalse((Path(root) / 'dataset/truth.jsonl').exists())

    def test_local_documentation_links(self):
        """Keep the onboarding entry points and contract links navigable offline."""
        for name in ('README.md', 'CONTRIBUTING.md', 'docs/student-guide.md', 'docs/sandbox-security.md'):
            path = ROOT / name
            for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', path.read_text()):
                if '://' in target or target.startswith('#'):
                    continue
                with self.subTest(document=name, target=target):
                    self.assertTrue((path.parent / target.split('#')[0]).exists())

    def assert_checkout_credentials_disabled(self, workflow):
        """Require explicit credential disabling within every checkout step."""
        steps = re.split(r"(?m)^[ \t]+- ", workflow)[1:]
        pattern = r"(?m)^\s*uses:\s*['\"]?actions/checkout@"
        checkouts = [step for step in steps if re.search(pattern, step)]
        checkout_lines = re.findall(r"(?m)^\s*(?:- )?uses:\s*['\"]?actions/checkout@", workflow)
        self.assertGreater(len(checkouts), 0)
        self.assertEqual(len(checkouts), len(checkout_lines))
        for step in checkouts:
            self.assertRegex(step, r"(?m)^\s+with:\s*$")
            self.assertRegex(step, r"(?m)^\s+persist-credentials:[ \t]*false[ \t]*$")

    def test_every_checkout_requires_explicit_credential_setting(self):
        """A safe first checkout must not conceal a later unsafe checkout."""
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        self.assert_checkout_credentials_disabled(workflow)
        for setting in ('', '        with:\n          persist-credentials: true\n'):
            second = workflow + '      - name: Second checkout\n        uses: actions/checkout@v4\n' + setting
            with self.assertRaises(AssertionError):
                self.assert_checkout_credentials_disabled(second)
        safe_second = workflow + '      - name: Second checkout\n        uses: actions/checkout@v4\n        with:\n          persist-credentials: false\n'
        self.assert_checkout_credentials_disabled(safe_second)

    def test_public_ci_has_no_privileged_execution(self):
        """Guard the specific public workflow against credential/privilege regressions."""
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        self.assertNotIn('pull_request_target', workflow)
        self.assertNotIn('secrets.', workflow)
        self.assertNotIn('self-hosted', workflow)
        self.assert_checkout_credentials_disabled(workflow)
        self.assertIn('timeout-minutes: 5', workflow)
        permissions = re.search(r'^permissions:\n((?:[ \t]+.*\n)+)', workflow, re.MULTILINE).group(1)
        self.assertEqual(permissions.strip(), 'contents: read')
        self.assertNotRegex(workflow, r'\b(?:id-token|contents|actions|packages):\s*write')
