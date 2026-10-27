import os
import tempfile
import unittest
import warnings
from unittest.mock import patch

from amst2.workflows.pre_align import _run_pre_align


class TestPreAlignIntermediate(unittest.TestCase):

    def setUp(self):
        warnings.simplefilter('ignore', category=Warning)

    def test_external_only_skips_intermediate_application(self):
        print('Testing pre_align: external-only applies transforms once')
        self._check_application_calls(False, False, 1)

    def test_external_plus_sbs_creates_intermediate(self):
        print('Testing pre_align: external plus SBS needs intermediate')
        self._check_application_calls(True, False, 2)

    def test_external_plus_nsbs_creates_intermediate(self):
        print('Testing pre_align: external plus NSBS needs intermediate')
        self._check_application_calls(False, True, 2)

    def _check_application_calls(self, sbs, nsbs, expected_count):
        with tempfile.TemporaryDirectory() as directory:
            transforms = os.path.join(directory, 'external.json')
            with open(transforms, 'w') as handle:
                handle.write('{}')
            config = {
                'general': {
                    'input_dirpath': '/input',
                    'output_dirpath': os.path.join(directory, 'output'),
                    'auto_pad': False
                },
                'workflow': {
                    'pre_existing_transforms': transforms,
                    'run_sbs': sbs,
                    'run_nsbs': nsbs
                }
            }
            with patch('amst2.workflows.lib.load_parameter_yaml', return_value=config), \
                    patch('amst2.workflows.lib.run_apply_transformation') as apply, \
                    patch('amst2.workflows.lib.run_nsbs_alignment') as align:
                _run_pre_align('unused.yaml', dryrun=True)

            self.assertEqual(apply.call_count, expected_count)
            self.assertEqual(align.call_count, int(sbs) + int(nsbs))
            self.assertEqual(apply.call_args_list[-1].kwargs['parameter_key'], 'apply_pre_align')
            self.assertEqual(apply.call_args_list[-1].kwargs['input_dirpath'], '/input')
            if expected_count == 2:
                self.assertEqual(apply.call_args_list[0].kwargs['parameter_key'],
                                 'apply_initial_transforms')
