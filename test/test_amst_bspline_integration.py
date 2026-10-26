"""Opt-in real B-spline AMST integration test.

Set AMST2_BSPLINE_INTEGRATION_YAML to a parameter YAML whose pre-alignment
outputs already exist. This test executes real Snakemake and elastix jobs.
"""

import os
import unittest
from pathlib import Path

import yaml

from amst2.workflows.amst import _run_amst


class TestAmstBsplineIntegration(unittest.TestCase):

    def test_real_bspline_amst(self):
        yaml_filepath = os.environ.get('AMST2_BSPLINE_INTEGRATION_YAML')
        if not yaml_filepath:
            self.skipTest('Set AMST2_BSPLINE_INTEGRATION_YAML to opt in')

        yaml_filepath = Path(yaml_filepath).expanduser().resolve()
        with yaml_filepath.open(encoding='utf-8') as handle:
            parameters = yaml.safe_load(handle)

        self.assertIn(parameters['amst']['transform'], ('bspline', 'BSplineTransform'))
        self.assertFalse(parameters.get('amst_to_tif_stack', {}).get('active', False),
                         'Disable optional TIFF export for this integration test')

        output_dirpath = Path(parameters['general']['output_dirpath']).expanduser().resolve()
        input_dirpath = Path(parameters['general'].get(
            'pre_align_dirpath', output_dirpath / 'apply_pre_align' / 'pre-align.ome.zarr')).expanduser().resolve()
        pre_align_json = Path(parameters.get('apply_amst', {}).get(
            'pre_align_transforms', parameters['general'].get(
                'pre_align_transforms', str(output_dirpath / 'pre-align.json'))))

        self.assertTrue(input_dirpath.is_dir(), f'Missing pre-aligned OME-Zarr: {input_dirpath}')
        self.assertTrue(pre_align_json.is_file(), f'Missing pre-alignment transforms: {pre_align_json}')
        self.assertFalse((output_dirpath / 'amst').exists(),
                         'Use an output directory with no previous AMST results')
        self.assertFalse((output_dirpath / 'apply_amst').exists(),
                         'Use an output directory with no previous AMST application')

        # Intentionally real: do not mock squirrel, Snakemake, or elastix.
        _run_amst(str(yaml_filepath), verbose=False)

        for relative in (
            'amst/amst.done',
            'amst/amst',
            'apply_amst/apply_amst.done',
            'apply_amst/amst.ome.zarr',
        ):
            self.assertTrue((output_dirpath / relative).exists(),
                            f'Missing workflow result: {relative}')

        transforms_dir = output_dirpath / 'amst' / 'amst'
        self.assertTrue(any(transforms_dir.iterdir()), 'B-spline transformation directory is empty')
        self.assertFalse((output_dirpath / 'amst' / 'amst.meta').exists())
        self.assertEqual(list((output_dirpath / 'amst').rglob('*preview*')), [])


if __name__ == '__main__':
    unittest.main()
