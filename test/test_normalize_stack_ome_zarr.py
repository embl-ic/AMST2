import runpy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from squirrel.library.ome_zarr import OMEZarrStore


SCRIPT = Path(__file__).resolve().parents[1] / "amst2" / "snakemake_call_scripts" / "normalize_stack.py"


def test_normalize_batches_write_complete_pyramid(tmp_path, monkeypatch):
    print('Testing workflow: normalize batches into pre-created OME-Zarr and update pyramid ...')
    import squirrel.library.normalization as normalization

    shape = (17, 16, 16)
    factors = ((1, 2, 2),)
    chunks = ((8, 8, 8), (8, 8, 8))
    src = tmp_path / 'input.ome.zarr'
    dst = tmp_path / 'output.ome.zarr'
    reference = tmp_path / 'reference.ome.zarr'
    source = (np.arange(np.prod(shape), dtype=np.uint32).reshape(shape) % 251).astype('uint8')

    def create(path):
        return OMEZarrStore.create(
            path=str(path), shape=shape, dtype='uint8', chunks=chunks,
            downsample_factors=factors, ome_version='0.4', zarr_format=2,
            shards=None
        )

    input_store = create(src)
    input_store.write(0, (0, 0, 0), source)
    create(dst)
    expected = create(reference)

    def normalize_slices(dataset, *, z_range, **kwargs):
        start, stop = z_range
        return (np.asarray(dataset[start:stop], dtype=np.uint16) + 7).clip(0, 255).astype('uint8')

    monkeypatch.setattr(normalization, 'normalize_slices', normalize_slices)
    expected_data = normalize_slices(source, z_range=(0, shape[0]))
    expected.write(0, (0, 0, 0), expected_data)
    expected.rebuild_pyramid()

    for batch_idx in (0, 8, 16):
        marker = tmp_path / f'normalize_stack_{batch_idx}.done'
        sm = SimpleNamespace(
            wildcards={'idx': str(batch_idx)},
            input=[str(dst)], output=[str(marker)], threads=1,
            params={'run_info': {
                'input_ome_zarr_filepath': str(src), 'batch_size': 8,
                'dilate_background': False, 'quantiles': (0.1, 0.9),
                'anchors': (0, 255), 'verbose': False
            }}
        )
        runpy.run_path(str(SCRIPT), run_name='__main__', init_globals={'snakemake': sm})
        assert marker.exists()

    result = OMEZarrStore(str(dst), mode='r')
    for level in range(len(result.metadata.levels)):
        np.testing.assert_array_equal(result.dataset(level)[:], expected.dataset(level)[:])


def test_normalize_unaligned_batch_does_not_mark_done(tmp_path, monkeypatch):
    print('Testing workflow: reject unaligned normalization batch without completion marker ...')
    import squirrel.library.normalization as normalization

    shape = (16, 16, 16)
    chunks = ((8, 8, 8), (8, 8, 8))
    src = tmp_path / 'input.ome.zarr'
    dst = tmp_path / 'output.ome.zarr'
    for path in (src, dst):
        OMEZarrStore.create(
            path=str(path), shape=shape, dtype='uint8', chunks=chunks,
            downsample_factors=((1, 2, 2),), ome_version='0.4', zarr_format=2,
            shards=None
        )
    monkeypatch.setattr(normalization, 'normalize_slices',
                        lambda dataset, *, z_range, **kwargs: np.ones((4, 16, 16), dtype='uint8'))
    marker = tmp_path / 'normalize_stack_4.done'
    sm = SimpleNamespace(
        wildcards={'idx': '4'}, input=[str(dst)], output=[str(marker)], threads=1,
        params={'run_info': {
            'input_ome_zarr_filepath': str(src), 'batch_size': 4,
            'dilate_background': False, 'quantiles': (0.1, 0.9),
            'anchors': (0, 255), 'verbose': False
        }}
    )
    with pytest.raises(ValueError, match='aligned'):
        runpy.run_path(str(SCRIPT), run_name='__main__', init_globals={'snakemake': sm})
    assert not marker.exists()
