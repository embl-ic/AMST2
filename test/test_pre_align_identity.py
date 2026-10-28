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

    def test_force_preserves_original_identity(self):
        print('Testing check_run_identity: forced mismatch preserves manifest')
        with tempfile.TemporaryDirectory() as directory:
            _check_run_identity({'sbs': {'sigma': 1}}, [('sbs', None)], directory)
            manifest = os.path.join(directory, '.amst2', 'run-identity.json')
            original = open(manifest).read()
            _check_run_identity({'sbs': {'sigma': 2}}, [('sbs', None)], directory, force=True)
            self.assertEqual(open(manifest).read(), original)
            with self.assertRaisesRegex(RuntimeError, 'sbs.sigma'):
                _check_run_identity({'sbs': {'sigma': 2}}, [('sbs', None)], directory)

    def test_force_legacy_manifest_and_untracked_directory(self):
        print('Testing check_run_identity: legacy and untracked forced reuse')
        with tempfile.TemporaryDirectory() as directory:
            _check_run_identity({'a': 1}, [('sbs', None)], directory)
            manifest = os.path.join(directory, '.amst2', 'run-identity.json')
            with open(manifest) as handle:
                legacy = json.load(handle)
            legacy.pop('parameters')
            with open(manifest, 'w') as handle:
                json.dump(legacy, handle)
            _check_run_identity({'a': 2}, [('sbs', None)], directory, force=True)
            with open(manifest) as handle:
                self.assertEqual(json.load(handle), legacy)
        with tempfile.TemporaryDirectory() as directory:
            with open(os.path.join(directory, 'old.done'), 'w'):
                pass
            _check_run_identity({'a': 1}, [('sbs', None)], directory, force=True)
            self.assertFalse(os.path.exists(os.path.join(directory, '.amst2')))

    def test_external_change_reports_and_force_keeps_identity(self):
        print('Testing check_run_identity: changed imported transforms')
        with tempfile.TemporaryDirectory() as directory:
            transform = os.path.join(directory, 'transforms.json')
            with open(transform, 'w') as handle:
                handle.write('first')
            stages = [('initial', transform)]
            output = os.path.join(directory, 'output')
            os.mkdir(output)
            _check_run_identity({'a': 1}, stages, output)
            with open(transform, 'w') as handle:
                handle.write('second')
            with self.assertRaisesRegex(RuntimeError, 'Imported transformation'):
                _check_run_identity({'a': 1}, stages, output)
            _check_run_identity({'a': 1}, stages, directory, force=True)
