"""Ensure AMST2 does not recreate stage-specific .meta directories."""
import unittest
from pathlib import Path


class TestNoMetaDirectories(unittest.TestCase):
    def test_alignment_entrypoints_and_workflow_use_direct_stage_paths(self):
        root = Path(__file__).resolve().parents[1] / 'amst2'
        for name in ('amst.py', 'stack_alignment.py', 'workflows/amst.py'):
            with self.subTest(name=name):
                content = (root / name).read_text()
                self.assertNotIn("}.meta'", content)
                self.assertNotIn("'amst.meta'", content)

    def test_stage_outputs_stay_in_stage_directory(self):
        root = Path(__file__).resolve().parents[1] / 'amst2'
        for name in ('amst.py', 'stack_alignment.py'):
            with self.subTest(name=name):
                content = (root / name).read_text()
                self.assertIn("meta_dirpath = output_location_args['target_dirpath']", content)
