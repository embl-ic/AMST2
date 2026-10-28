"""Regression tests for interrupted Snakemake execution."""
import importlib.util
import signal
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch


class TestWorkflowInterrupt(unittest.TestCase):

    def test_interrupt_stops_process_group(self):
        print('Testing interrupt forwards SIGINT to the Snakemake process group')
        path = Path(__file__).resolve().parents[1] / 'amst2/workflows/lib.py'
        spec = importlib.util.spec_from_file_location('workflow_interrupt_test', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        class FakeProcess:
            pid = 12345
            returncode = None

            def __init__(self, *args, **kwargs):
                self.stderr = self
                self.closed = False
                self.options = kwargs

            def __iter__(self):
                raise KeyboardInterrupt

            def wait(self, timeout=None):
                self.returncode = -signal.SIGINT
                return self.returncode

            def close(self):
                self.closed = True

        process = FakeProcess()
        with patch.object(subprocess, 'Popen', return_value=process) as popen, \
                patch.object(module.os, 'killpg') as killpg:
            result = module.run_snakemake_workflow('snakemake', 'nsbs_alignment')

        self.assertEqual(result, 130)
        self.assertEqual(popen.call_args.kwargs['start_new_session'], True)
        self.assertEqual(popen.call_args.kwargs['stdout'], subprocess.DEVNULL)
        killpg.assert_called_once_with(12345, signal.SIGINT)
        self.assertTrue(process.closed)

    def test_lock_exception_is_reported(self):
        print('Testing lock errors are not misreported as successful execution')
        path = Path(__file__).resolve().parents[1] / 'amst2/workflows/lib.py'
        spec = importlib.util.spec_from_file_location('workflow_lock_test', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        class FakeProcess:
            returncode = 0

            def __init__(self, *args, **kwargs):
                self.stderr = iter(['LockException:\n', 'Directory cannot be locked\n'])

            def wait(self):
                return 0

        with patch.object(subprocess, 'Popen', FakeProcess):
            self.assertEqual(module.run_snakemake_workflow('snakemake', 'nsbs'), 1)
