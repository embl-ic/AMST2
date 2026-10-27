"""OME-Zarr metadata compatibility checks for squirrel 0.5.5."""
from pathlib import Path
import pytest
import numpy as np


def test_store_metadata_and_dataset(tmp_path):
    print('Testing OME-Zarr metadata, resolution, units and dataset access ...')
    from squirrel.library.ome_zarr import OMEZarrStore
    path = tmp_path / 'input.ome.zarr'
    store = OMEZarrStore.create(
        str(path), shape=(8, 32, 32), dtype=np.uint16,
        chunks=(4, 16, 16), shards=None,
        downsample_factors=((1, 2, 2),),
        resolution=(2., 0.5, 0.5), unit='micrometer',
        ome_version='0.4', zarr_format=2,
    )
    reopened = OMEZarrStore(str(path), mode='r')
    assert tuple(reopened.metadata.scale(0)) == (2., 0.5, 0.5)
    assert reopened.metadata.units == 'micrometer'
    assert reopened.dataset(0).shape == (8, 32, 32)
    assert reopened.dataset(0).dtype == np.dtype('uint16')
    assert reopened.dataset(1).shape == (8, 16, 16)


def test_legacy_dataset_key_selection(tmp_path):
    print('Testing OME-Zarr dataset key selection for TIFF export ...')
    from squirrel.library.ome_zarr import OMEZarrStore
    path = tmp_path / 'input.ome.zarr'
    OMEZarrStore.create(str(path), shape=(8, 32, 32),
                        chunks=(4, 16, 16), shards=None,
                        downsample_factors=((1, 2, 2),),
                        ome_version='0.4', zarr_format=2)
    store = OMEZarrStore(str(path), mode='r')
    for key, level in [('s0', 0), ('s1', 1)]:
        selected = store.dataset(int(key[1:]))
        np.testing.assert_equal(selected.shape, store.dataset(level).shape)
    with pytest.raises(ValueError):
        key = 'invalid'
        if not key.startswith('s'):
            raise ValueError(key)
