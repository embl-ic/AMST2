"""Regression tests for AMST2's remaining squirrel 0.5.5 affine call scripts."""
import runpy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from squirrel.library.affine_matrices import AffineStack

SCRIPTS = Path(__file__).resolve().parents[1] / "amst2" / "snakemake_call_scripts"


def _stack(path, translations, *, sequenced=False, metadata=None, pivot=(5., 7.)):
    matrices = np.repeat(np.eye(3)[None], len(translations), axis=0)
    matrices[:, :2, 2] = translations
    AffineStack.from_array(matrices, pivot=pivot, sequenced=sequenced,
                           metadata=metadata).write(path)


def _run(script, inputs, outputs, run_info, **params):
    import builtins
    old = getattr(builtins, "snakemake", None)
    builtins.snakemake = SimpleNamespace(
        input=list(map(str, inputs)), output=list(map(str, outputs)),
        params={"run_info": run_info, **params}, threads=1)
    try:
        runpy.run_path(str(SCRIPTS / script), run_name="__main__")
    finally:
        if old is None:
            del builtins.snakemake
        else:
            builtins.snakemake = old


def test_join_affine_multiple_files_and_pivot(tmp_path):
    print('Testing workflow: join affine files and preserve sequencing and pivot ...')
    a, b, out = (tmp_path / name for name in ('a.json', 'b.json', 'joined.json'))
    _stack(a, [[1., 2.], [2., 1.]])
    if not np.allclose(AffineStack.read(a).pivot, [5., 7.]):
        pytest.skip("Requires squirrel Patch A.2 pivot serialization")
    _stack(b, [[-1., 3.]])
    _run('join_transformations.py', [a, b], [out], {'transform': 'affine'})
    result = AffineStack.read(out)
    assert result.sequenced
    np.testing.assert_allclose(result.pivot, [5., 7.])
    np.testing.assert_allclose(result.as_array()[:, :2, 2],
                               [[1., 2.], [3., 3.], [2., 6.]])


def test_preview_join_without_ome_zarr(tmp_path):
    print('Testing workflow: preview joins affines and writes transform metadata ...')
    a, b, preview, out = (tmp_path / name for name in
                          ('a.json', 'b.json', 'preview.placeholder', 'joined.json'))
    bounds = [[0., 0., 10., 12.], [0., 0., 10., 12.]]
    _stack(a, [[1., 0.], [0., 2.]], metadata={'bounds': bounds})
    _stack(b, [[1., 1.]], metadata={'bounds': [[0., 0., 10., 12.]]})
    # Non-OME-Zarr input follows the placeholder-output branch.
    import tifffile
    tifffile.imwrite(tmp_path / "slice_000.tif", np.zeros((10, 12), dtype=np.uint8))
    _run('alignment_preview.py', [a, b], [preview, out], {
        'preview_downsample_level': 0, 'input_ome_zarr_filepath': str(tmp_path),
        'verbose': False, 'stack_key': 'data', 'stack_pattern': '*.tif'
    }, save_joined_transforms=True, compute_auto_pad=True)
    result = AffineStack.read(out)
    assert result.sequenced
    assert result.has_metadata('stack_shape')
    assert result.get_metadata('stack_shape')[0] == 3
    assert preview.exists()


def test_bspline_branch_preserves_existing_loader(tmp_path, monkeypatch):
    print('Testing workflow: B-spline join retains Elastix loader and writer ...')
    from squirrel.library import elastix
    calls = []
    class Dummy:
        def to_file(self, path):
            calls.append(('write', str(path)))
    monkeypatch.setattr(elastix, 'load_transform_stack_from_multiple_files',
                        lambda paths: (calls.append(('load', list(paths))), Dummy())[1])
    out = tmp_path / 'bspline'
    _run('join_transformations.py', [tmp_path / 'part'], [out],
         {'transform': 'bspline'})
    assert calls[0][0] == 'load'
    assert calls[1] == ('write', str(out))


def test_preview_scale_geometry_and_pivot():
    print('Testing workflow: preview scaling preserves expected Z length and pivot ...')
    stack = AffineStack.identity(8, ndim=2, pivot=[5., 7.], sequenced=True,
                                 metadata={'stack_shape': [8, 32, 32]})
    scaled = stack.scaled_for_stack_resize(0.5)
    assert len(scaled) == 4
    np.testing.assert_allclose(scaled.pivot, [2.5, 3.5])
    assert scaled.sequenced
