"""Prevent preview generation from re-entering the alignment Snakemake workflows."""

import unittest
from pathlib import Path


class TestNoAlignmentPreviews(unittest.TestCase):

    def test_alignment_snakefiles_have_no_preview_rules(self):
        workflows = Path(__file__).resolve().parents[1] / 'amst2' / 'snakemake_workflows'
        for name in ('amst_affine.snk', 'amst_bspline.snk',
                     'default_amst_pre_alignment.snk',
                     'template_matching_alignment.snk',
                     'elastix_stack_alignment.snk'):
            with self.subTest(name=name):
                contents = (workflows / name).read_text()
                self.assertNotIn('alignment_preview.py', contents)
                self.assertNotIn('preview.h5', contents)
                self.assertNotIn('rule final_preview:', contents)
                self.assertNotIn('rule amst_preview:', contents)

    def test_preview_script_removed(self):
        scripts = Path(__file__).resolve().parents[1] / 'amst2' / 'snakemake_call_scripts'
        self.assertFalse((scripts / 'alignment_preview.py').exists())

    def test_no_preview_options_in_alignment_entrypoints(self):
        root = Path(__file__).resolve().parents[1] / 'amst2'
        for name in ('amst.py', 'stack_alignment.py'):
            with self.subTest(name=name):
                contents = (root / name).read_text()
                self.assertNotIn("parser.add_argument('--no_preview", contents)
                self.assertNotIn("parser.add_argument('--preview_downsample_level", contents)
