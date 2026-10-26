"""Numerical integration tests for AMST2 affine application to OME-Zarr."""
import subprocess
import tempfile
import unittest
import warnings
from pathlib import Path

import numpy as np


class TestOMEZarrTransformationApplication(unittest.TestCase):

    def setUp(self):
        warnings.simplefilter('ignore', category=Warning)

    @staticmethod
    def _apply(root, batch_size, matrices):
        from squirrel.library.affine_matrices import AffineStack
        from squirrel.library.ome_zarr import OMEZarrStore

        depth = len(matrices)
        data = np.zeros((depth, 32, 32), dtype=np.uint16)
        for z in range(depth):
            data[z, 7 + z, 10] = 100 + z
            data[z, 15, 20 - z] = 200 + z

        input_path = root / 'input.ome.zarr'
        store = OMEZarrStore.create(
            str(input_path), shape=data.shape, dtype=data.dtype,
            chunks=(1, 16, 16), shards=None,
            downsample_factors=((1, 2, 2),),
            resolution=(2.0, 0.5, 0.25), unit='micrometer',
            ome_version='0.4', zarr_format=2)
        store.write(0, (0, 0, 0), data, update_pyramid=True)

        # Verify the fixture through the same reader used by the application.
        input_readback = OMEZarrStore(str(input_path), mode='r').dataset(0)[:]
        np.testing.assert_array_equal(
            input_readback, data,
            err_msg='Synthetic OME-Zarr input differs from the intended pixels')

        transforms_path = root / 'transforms.json' 
        AffineStack.from_array(
            matrices, sequenced=True,
            metadata={'stack_shape': list(data.shape)}).write(str(transforms_path))

        output_dir = root / 'output'
        # Use the installed AMST2 entry point, which runs the real Snakemake workflow.
        command = [
            'amst2-apply_transformation', str(input_path), str(transforms_path),
            str(output_dir), '--stack_key', 's0', '--batch_size', str(batch_size),
            '--cores', '1', '--max_cores_per_task', '1',
            '--chunk_size', '1', '16', '16',
            '--downsample_factors', '2',
            '--resample_interpolator', 'nearest', '--no_autopad',
            '-out-oz-fn', 'result.ome.zarr',
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if 'At least one job did not complete successfully' in result.stderr or 'Exiting because a job execution failed' in result.stderr:
            raise AssertionError(
                f'Snakemake failed despite application exit code {result.returncode}:\n'
                f'{result.stdout}\n{result.stderr}')
        if result.returncode:
            raise AssertionError(
                f'AMST2 transformation application failed ({result.returncode}):\n'
                f'{result.stdout}\n{result.stderr}')

        output_path = output_dir / 'result.ome.zarr'
        if not output_path.is_dir():
            raise AssertionError(f'Application did not create {output_path}')
        self_check = OMEZarrStore(str(output_path), mode='r')
        return data, self_check

    def test_identity_preserves_pixels_across_partial_batches(self):
        print('Testing apply_transformation: identity preserves OME-Zarr pixels')
        matrices = np.repeat(np.eye(3)[None, :, :], 9, axis=0)
        with tempfile.TemporaryDirectory() as directory:
            source, output = self._apply(Path(directory), 4, matrices)
            actual = output.dataset(0)[:]
            np.testing.assert_array_equal(actual, source)
            self.assertEqual(output.dataset(0).dtype, source.dtype)
            self.assertEqual(tuple(output.shape(0)), source.shape)

    def test_known_translation_moves_pixels_in_output_to_input_direction(self):
        print('Testing apply_transformation: known integer translation')
        matrices = np.repeat(np.eye(3)[None, :, :], 9, axis=0)
        matrices[:, 1, 2] = 3  # Positive column offset samples three pixels right.
        with tempfile.TemporaryDirectory() as directory:
            source, output = self._apply(Path(directory), 4, matrices)
            expected = np.zeros_like(source)
            expected[:, :, :-3] = source[:, :, 3:]
            np.testing.assert_array_equal(output.dataset(0)[:], expected)

    def test_slice_dependent_translations_cross_batch_boundaries(self):
        print('Testing apply_transformation: slice-dependent shifts across batches')
        matrices = np.repeat(np.eye(3)[None, :, :], 9, axis=0)
        # Different shifts on both sides of the 4/8 slice batch boundaries.
        shifts = [0, 1, 2, 3, 0, -1, -2, -3, 1]
        matrices[:, 1, 2] = shifts
        with tempfile.TemporaryDirectory() as directory:
            source, output = self._apply(Path(directory), 4, matrices)
            expected = np.zeros_like(source)
            for z, shift in enumerate(shifts):
                if shift > 0:
                    expected[z, :, :-shift] = source[z, :, shift:]
                elif shift < 0:
                    expected[z, :, -shift:] = source[z, :, :shift]
                else:
                    expected[z] = source[z]
            np.testing.assert_array_equal(output.dataset(0)[:], expected)

    def test_identity_results_independent_of_batch_size(self):
        print('Testing apply_transformation: batch size does not change pixels')
        matrices = np.repeat(np.eye(3)[None, :, :], 9, axis=0)
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            _, output_four = self._apply(Path(first), 4, matrices)
            _, output_eight = self._apply(Path(second), 8, matrices)
            np.testing.assert_array_equal(output_four.dataset(0)[:],
                                          output_eight.dataset(0)[:])


if __name__ == '__main__':
    unittest.main()
