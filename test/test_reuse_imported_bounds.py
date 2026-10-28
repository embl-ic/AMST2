import os
import tempfile
import unittest
import warnings
from unittest.mock import patch

import yaml

from amst2.workflows.pre_align import _run_pre_align


class TestReuseImportedBounds(unittest.TestCase):

    def setUp(self):
        warnings.simplefilter('ignore', category=Warning)

    def _parameters(self, directory, nsbs):
        return {
            'general': {
                'input_dirpath': 'input',
                'output_dirpath': directory,
                'auto_pad': True
            },
            'stack_to_ome_zarr': {'active': False},
            'pre_existing_transforms': {
                'active': True,
                'transform_filepath': 'imported.json'
            },
            'sbs_alignment': {'active': False},
            'nsbs_alignment': {'active': nsbs},
            'pre_align_to_tif_stack': {'active': False},
            'apply_pre_align': {},
        }

    def test_imported_only_uses_cluster_preparation(self):
        print('Testing imported-only cluster preparation')
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'parameters.yaml')
            with open(path, 'w') as handle:
                yaml.safe_dump(self._parameters(directory, False), handle)
            with patch('amst2.workflows.lib.run_apply_transformation') as apply:
                _run_pre_align(path, dryrun=True)
            self.assertEqual(apply.call_count, 2)
            self.assertTrue(apply.call_args_list[0].args[0][
                'apply_initial_transforms']['auto_pad'])

    def test_imported_nsbs_uses_cluster_preparation(self):
        print('Testing imported and NSBS cluster preparation')
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'parameters.yaml')
            with open(path, 'w') as handle:
                yaml.safe_dump(self._parameters(directory, True), handle)
            with patch('amst2.workflows.lib.run_apply_transformation') as apply, \
                    patch('amst2.workflows.lib.run_nsbs_alignment'):
                _run_pre_align(path, dryrun=True)
            self.assertEqual(apply.call_count, 2)
            self.assertTrue(apply.call_args_list[0].args[0][
                'apply_initial_transforms']['auto_pad'])
