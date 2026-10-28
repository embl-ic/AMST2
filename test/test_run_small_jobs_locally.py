import unittest
from pathlib import Path


class TestRunSmallJobsLocally(unittest.TestCase):

    def test_rule_selection(self):
        print('Testing conditional local rule selection')
        root = Path(__file__).resolve().parents[1] / 'amst2' / 'snakemake_workflows'
        expected = {
            'apply_transformation.snk': ['create_ome_zarr'],
            'elastix_stack_alignment.snk': ['create_ome_zarr', 'finalize_alignment_transforms'],
            'template_matching_alignment.snk': ['create_ome_zarr', 'finalize_alignment_transforms'],
            'amst_affine.snk': ['finalize_amst_transforms'],
        }
        for filename, rules in expected.items():
            content = (root / filename).read_text()
            self.assertIn("if run_info.get('run_small_jobs_locally', False):", content)
            self.assertIn('localrules: ' + ', '.join(rules), content)
        content = (root / 'apply_transformation.snk').read_text()
        self.assertNotIn('localrules: prepare_transforms', content)

    def test_default_generator_flags(self):
        print('Testing convenience flags in both default parameter generators')
        root = Path(__file__).resolve().parents[1] / 'amst2' / 'workflows'
        for filename in ('pre_align.py', 'amst.py'):
            content = (root / filename).read_text()
            self.assertIn("parser.add_argument('--run_small_jobs_locally'", content)
            self.assertIn("params.append('general:run_small_jobs_locally:true')", content)
