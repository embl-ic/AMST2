import sys
import unittest
import warnings
from unittest.mock import patch

from amst2.workflows.pre_align import get_default_parameter_file


class TestPreAlignFijiPreset(unittest.TestCase):

    def setUp(self):
        warnings.simplefilter('ignore', category=Warning)

    def test_fiji_preset_disables_sbs_and_enables_nsbs(self):
        print('Testing get_default_parameter_file: Fiji preset settings')
        arguments = ['amst2-wf-pre_align-get_default_parameter_file',
                     '--fiji', 'results/fiji-transforms.json']

        with patch.object(sys, 'argv', arguments):
            with patch('amst2.workflows.lib.get_default_parameter_file_from_repo') as generate:
                get_default_parameter_file()

        params = generate.call_args.kwargs['params']
        self.assertEqual(params, [
            'pre_existing_transforms:active:true',
            'pre_existing_transforms:transform_filepath:results/fiji-transforms.json',
            'sbs_alignment:active:false',
            'nsbs_alignment:active:true',
        ])
        self.assertEqual(generate.call_args.args[0], 'pre_align')

    def test_fiji_preset_allows_explicit_overrides(self):
        print('Testing get_default_parameter_file: explicit overrides')
        arguments = ['amst2-wf-pre_align-get_default_parameter_file',
                     '--fiji', 'results/fiji-transforms.json',
                     '--params', 'nsbs_alignment:active:false']

        with patch.object(sys, 'argv', arguments):
            with patch('amst2.workflows.lib.get_default_parameter_file_from_repo') as generate:
                get_default_parameter_file()

        params = generate.call_args.kwargs['params']
        self.assertEqual(params[-1], 'nsbs_alignment:active:false')
        self.assertEqual(params[3], 'nsbs_alignment:active:true')
