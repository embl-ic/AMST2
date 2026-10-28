import unittest
from pathlib import Path


class TestApplyTransformationSequencing(unittest.TestCase):

    def test_nonsequenced_affine_stacks_are_allowed(self):
        print('Testing apply_transformation: non-sequenced affine stacks are allowed')

        script_path = (Path(__file__).resolve().parents[1] / 'amst2' /
                       'snakemake_call_scripts' / 'apply_transformation.py')
        script = script_path.read_text()

        self.assertIn('assert_sequenced=False,', script)
        self.assertNotIn('assert_sequenced=True,', script)
