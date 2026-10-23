import json
import os
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch

from amst2.workflows.pre_align import _check_run_identity
from amst2.workflows.pre_align import _compose_stage_transforms


class TestPreAlignOutputLayout(unittest.TestCase):

    def setUp(self):
        warnings.simplefilter('ignore', category=Warning)

    def test_run_identity_is_hidden_and_rejects_untracked_output(self):
        print('Testing pre_align: hidden run identity and output protection')
        parameters = {'general': {'input_dirpath': 'input'}}
        with tempfile.TemporaryDirectory() as directory:
            _check_run_identity(parameters, [('nsbs', None)], directory)
            manifest = Path(directory) / '.amst2/run-identity.json'
            self.assertTrue(manifest.is_file())
            self.assertFalse((Path(directory) / 'pre-align-run-identity.json').exists())
            self.assertIn('configuration', json.loads(manifest.read_text()))
            _check_run_identity(parameters, [('nsbs', None)], directory)
            with self.assertRaises(RuntimeError):
                _check_run_identity({'changed': True}, [('nsbs', None)], directory)

        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'untracked.txt').write_text('existing')
            with self.assertRaises(RuntimeError):
                _check_run_identity(parameters, [('nsbs', None)], directory)

    def test_composition_does_not_leave_intermediate_files(self):
        print('Testing pre_align: temporary composition outputs')
        with tempfile.TemporaryDirectory() as directory:
            inputs = [os.path.join(directory, f'input-{i}.json') for i in range(3)]
            for filepath in inputs:
                Path(filepath).write_text('{}')
            output = os.path.join(directory, 'pre-align.json')
            calls = []

            def compose(paths, target, **kwargs):
                calls.append((paths, target))
                Path(target).write_text('{}')

            with patch('squirrel.workflows.transformation.dot_product_on_affines_workflow',
                       side_effect=compose):
                _compose_stage_transforms(inputs, output)

            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0][0][0], inputs[0])
            self.assertEqual(calls[1][0][1], inputs[2])
            self.assertEqual(calls[-1][1], output)
            self.assertTrue(Path(output).is_file())
            self.assertFalse(Path(calls[0][1]).exists())
            self.assertEqual(sorted(p.name for p in Path(directory).iterdir()),
                             ['input-0.json', 'input-1.json', 'input-2.json', 'pre-align.json'])
