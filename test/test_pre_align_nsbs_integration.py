"""Opt-in integration test for the real NSBS-only pre-alignment workflow.

Set AMST2_NSBS_INTEGRATION_YAML to a configured local parameter YAML file.
The test runs Snakemake/elastix and writes to the YAML's output directory.
"""

import os
import unittest
import warnings
from pathlib import Path

import yaml

from amst2.workflows.pre_align import _run_pre_align


class TestPreAlignNsbsIntegration(unittest.TestCase):

    def setUp(self):
        warnings.simplefilter('ignore', category=Warning)

    def test_nsbs_only_real_execution(self):
        print('Testing pre_align: real NSBS-only Snakemake/elastix execution')
        yaml_path = os.environ.get('AMST2_NSBS_INTEGRATION_YAML')
        if not yaml_path:
            self.skipTest('Set AMST2_NSBS_INTEGRATION_YAML to opt in')

        yaml_path = Path(yaml_path).expanduser().resolve()
        with yaml_path.open(encoding='utf-8') as handle:
            parameters = yaml.safe_load(handle)

        workflow = parameters.get('workflow', {})
        self.assertFalse(workflow.get('pre_existing_transforms'))
        self.assertFalse(workflow.get('run_sbs', True))
        self.assertTrue(workflow.get('run_nsbs', True))
        self.assertFalse(parameters.get('stack_to_ome_zarr', {}).get('active', False))
        self.assertFalse(parameters.get('pre_align_to_tif_stack', {}).get('active', False))

        general = parameters['general']
        self.assertFalse(general.get('auto_pad', False))
        self.assertGreater(parameters['nsbs_alignment']['z_step'], 1)
        input_path = Path(general['input_dirpath']).expanduser().resolve()
        output_path = Path(general['output_dirpath']).expanduser().resolve()
        self.assertTrue(input_path.exists(), f'Missing input: {input_path}')
        self.assertNotEqual(input_path, output_path)
        self.assertFalse(output_path.exists(),
                         'Use a fresh, nonexistent output directory for this integration test')

        # This is intentionally not mocked: it invokes actual Snakemake/elastix.
        # Results are preserved in the configured output directory for inspection.
        _run_pre_align(str(yaml_path), dryrun=False, verbose=False)

        expected = (
            'nsbs_alignment/nsbs_alignment.done',
            'nsbs_alignment/nsbs.meta/elastix.json',
            'nsbs_alignment/nsbs.ome.zarr',
            'pre-align-combined.json',
            'pre-align.json',
            'apply_pre_align/apply_pre_align.done',
            'apply_pre_align/pre-align.ome.zarr',
        )
        for relative_path in expected:
            self.assertTrue((output_path / relative_path).exists(),
                            f'Missing workflow result: {relative_path}')

        self.assertFalse((output_path / 'sbs_alignment').exists())
        self.assertFalse((output_path / 'apply_initial_transforms').exists())

        from squirrel.library.affine_matrices import AffineStack

        transform_stack = AffineStack.read(str(output_path / 'pre-align.json'))
        self.assertTrue(transform_stack.sequenced)
        self.assertGreater(len(transform_stack), 0)
