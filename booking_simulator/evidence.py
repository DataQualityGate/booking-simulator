"""Validate evidence structure and optional pinned artifact existence, not correctness."""
import argparse
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from urllib.parse import urlsplit

from .predictions import _parse

SCHEMA_PATH = Path(__file__).resolve().parent.parent / 'schemas' / 'sdlc-evidence-v1.schema.json'


def _schema_errors(value, schema, path='$'):
    """Validate the closed subset of JSON Schema used by the bundled contract.

    This is not a general JSON Schema implementation. Unsupported keywords fail
    closed so a schema revision cannot silently weaken local validation.
    """
    supported = {'$schema', '$id', 'description', 'type', 'const', 'enum', 'required',
                 'properties', 'additionalProperties', 'items', 'minItems', 'minLength', 'pattern'}
    if schema.keys() - supported:
        raise ValueError('Unsupported bundled schema keyword')
    errors = []
    kind = schema.get('type')
    matches = {'object': isinstance(value, dict), 'array': isinstance(value, list),
               'string': isinstance(value, str)}
    if kind is not None and (kind not in matches or not matches[kind]):
        return [f'{path}: expected {kind}']
    if 'const' in schema and value != schema['const']:
        errors.append(f'{path}: unsupported constant')
    if 'enum' in schema and value not in schema['enum']:
        errors.append(f'{path}: unsupported value')
    if isinstance(value, dict):
        properties = schema.get('properties', {})
        for field in schema.get('required', []):
            if field not in value:
                errors.append(f'{path}.{field}: required')
        if schema.get('additionalProperties') is False and value.keys() - properties.keys():
            errors.append(f'{path}: unknown fields are forbidden')
        for key in sorted(value.keys() & properties.keys()):
            errors.extend(_schema_errors(value[key], properties[key], f'{path}.{key}'))
    if isinstance(value, list):
        if len(value) < schema.get('minItems', 0):
            errors.append(f'{path}: too few items')
        for i, item in enumerate(value):
            errors.extend(_schema_errors(item, schema.get('items', {}), f'{path}[{i}]'))
    if isinstance(value, str):
        if len(value) < schema.get('minLength', 0):
            errors.append(f'{path}: string is empty')
        if 'pattern' in schema and re.search(schema['pattern'], value) is None:
            errors.append(f'{path}: invalid string format')
    return errors


def _reference_kind(value):
    """Reject traversal and credential-bearing links without fetching any URL."""
    if any(ord(char) < 32 or char.isspace() for char in value) or '\\' in value:
        raise ValueError('Invalid artifact reference')
    parsed = urlsplit(value)
    if parsed.scheme:
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query:
            raise ValueError('Remote references require HTTPS without credentials or query')
        return 'remote'
    if parsed.netloc or parsed.query or parsed.fragment or ':' in value or PurePosixPath(value).is_absolute():
        raise ValueError('Local references must be repository-relative file paths')
    if '..' in value.split('/') or not value or value.endswith('/') or value == '.':
        raise ValueError('Invalid local artifact path')
    return 'local'


def _git(repository, *args):
    """Inspect Git object metadata without checking out or executing files."""
    result = subprocess.run(['git', '-C', str(repository), *args], capture_output=True, text=True, timeout=10)
    return result.returncode == 0, result.stdout.strip()


def validate_evidence(text, *, repository=None):
    """Check strict JSON/schema, ID relationships and optionally pinned Git objects.

    Commands recorded by students are never executed. Remote links are never
    fetched; their existence and content remain explicitly unverified.
    """
    report = {'schema_version': '1.0', 'valid': False, 'errors': [],
              'verification': 'structure_only', 'correctness_demonstrated': False,
              'remote_references_verified': False}
    errors = report['errors']
    try:
        evidence = _parse(text)
    except ValueError:
        errors.append('Invalid strict JSON')
        return report
    schema = _parse(SCHEMA_PATH.read_text(encoding='utf-8'))
    errors.extend(_schema_errors(evidence, schema))
    if errors:
        return report
    findings = [f for review in evidence['reviews'] for f in review['findings']]
    for name, values in [('tests', evidence['tests']), ('reviews', evidence['reviews']),
                         ('findings', findings), ('human_decisions', evidence['human_decisions'])]:
        ids = [row['id'] for row in values]
        if len(ids) != len(set(ids)):
            errors.append(f'{name}: duplicate IDs')
    finding_ids = {finding['id'] for finding in findings}
    for decision in evidence['human_decisions']:
        if len(decision['finding_ids']) != len(set(decision['finding_ids'])):
            errors.append('human_decisions: duplicate finding references')
        if set(decision['finding_ids']) - finding_ids:
            errors.append('human_decisions: unknown finding reference')
    references = [evidence['intent'], evidence['spec']]
    references += [row['artifact'] for row in evidence['tests'] + evidence['reviews']]
    local = []
    for ref in references:
        try:
            if _reference_kind(ref) == 'local':
                local.append(ref)
        except ValueError as error:
            errors.append(str(error))
    if repository is not None and not errors:
        try:
            commit = evidence['commit_sha']
            exists, kind = _git(repository, 'cat-file', '-t', commit)
            if not exists or kind != 'commit':
                errors.append('commit_sha: commit does not exist in repository')
            else:
                for ref in sorted(set(local)):
                    exists, kind = _git(repository, 'cat-file', '-t', f'{commit}:{ref}')
                    if not exists or kind != 'blob':
                        errors.append('Artifact file missing at pinned commit: ' + ref)
                report['verification'] = 'pinned_local_artifacts'
        except (OSError, subprocess.TimeoutExpired):
            errors.append('Cannot inspect repository objects')
    report['valid'] = not errors
    return report


def main():
    """Print diagnostics with distinct invalid-evidence and input-error exits."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--repository', type=Path, help='Read-only Git object checks at commit_sha')
    args = parser.parse_args()
    try:
        report = validate_evidence(args.evidence.read_text(encoding='utf-8'), repository=args.repository)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['valid'] else 1)


if __name__ == '__main__':
    main()
