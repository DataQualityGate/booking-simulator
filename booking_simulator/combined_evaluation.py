"""Prepare combined public SDLC/impact handoffs without executing student code."""
import argparse
import hashlib
import json
from pathlib import Path

from .challenges import get_challenge
from .evaluation_adapter import _read, _rows, prepare_evaluation
from .evidence import _reference_kind, _schema_errors, validate_evidence
from .incidents import SERVICES, _index, _labels
from .predictions import _parse

SCHEMA = Path(__file__).resolve().parent.parent / 'schemas' / 'combined-submission-v1.schema.json'


def _submission_path(root, name):
    if _reference_kind(name) != 'local':
        raise ValueError('Submission files must be local repository-relative paths')
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Submission path escapes submission directory')
    return path


def _impact_records(predictions, truth):
    """Validate exact impact coverage and prepare expected/predicted label pairs."""
    fields = {'case_id', 'affected_services', 'possibly_affected_services'}
    for rows, expected_fields in ((predictions, fields), (truth, fields | {'unaffected_services'})):
        for row in rows:
            if not isinstance(row, dict) or row.keys() != expected_fields:
                raise ValueError('Invalid impact record fields')
            if not isinstance(row['case_id'], str) or not row['case_id'].strip():
                raise ValueError('Impact case_id must be a nonempty string')
            _labels(row, set(SERVICES), reference='unaffected_services' in expected_fields)
    predicted, expected = _index(predictions, 'prediction'), _index(truth, 'reference')
    if not expected or predicted.keys() != expected.keys():
        raise ValueError('Impact predictions must cover every reference and challenge case exactly once')
    return [{'case_id': key,
             'prediction': {name: sorted(predicted[key][name]) for name in sorted(fields - {'case_id'})},
             'expected': {name: sorted(expected[key][name]) for name in sorted(fields - {'case_id'} | {'unaffected_services'})}}
            for key in sorted(expected)]


def prepare_combined(dataset, reference, submission, *, repository=None):
    """Return an instructor-only request; presence validation is not grading.

    Functional execution, held-out assessment and qualitative process review are
    responsibilities of engineering-evals in disposable isolated environments.
    """
    dataset, reference, submission = map(Path, (dataset, reference, submission))
    root = submission.parent
    submission_text, submission_hash = _read(submission)
    manifest = _parse(submission_text)
    errors = _schema_errors(manifest, _parse(SCHEMA.read_text(encoding='utf-8')))
    if errors:
        raise ValueError('Invalid combined submission: ' + '; '.join(errors))
    paths = {key: _submission_path(root, manifest[key])
             for key in ('booking_predictions', 'impact_predictions', 'evidence')}
    # Keep every instructor source outside public/student inputs, including symlinks.
    impact_truth_path = (reference / 'impact-truth.jsonl').resolve()
    for source in ((reference / 'truth.jsonl').resolve(), impact_truth_path):
        if source.is_relative_to(dataset.resolve()) or source.is_relative_to(root.resolve()):
            raise ValueError('Instructor references must stay outside dataset and submission directories')
    evidence_text, evidence_hash = _read(paths['evidence'])
    report = validate_evidence(evidence_text, repository=repository)
    if not report['valid']:
        raise ValueError('Invalid SDLC evidence: ' + '; '.join(report['errors']))
    evidence = _parse(evidence_text)
    for field in ('challenge_id', 'commit_sha'):
        if manifest[field] != evidence[field]:
            raise ValueError('Submission/evidence mismatch: ' + field)
    challenge = get_challenge(manifest['challenge_id'])
    booking = prepare_evaluation(dataset, reference, paths['booking_predictions'])
    prediction_text, prediction_hash = _read(paths['impact_predictions'])
    truth_text, truth_hash = _read(impact_truth_path)
    records = _impact_records(_rows(prediction_text), _rows(truth_text) + [challenge['impact']])
    challenge_hash = hashlib.sha256(json.dumps(challenge, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {
        'contract_version': '1.0', 'task': 'combined_sdlc_impact',
        'challenge_id': manifest['challenge_id'], 'commit_sha': manifest['commit_sha'],
        'input_sha256': {'submission': submission_hash, 'evidence': evidence_hash,
                         'impact_predictions': prediction_hash, 'impact_truth': truth_hash,
                         'challenge': challenge_hash},
        'booking_evaluation': booking, 'impact_records': records,
        'functional_contract': challenge,
        'sdlc_evidence': evidence, 'evidence_validation': report,
        'assessment': {'functional_correctness': 'not_evaluated',
                       'regression': 'not_evaluated', 'impact': 'not_scored',
                       'process_review': 'requires_independent_review'},
    }


def write_combined(dataset, reference, submission, output, *, repository=None):
    dataset, reference, submission, output = map(Path, (dataset, reference, submission, output))
    destination = output.resolve()
    if any(destination.is_relative_to(path.resolve()) for path in (dataset, reference, submission.parent)):
        raise ValueError('Instructor request must be outside dataset, reference and submission directories')
    # Fully validate before creating output; exclusive creation protects other files.
    request = prepare_combined(dataset, reference, submission, repository=repository)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as handle:
        handle.write(json.dumps(request, indent=2, sort_keys=True) + '\n')
    return request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--submission', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repository', type=Path)
    args = parser.parse_args()
    try:
        write_combined(args.dataset, args.reference, args.submission, args.output, repository=args.repository)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f'Prepared instructor-only combined request in {args.output}; no student code executed or graded.')


if __name__ == '__main__':
    main()
