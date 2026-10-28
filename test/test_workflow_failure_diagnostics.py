"""Regression tests for concise Snakemake failure diagnostics."""
import importlib.util
from pathlib import Path
import unittest
from contextlib import redirect_stdout
from io import StringIO


class TestWorkflowFailureDiagnostics(unittest.TestCase):

    def setUp(self):
        module_path = (Path(__file__).resolve().parents[1] / 'amst2' /
                       'workflows' / 'lib.py')
        spec = importlib.util.spec_from_file_location('workflow_diagnostics', module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.summarize = module._summarize_snakemake_failure

    def _render(self, message):
        output = StringIO()
        with redirect_stdout(output):
            self.summarize(message, 'nsbs_alignment')
        return output.getvalue()

    def test_rule_wildcards_and_log(self):
        print('Testing rule, batch start index, and log extraction')
        message = ('Error in rule elastix_stack_alignment:\n'
                   '    wildcards: idx=24\n'
                   '    log: /tmp/snakemake/job.log\n'
                   'ValueError: failed\n')
        summary = self._render(message)
        self.assertIn('stage: nsbs_alignment', summary)
        self.assertIn('Failed rule: elastix_stack_alignment', summary)
        self.assertIn('Batch start index (idx): 24', summary)
        self.assertIn('Job log: /tmp/snakemake/job.log', summary)
        self.assertIn('ValueError: failed', summary)

    def test_lock_hint(self):
        print('Testing explicit unlock recovery hint')
        summary = self._render('LockException:\nDirectory cannot be locked\n')
        self.assertIn('--unlock', summary)

    def test_unknown_failure_does_not_invent_details(self):
        print('Testing fallback when Snakemake supplies no job details')
        summary = self._render('process exited unexpectedly\n')
        self.assertIn('No rule or job details found', summary)
        self.assertNotIn('Failed rule:', summary)


if __name__ == '__main__':
    unittest.main()
