import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('step9_replay', ROOT/'src/replay_summary.py')
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)


class SummaryChecks(unittest.TestCase):
    def setUp(self):
        self.facts = replay.load(ROOT/'examples/aggregate_facts.json')
        self.draft = replay.load(ROOT/'examples/ai_draft.json')

    def test_valid_saved_example(self):
        self.assertTrue(replay.validate(self.facts, self.draft))
        output = replay.render(self.facts, self.draft)
        self.assertIn('106,758', output)
        self.assertIn('30.6%', output)

    def test_changed_metric_rejected(self):
        self.facts['roc_auc'] = .99
        with self.assertRaisesRegex(ValueError, 'Source mismatch'):
            replay.validate(self.facts, self.draft)

    def test_changed_cohort_rejected(self):
        self.facts['cohort_patients'] = 106758
        with self.assertRaisesRegex(ValueError, 'Source mismatch'):
            replay.validate(self.facts, self.draft)

    def test_record_field_rejected(self):
        self.facts['patient_name'] = 'Synthetic test only'
        with self.assertRaisesRegex(ValueError, 'Unexpected'):
            replay.validate(self.facts, self.draft)

    def test_invented_number_rejected(self):
        self.draft['paragraphs'][0] += ' Accuracy is 99%.'
        with self.assertRaisesRegex(ValueError, 'Numbers must'):
            replay.validate(self.facts, self.draft)

    def test_unknown_placeholder_rejected(self):
        self.draft['paragraphs'][0] += ' {cost_savings}'
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            replay.validate(self.facts, self.draft)

    def test_missing_review_status_rejected(self):
        self.draft['status'] = 'Clinically approved'
        with self.assertRaisesRegex(ValueError, 'review status'):
            replay.validate(self.facts, self.draft)

    def test_unsupported_prose_remains_a_human_review_task(self):
        modified = copy.deepcopy(self.draft)
        modified['paragraphs'][3] = 'This model eliminates every adverse outcome.'
        # A numerical checker cannot judge clinical truth. Document this boundary.
        self.assertTrue(replay.validate(self.facts, modified))


if __name__ == '__main__':
    unittest.main(verbosity=2)
