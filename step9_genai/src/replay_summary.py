"""Validate source-linked facts and render a saved AI draft. No LLM/API call."""
import argparse
import json
import re
from pathlib import Path
from string import Formatter

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {
    'cohort_sessions': ',', 'cohort_patients': ',',
    'event_prevalence_pct': '.2f', 'test_sessions': ',',
    'test_patients': ',', 'selected_model': '', 'feature_count': '',
    'average_precision': '.3f', 'roc_auc': '.3f', 'brier_score': '.3f',
    'threshold': '.3f', 'sensitivity': '.1%', 'precision': '.1%',
}


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def validate(facts, draft, evidence_dir=ROOT / 'evidence'):
    metrics = load(evidence_dir / 'original_test_metrics.json')
    threshold = load(evidence_dir / 'decision_threshold.json')
    card = (evidence_dir / 'model_card.md').read_text(encoding='utf-8')
    expected = {
        'schema_version': 1, 'dataset': 'HEMOBP Version 3',
        'cohort_sessions': 106758, 'cohort_patients': 830,
        'event_prevalence_pct': 8.49, 'test_sessions': 21354,
        'test_patients': 170, 'selected_model': metrics['selected_model'],
        'threshold': threshold['threshold'], 'feature_count': len(threshold['features']),
    }
    for key in ['average_precision', 'roc_auc', 'brier_score', 'sensitivity', 'precision']:
        expected[key] = metrics['test_metrics_calibrated'][key]
    if set(facts) != set(expected):
        raise ValueError('Unexpected or missing aggregate fields')
    for key, value in expected.items():
        if type(facts[key]) is not type(value) or facts[key] != value:
            raise ValueError('Source mismatch: ' + key)
    for literal in ['106,758 sessions from 830 patients', '8.49%', '21,354 sessions', '170 independent patients']:
        if literal not in card:
            raise ValueError('Model card changed; reconcile the cohort facts')
    m = metrics['test_metrics_calibrated']
    if sum(m[k] for k in ['tp', 'tn', 'fp', 'fn']) != facts['test_sessions']:
        raise ValueError('Confusion-matrix total does not match test sessions')
    if metrics['operating_threshold'] != facts['threshold']:
        raise ValueError('Threshold source mismatch')
    if set(draft) != {'status', 'paragraphs'} or draft['status'] != 'AI-drafted example; investigator review pending':
        raise ValueError('Missing draft provenance/review status')
    if not isinstance(draft['paragraphs'], list) or len(draft['paragraphs']) != 4:
        raise ValueError('Expected four reviewable paragraphs')
    seen = set()
    for paragraph in draft['paragraphs']:
        if not isinstance(paragraph, str) or len(paragraph) > 2000:
            raise ValueError('Invalid paragraph')
        for literal, field, spec, conversion in Formatter().parse(paragraph):
            if re.search(r'\d', literal):
                raise ValueError('Numbers must come from source-linked placeholders')
            if field is not None:
                if field not in FIELDS or spec != FIELDS[field] or conversion:
                    raise ValueError('Unsupported placeholder or format')
                seen.add(field)
    if seen != set(FIELDS):
        raise ValueError('Missing required source-linked facts')
    return True


def render(facts, draft):
    return '# DIAL-ALERT: AI-assisted summary\n\n' + draft['status'] + '\n\n' + '\n\n'.join(
        p.format_map(facts) for p in draft['paragraphs']
    ) + '\n\nNumeric checks passed. Prose still requires investigator review.\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--facts', type=Path, default=ROOT/'examples/aggregate_facts.json')
    parser.add_argument('--draft', type=Path, default=ROOT/'examples/ai_draft.json')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    facts, draft = load(args.facts), load(args.draft)
    validate(facts, draft)
    result = render(facts, draft)
    print('PASS: aggregate facts match frozen source artifacts.\n')
    print('MODE: saved-draft replay; no live LLM call.\n')
    print(result)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding='utf-8')


if __name__ == '__main__':
    main()
