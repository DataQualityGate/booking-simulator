"""One-command offline rehearsal of public contracts, not a student solution."""
import json
from pathlib import Path
import tempfile

from .cli import save
from .combined_evaluation import write_combined
from .incidents import evaluate

ROOT = Path(__file__).resolve().parent.parent


def run_smoke():
    """Exercise old generation and combined validation in an ephemeral directory."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        save(root / 'generated', 42, 20, incidents=True)
        request = write_combined(ROOT / 'examples/evaluation/dataset',
                                 ROOT / 'examples/evaluation/reference',
                                 ROOT / 'examples/combined/submission.json', root / 'request.json')
        predictions = [{'case_id': row['case_id'], **row['prediction']} for row in request['impact_records']]
        truth = [{'case_id': row['case_id'], **row['expected']} for row in request['impact_records']]
        score = evaluate(predictions, truth)
        if score['correct'] != score['total']:
            raise ValueError('Public impact fixture no longer matches its public reference')
        return {'valid': True, 'booking_records': len(request['booking_evaluation']['records']),
                'impact_cases': len(request['impact_records']), 'evidence_valid': request['evidence_validation']['valid'],
                'student_correctness_demonstrated': False}


def main():
    """Print a repeatable public rehearsal result without leaving output files."""
    print(json.dumps(run_smoke(), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
