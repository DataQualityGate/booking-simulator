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


def active_workflow(workflow):
    """Strip comments from the policy fields in this workflow's plain block layout.

    This is a regression guard for the checked-in layout, not a general YAML
    parser or a substitute for reviewing executable workflow changes. Alternate
    permission/timeout layouts must fail these checks until explicitly supported.
    """
    active = []
    block_indent = None
    for line in workflow.splitlines():
        indent = len(line) - len(line.lstrip())
        if block_indent is not None:
            if not line.strip() or indent > block_indent:
                active.append(line)  # GitHub interpolates expressions even in shell comments.
                continue
            block_indent = None
        quote = None
        index = 0
        while index < len(line):
            char = line[index]
            if quote == '"' and char == '\\':
                index += 2
                continue
            if quote == "'" and line[index:index + 2] == "''":
                index += 2
                continue
            if quote:
                if char == quote:
                    quote = None
            elif char in ("'", '"'):
                quote = char
            elif char == '#' and (index == 0 or line[index - 1].isspace()):
                line = line[:index]
                break
            index += 1
        if quote:
            raise AssertionError('Multiline quoted scalars require explicit policy review')
        line = line.rstrip()
        active.append(line)
        if re.search(r':\s*[|>][-+0-9]*\s*$', line):
            block_indent = indent
    return '\n'.join(active) + '\n'



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
        for name in ('README.md', 'CONTRIBUTING.md', 'docs/student-guide.md', 'docs/sandbox-security.md', 'docs/bootcamp/combined-case-plan.md', 'docs/combined-submission.md'):
            path = ROOT / name
            for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', path.read_text()):
                if '://' in target or target.startswith('#'):
                    continue
                with self.subTest(document=name, target=target):
                    self.assertTrue((path.parent / target.split('#')[0]).exists())

    def assert_checkout_credentials_disabled(self, workflow):
        """Require explicit credential disabling within every checkout step."""
        workflow = active_workflow(workflow)
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

    def workflow_jobs(self, active):
        """Split only supported plain block jobs; reject layouts that hide boundaries."""
        section = re.search(r'(?ms)^jobs:\n(.*?)(?=^[^\s].*:[ \t]*$|\Z)', active)
        self.assertIsNotNone(section)
        identifiers = []
        for line in section.group(1).splitlines():
            if re.match(r'  \S', line):
                header = re.fullmatch(r'  ([A-Za-z_][A-Za-z0-9_-]*):', line)
                self.assertIsNotNone(header, f'Unsupported job layout: {line}')
                identifiers.append(header[1])
        self.assertGreater(len(identifiers), 0)
        self.assertEqual(len(identifiers), len(set(identifiers)), 'Duplicate job ID')
        jobs = re.findall(r'(?ms)^  [A-Za-z_][A-Za-z0-9_-]*:\n(.*?)(?=^  [A-Za-z_][A-Za-z0-9_-]*:\n|\Z)', section.group(1))
        self.assertEqual(len(jobs), len(identifiers))
        return jobs

    def assert_job_timeouts(self, workflow):
        """Require an active five-minute limit in every block-style CI job."""
        active = active_workflow(workflow)
        jobs = self.workflow_jobs(active)
        for job in jobs:
            self.assertRegex(job, r'(?m)^    timeout-minutes:[ \t]*5[ \t]*$')

    def assert_permissions_read_only(self, workflow):
        """Fail closed on scalar/flow permissions and any workflow/job write grant."""
        active = active_workflow(workflow)
        lines = [line for line in active.splitlines() if line.strip()]
        top_level = None
        for index, line in enumerate(lines):
            header = re.fullmatch(r'( *)permissions:[ \t]*(.*)', line)
            if not header:
                continue
            indent, inline = len(header[1]), header[2]
            self.assertEqual(inline, '', 'Use explicit block-style read-only permissions')
            entries = {}
            for entry in lines[index + 1:]:
                if len(entry) - len(entry.lstrip()) <= indent:
                    break
                setting = re.fullmatch(r' {' + str(indent + 2) + r'}([a-z][a-z-]*):[ \t]*(read|none)', entry)
                self.assertIsNotNone(setting, f'Unsafe or unsupported permission: {entry}')
                self.assertNotIn(setting[1], entries, 'Duplicate permission scope')
                entries[setting[1]] = setting[2]
            self.assertTrue(entries, 'Permissions must be explicit')
            if indent == 0:
                self.assertIsNone(top_level, 'Duplicate top-level permissions')
                top_level = entries
        self.assertEqual(top_level, {'contents': 'read'})
        jobs = self.workflow_jobs(active)
        for job in jobs:
            headers = re.findall(r'(?m)^    permissions:.*$', job)
            self.assertLessEqual(len(headers), 1, 'Duplicate job permission mapping')
            override = re.search(r'(?ms)^    permissions:\n(.*?)(?=^    \S|\Z)', job)
            effective = top_level if override is None else dict(re.findall(
                r'(?m)^      ([a-z][a-z-]*):[ \t]*(read|none)[ \t]*$', override.group(1)))
            if re.search(r'(?m)^\s*(?:- )?uses:\s*[\'\"]?actions/checkout@', job):
                self.assertEqual(effective.get('contents'), 'read', 'Checkout jobs need effective contents: read')

    def test_active_job_timeouts(self):
        """A comment, step setting or another bounded job cannot hide an unbounded job."""
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        self.assert_job_timeouts(workflow)
        invalid = [workflow.replace('    timeout-minutes: 5', '    # timeout-minutes: 5'),
                   workflow.replace('    timeout-minutes: 5', '      timeout-minutes: 5'),
                   workflow + '  extra:\n    runs-on: ubuntu-latest\n']
        for text in invalid:
            with self.assertRaises(AssertionError):
                self.assert_job_timeouts(text)
        self.assert_job_timeouts(workflow + '  extra:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5 # active limit\n')

    def test_active_permission_scopes(self):
        """Reject workflow/job write grants while ignoring commented examples."""
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        self.assert_permissions_read_only(workflow)
        invalid = [workflow.replace('permissions:\n  contents: read', 'permissions: write-all'),
                   workflow.replace('    timeout-minutes: 5', '    permissions:\n      issues: write\n    timeout-minutes: 5'),
                   workflow.replace('    timeout-minutes: 5', '    permissions: write-all\n    timeout-minutes: 5'),
                   workflow.replace('permissions:\n  contents: read', 'permissions: {contents: write}')]
        for text in invalid:
            with self.assertRaises(AssertionError):
                self.assert_permissions_read_only(text)
        self.assert_permissions_read_only(workflow + '# permissions: write-all\n#   issues: write\n')
        self.assert_permissions_read_only(workflow.replace('    timeout-minutes: 5', '    permissions:\n      contents: read\n      issues: none\n    timeout-minutes: 5'))

    def assert_public_ci_policy(self, text):
        """Check the supported public workflow layout without executing fixture commands."""
        workflow = active_workflow(text)
        self.assertNotIn('pull_request_target', workflow)
        self.assertNotRegex(workflow, r'(?i)\bsecrets\b')
        self.assertNotIn('self-hosted', workflow)
        self.assert_checkout_credentials_disabled(workflow)
        self.assert_job_timeouts(workflow)
        self.assert_permissions_read_only(workflow)

    def test_public_ci_has_no_privileged_execution(self):
        """Guard the checked-in public workflow against privilege regressions."""
        self.assert_public_ci_policy((ROOT / '.github/workflows/ci.yml').read_text())

    def test_quoted_hashes_and_script_expressions_stay_visible(self):
        """YAML/shell quoting and literal blocks must not conceal a secrets expression."""
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        lines = ["        run: 'echo \"#${{ secrets.TOKEN }}\"'",
                 '        run: "echo \\"#${{ secrets.TOKEN }}\\""',
                 "        run: 'echo ''#${{ secrets.TOKEN }}'''",
                 '        run: echo prefix#${{ secrets.TOKEN }}',
                 '        run: |\n          # ${{ secrets.TOKEN }}']
        for line in lines:
            text = workflow + '      - name: Synthetic prohibited expression\n' + line + '\n'
            self.assertIn('${{ secrets.TOKEN }}', active_workflow(text))
            with self.assertRaises(AssertionError):
                self.assert_public_ci_policy(text)
        self.assert_public_ci_policy(workflow + '# ${{ secrets.TOKEN }}\n')

    def test_checkout_requires_effective_job_contents_permission(self):
        """Job overrides replace workflow grants rather than merging with them."""
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        for entries in ('      issues: none', '      contents: none', '      issues: read'):
            changed = workflow.replace('    timeout-minutes: 5', '    permissions:\n' + entries + '\n    timeout-minutes: 5')
            with self.assertRaises(AssertionError):
                self.assert_permissions_read_only(changed)
        # A separate job without checkout does not need repository read access.
        self.assert_permissions_read_only(workflow + '  reporting:\n    permissions:\n      issues: none\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n    steps:\n      - run: echo synthetic\n')

    def test_documented_combined_contract_rehearsal(self):
        """Run the guide's public rehearsal commands without a student solution or keys."""
        guide = (ROOT / 'docs/student-guide.md').read_text()
        section = guide.split('## Rehearse the combined contracts', 1)[1]
        block = re.search(r'```bash\n(.*?)```', section, re.DOTALL).group(1)
        commands = [shlex.split(line) for line in block.splitlines() if line.strip()]
        self.assertEqual(len(commands), 3)
        for args in commands:
            self.assertEqual(args[0], 'python')
            args[0] = sys.executable
            try:
                result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=30)
            except subprocess.TimeoutExpired:
                self.fail('Documented combined rehearsal timed out')
            self.assertEqual(result.returncode, 0, result.stderr)
            value = json.loads(result.stdout)
            if args[2] == 'booking_simulator.smoke':
                self.assertTrue(value['valid'])
                self.assertFalse(value['student_correctness_demonstrated'])
            elif args[2] == 'booking_simulator.challenges':
                self.assertEqual(value['challenge_id'], 'supplier-recovery-v1')
            else:
                self.assertTrue(value['valid'])
                self.assertFalse(value['correctness_demonstrated'])

    def test_unsupported_job_layouts_fail_closed(self):
        """Quoted, flow-style and duplicate jobs cannot inherit a neighboring job's checks."""
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        unsupported = ["  'extra':\n    runs-on: ubuntu-latest\n",
                       '  "extra":\n    runs-on: ubuntu-latest\n',
                       '  extra: {runs-on: ubuntu-latest}\n',
                       '  test:\n    runs-on: ubuntu-latest\n']
        for extra in unsupported:
            for check in (self.assert_job_timeouts, self.assert_permissions_read_only):
                with self.subTest(extra=extra, check=check.__name__):
                    with self.assertRaises(AssertionError):
                        check(workflow + extra)
