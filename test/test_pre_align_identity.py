import json
import os
import tempfile
import unittest
import warnings

from amst2.workflows.pre_align import _check_run_identity


class TestPreAlignIdentity(unittest.TestCase):

    def setUp(self):
        warnings.simplefilter('ignore', category=Warning)

    def test_check_run_identity_rejects_changed_external_file(self):
        print('Testing check_run_identity: changed external transforms')
        with tempfile.TemporaryDirectory() as directory:
            output = os.path.join(directory, 'output')
            os.mkdir(output)
            transform = os.path.join(directory, 'transforms.json')
            with open(transform, 'w') as handle:
                json.dump({'value': 1}, handle)
            config = {'general': {'input_dirpath': 'input'}}
            stages = [('initial', transform)]
            _check_run_identity(config, stages, output)
            _check_run_identity(config, stages, output)
            with open(transform, 'w') as handle:
                json.dump({'value': 2}, handle)
            with self.assertRaises(RuntimeError):
                _check_run_identity(config, stages, output)

    def test_check_run_identity_rejects_untracked_output(self):
        print('Testing check_run_identity: untracked outputs')
        with tempfile.TemporaryDirectory() as directory:
            with open(os.path.join(directory, 'old.done'), 'w'):
                pass
            with self.assertRaises(RuntimeError):
                _check_run_identity({'general': {}}, [('sbs', None)], directory)

    def test_check_run_identity_rejects_changed_parameters(self):
        print('Testing check_run_identity: changed parameters')
        with tempfile.TemporaryDirectory() as directory:
            _check_run_identity({'sbs': {'sigma': 1}}, [('sbs', None)], directory)
            with self.assertRaises(RuntimeError):
                _check_run_identity({'sbs': {'sigma': 2}}, [('sbs', None)], directory)
