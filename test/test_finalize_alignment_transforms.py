import unittest
import warnings


class TestFinalizeAlignmentTransforms(unittest.TestCase):

    def setUp(self):
        warnings.simplefilter('ignore', category=Warning)

    def test_finalize_transforms_without_preview(self):
        print('Testing finalize_alignment_transforms: writes transforms without a preview')
        import tempfile
        from pathlib import Path
        import numpy as np
        import tifffile
        from squirrel.library.affine_matrices import AffineStack
        from amst2.snakemake_call_scripts.finalize_alignment_transforms import (
            finalize_alignment_transforms)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tifffile.imwrite(root / 'slice_000.tif', np.zeros((10, 12), dtype=np.uint8))
            for index in range(2):
                AffineStack.identity(1, ndim=2, sequenced=True).write(
                    root / f'elastix_{index}.json')

            output = root / 'elastix.json'
            run_info = {'input_ome_zarr_filepath': str(root),
                        'stack_key': 's0', 'stack_pattern': '*.tif',
                        'stack_shape': [2, 10, 12]}
            finalize_alignment_transforms(
                [str(root / f'elastix_{index}.json') for index in range(2)],
                str(output), run_info)

            result = AffineStack.read(output)
            self.assertTrue(result.sequenced)
            self.assertTrue(result.has_metadata('stack_shape'))
            self.assertEqual(list(result.get_metadata('stack_shape')), [1, 10, 12])
            self.assertFalse((root / 'elastix_preview.h5').exists())
