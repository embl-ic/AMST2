import ast
import unittest
from pathlib import Path


class TestAmstAffineWorkflowStructure(unittest.TestCase):

    def test_only_required_rules_remain(self):
        print('Testing AMST affine: no disconnected placeholder rules')
        source = (Path(__file__).resolve().parents[1] / 'amst2' /
                  'snakemake_workflows' / 'amst_affine.snk').read_text()
        for rule in ('apply_transformations', 'create_ome_zarr',
                     'compute_auto_pad'):
            self.assertNotIn(f'rule {rule}:', source)
        self.assertNotIn('some_output_file', source)
        for rule in ('all', 'finalize_amst_transforms', 'amst'):
            self.assertIn(f'rule {rule}:', source)

    def test_finalization_target(self):
        print('Testing AMST affine: finalized transformations are the target')
        source = (Path(__file__).resolve().parents[1] / 'amst2' /
                  'snakemake_workflows' / 'amst_affine.snk').read_text()
        self.assertIn('os.path.join(meta_dirpath, "amst.json")', source)
        self.assertIn('"finalize_alignment_transforms.py"', source)
        self.assertNotIn('preview', source.lower())


if __name__ == '__main__':
    unittest.main()
