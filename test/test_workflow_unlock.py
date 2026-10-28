"""Regression tests for AMST2 workflow unlocking."""
import importlib.util
import json
import signal
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class TestWorkflowUnlock(unittest.TestCase):

    def setUp(self):
        path = Path(__file__).resolve().parents[1] / 'amst2/workflows/lib.py'
        spec = importlib.util.spec_from_file_location('workflow_unlock_test', path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_unlock_existing_cache_only(self):
        print('Testing unlock targets only existing Snakemake caches')
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = (Path(tmpdir) / 'nsbs_alignment' / 'snk_cache' /
                     'stack_alignment_nsbs')
            cache.mkdir(parents=True)
            (cache / 'run.json').write_text('{}')
            params = {'general': {'output_dirpath': tmpdir}}
            with patch.object(subprocess, 'run') as run:
                run.return_value.returncode = 0
                self.module.unlock_snakemake_workflows(
                    params, ['sbs_alignment', 'nsbs_alignment'])
            run.assert_called_once()
            command = run.call_args.args[0]
            self.assertIn('--unlock', command)
            self.assertEqual(command[command.index('--directory') + 1], str(cache))
            self.assertTrue(command[command.index('--snakefile') + 1].endswith(
                'elastix_stack_alignment.snk'))
            self.assertFalse((Path(tmpdir) / 'sbs_alignment').exists())

    def test_unlock_does_not_modify_run_identity(self):
        print('Testing unlock leaves run identity untouched')
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = Path(tmpdir) / '.amst2' / 'run-identity.json'
            manifest.parent.mkdir()
            manifest.write_text('{"configuration": "original"}')
            params = {'general': {'output_dirpath': tmpdir}}
            with patch.object(subprocess, 'run') as run:
                self.module.unlock_snakemake_workflows(params, ['nsbs_alignment'])
            run.assert_not_called()
            self.assertEqual(json.loads(manifest.read_text()),
                             {'configuration': 'original'})

    def test_unlock_failure_is_reported(self):
        print('Testing failed unlock stops with an error')
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Path(tmpdir) / 'sbs_alignment/snk_cache/stack_alignment_sbs'
            cache.mkdir(parents=True)
            (cache / 'run.json').write_text('{}')
            params = {'general': {'output_dirpath': tmpdir}}
            with patch.object(subprocess, 'run') as run:
                run.return_value.returncode = 1
                with self.assertRaisesRegex(RuntimeError, 'unlock failed'):
                    self.module.unlock_snakemake_workflows(params, ['sbs_alignment'])

    def test_repeated_interrupt_is_ignored_during_cleanup(self):
        print('Testing additional SIGINT is ignored during cleanup')
        class FakeProcess:
            pid = 12345
            returncode = None

            def __init__(self):
                self.stderr = self

            def __iter__(self):
                raise KeyboardInterrupt

            def wait(self, timeout=None):
                self.returncode = -signal.SIGINT
                return self.returncode

            def close(self):
                pass

        original = signal.getsignal(signal.SIGINT)
        with patch.object(subprocess, 'Popen', return_value=FakeProcess()), \
                patch.object(self.module.os, 'killpg'):
            self.assertEqual(self.module.run_snakemake_workflow('command', 'test'), 130)
        self.assertEqual(signal.getsignal(signal.SIGINT), original)
