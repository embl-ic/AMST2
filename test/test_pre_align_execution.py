import os
import tempfile
import unittest
import warnings
from unittest.mock import patch

import numpy as np

from amst2.workflows.pre_align import _run_pre_align


class TestPreAlignExecution(unittest.TestCase):

    def setUp(self):
        warnings.simplefilter('ignore', category=Warning)

    def test_nsbs_only_uses_original_input(self):
        print('Testing pre_align: NSBS-only input and final application')
        with tempfile.TemporaryDirectory() as directory:
            config = {
                'general': {
                    'input_dirpath': '/original',
                    'output_dirpath': os.path.join(directory, 'output'),
                    'stack_key': 's0',
                    'auto_pad': False
                },
                'stack_to_ome_zarr': {'active': False},
                        'pre_align_to_tif_stack': {'active': False},
                        'pre_existing_transforms': {'active': False},
                'sbs_alignment': {'active': False},
                'nsbs_alignment': {'active': True}
            }
            with patch('amst2.workflows.lib.load_parameter_yaml', return_value=config), \
                    patch('amst2.workflows.lib.run_apply_transformation') as apply, \
                    patch('amst2.workflows.lib.run_nsbs_alignment') as align:
                _run_pre_align('unused.yaml', dryrun=True)

            align.assert_called_once()
            self.assertEqual(align.call_args.kwargs['parameter_key'], 'nsbs_alignment')
            self.assertEqual(align.call_args.kwargs['input_dirpath'], '/original')
            self.assertEqual(align.call_args.args[0]['nsbs_alignment']['stack_key'], 's0')
            apply.assert_called_once()
            self.assertEqual(apply.call_args.kwargs['input_dirpath'], '/original')
            self.assertEqual(apply.call_args.kwargs['parameter_key'], 'apply_pre_align')

    def test_synthetic_resampling_uses_expected_image_coordinates(self):
        print('Testing pre_align: squirrel resamples known synthetic translations')
        from squirrel.library.affine_matrices import AffineStack
        from squirrel.workflows.elastix import apply_multi_step_stack_alignment_workflow
        import tifffile

        with tempfile.TemporaryDirectory() as directory:
            image = np.zeros((64, 64), dtype=np.uint8)
            image[24:32, 24:32] = 255
            moved = np.zeros_like(image)
            moved[24:32, 29:37] = 255
            tifffile.imwrite(os.path.join(directory, '000.tif'), image)
            tifffile.imwrite(os.path.join(directory, '001.tif'), moved)

            identity = np.eye(3)

            # The second slice is displaced five pixels to the right.
            # Squirrel uses (row, column) coordinate order.
            # Transformix resampling uses an output-to-input mapping,
            # so a positive column translation moves image content left.
            correction = identity.copy()
            correction[1, 2] = 5

            transforms = AffineStack.from_array(
                np.stack([identity, correction]),
                sequenced=True
            )
            transforms_path = os.path.join(directory, 'transforms.json')
            transforms.write(transforms_path)

            result = apply_multi_step_stack_alignment_workflow(
                directory, [transforms_path], pattern='*.tif',
                assert_sequenced=True, n_workers=1, quiet=True,
                resample_interpolator='nearest'
            )
            self.assertEqual(result.shape, (2, 64, 64))
            np.testing.assert_array_equal(result[0], result[1])

    def test_composed_affines_match_sequential_resampling(self):
        print('Testing pre_align: numerical affine composition')
        from amst2.workflows.pre_align import _compose_stage_transforms
        from squirrel.library.affine_matrices import AffineStack
        from squirrel.workflows.elastix import apply_multi_step_stack_alignment_workflow
        import tifffile

        with tempfile.TemporaryDirectory() as directory:
            image = np.zeros((64, 64), dtype=np.uint8)
            image[12:19, 17:22] = 255
            image[30:34, 40:51] = 128
            image[43:53, 12:16] = 64

            source_dir = os.path.join(directory, 'source')
            intermediate_dir = os.path.join(directory, 'intermediate')
            os.makedirs(source_dir)
            os.makedirs(intermediate_dir)
            for index in range(2):
                tifffile.imwrite(os.path.join(source_dir, f'{index:03d}.tif'), image)

            identity = np.eye(3)
            translation = identity.copy()
            translation[1, 2] = 5
            rotation = np.array([[0., -1., 63.],
                                 [1., 0., 0.],
                                 [0., 0., 1.]])

            stage_paths = []
            for name, matrix in [('translation', translation), ('rotation', rotation)]:
                filepath = os.path.join(directory, f'{name}.json')
                AffineStack.from_array(
                    np.stack([identity, matrix]), sequenced=True
                ).write(filepath)
                stage_paths.append(filepath)

            options = dict(pattern='*.tif', assert_sequenced=True,
                           n_workers=1, quiet=True,
                           resample_interpolator='nearest')
            first = apply_multi_step_stack_alignment_workflow(
                source_dir, [stage_paths[0]], **options
            )
            for index, frame in enumerate(first):
                tifffile.imwrite(os.path.join(intermediate_dir, f'{index:03d}.tif'), frame)

            sequential = apply_multi_step_stack_alignment_workflow(
                intermediate_dir, [stage_paths[1]], **options
            )
            combined_path = os.path.join(directory, 'combined.json')
            _compose_stage_transforms(stage_paths, combined_path)
            combined = apply_multi_step_stack_alignment_workflow(
                source_dir, [combined_path], **options
            )

            np.testing.assert_array_equal(combined[0], image)
            self.assertGreater(np.count_nonzero(sequential[1]), 0)
            np.testing.assert_array_equal(combined, sequential)
