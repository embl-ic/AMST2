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
            'workflow:pre_existing_transforms:results/fiji-transforms.json',
            'workflow:run_sbs:false',
            'workflow:run_nsbs:true',
        ])
        self.assertEqual(generate.call_args.args[0], 'pre_align')

    def test_fiji_preset_allows_explicit_overrides(self):
        print('Testing get_default_parameter_file: explicit overrides')
        arguments = ['amst2-wf-pre_align-get_default_parameter_file',
                     '--fiji', 'results/fiji-transforms.json',
                     '--params', 'workflow:run_nsbs:false']

        with patch.object(sys, 'argv', arguments):
            with patch('amst2.workflows.lib.get_default_parameter_file_from_repo') as generate:
                get_default_parameter_file()

        params = generate.call_args.kwargs['params']
        self.assertEqual(params[-1], 'workflow:run_nsbs:false')
        self.assertEqual(params[2], 'workflow:run_nsbs:true')
