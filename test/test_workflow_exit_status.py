"""Regression coverage for Snakemake subprocess completion detection."""
import importlib.util
from pathlib import Path
import sys
import types


def _load_workflow_lib():
    path = Path(__file__).resolve().parents[1] / 'amst2' / 'workflows' / 'lib.py'
    spec = importlib.util.spec_from_file_location('amst2_workflow_lib_exit_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_with_stderr(monkeypatch, stderr, returncode):
    class FakeProcess:
        def __init__(self, *args, **kwargs):
            self.stderr = iter(stderr.splitlines(keepends=True))
            self.returncode = returncode
        def wait(self):
            return self.returncode

    monkeypatch.setattr('subprocess.Popen', FakeProcess)
    return _load_workflow_lib().run_snakemake_workflow('snakemake --cores 1', 'test_step')


def test_success_with_progress(monkeypatch):
    print('Testing successful Snakemake execution with progress output')
    assert _run_with_stderr(monkeypatch, '1 of 1 steps (100%) done\n', 0) == 0


def test_success_with_no_jobs(monkeypatch):
    print('Testing successful Snakemake execution with no jobs to run')
    assert _run_with_stderr(monkeypatch, 'Nothing to be done (all requested files are present and up to date).\n', 0) == 0


def test_failure_with_progress(monkeypatch):
    print('Testing failed Snakemake execution despite apparent completion progress')
    assert _run_with_stderr(monkeypatch, '1 of 1 steps (100%) done\n', 1) == 1


def test_failure_without_stderr(monkeypatch):
    print('Testing failed Snakemake execution with empty stderr')
    assert _run_with_stderr(monkeypatch, '', 2) == 1


def test_failure_message_with_misleading_zero_exit(monkeypatch):
    print('Testing explicit Snakemake job failure with misleading zero exit code')
    log = ('1 of 9 steps (11%) done\n'
           'Exiting because a job execution failed. Look above for error message\n'
           'WorkflowError:\nAt least one job did not complete successfully.\n')
    assert _run_with_stderr(monkeypatch, log, 0) == 1


def test_no_completion_marker_with_zero_exit(monkeypatch):
    print('Testing zero exit without a recognizable Snakemake success message')
    assert _run_with_stderr(monkeypatch, 'Submitted job 42\n', 0) == 1


def test_failure_after_full_progress(monkeypatch):
    print('Testing explicit failure overrides earlier 100 percent progress')
    log = ('9 of 9 steps (100%) done\n'
           'WorkflowError:\nAt least one job did not complete successfully.\n')
    assert _run_with_stderr(monkeypatch, log, 0) == 1
