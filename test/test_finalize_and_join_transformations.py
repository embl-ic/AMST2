"""Focused squirrel 0.5.5 compatibility tests for the Snakemake call script."""
from pathlib import Path
from types import SimpleNamespace
import runpy

import numpy as np
import pytest
from squirrel.library.affine_matrices import AffineStack

SCRIPT = Path(__file__).resolve().parents[1] / 'amst2/snakemake_call_scripts/finalize_and_join_transformations.py'
PIVOT = [7., 11.]
BOUNDS = [[0., 0., 20., 24.]] * 4


def stack(matrices, sequenced):
    return AffineStack.from_array(np.asarray(matrices, dtype=float), pivot=PIVOT,
                                  sequenced=sequenced, metadata={'bounds': BOUNDS})


def run_case(tmp_path, use_tm, use_local):
    relative = stack([
        [[1, 0, 0], [0, 1, 0]],
        [[0, -1, 2], [1, 0, 3]],
        [[1, 0, -2], [0, 1, 1]],
        [[1, 0, 1], [0, 1, -1]],
    ], False)
    local = relative.to_sequenced()
    tm = stack([matrix.as_compact() for matrix in local], True)
    # Nontrivial residual; ensure smoothing has an observable effect.
    tm = tm @ stack([[[1, 0, d], [0, 1, -d / 2]] for d in (0, 3, -2, 1)], True)
    paths = []
    for name, source in [('local0', relative[:2]), ('local1', relative[2:]),
                         ('tm0', tm[:2]), ('tm1', tm[2:])]:
        # Slicing is converted back to a stack to retain the intended per-file bounds.
        original = relative if name.startswith('local') else tm
        start = 0 if name.endswith('0') else 2
        fragment = AffineStack.from_array([m.as_compact() for m in original[start:start+2]],
                                         pivot=PIVOT, sequenced=original.sequenced,
                                         metadata={'bounds': BOUNDS[start:start+2]})
        path = tmp_path / (name + '.json')
        fragment.write(path)
        paths.append(path)
    selected = (paths[2:] if use_tm else [])
    if use_local:
        selected = paths[:2] + selected
    out = tmp_path / 'output.json'
    snakemake = SimpleNamespace(input=selected, output=[out],
                               params={'run_info': {'combine_sigma': 0.8},
                                       'use_tm': use_tm, 'use_local': use_local})
    runpy.run_path(str(SCRIPT), run_name='__main__', init_globals={'snakemake': snakemake})
    actual = AffineStack.read(out)
    if use_tm and use_local:
        expected = local @ (tm @ local.inverse()).smooth_gaussian(0.8)
    elif use_tm:
        expected = tm
    else:
        expected = local
    expected.set_metadata('bounds', BOUNDS)
    expected, shape = expected.auto_pad(stack_bounds=BOUNDS, extra_padding=16)
    np.testing.assert_allclose(actual.as_homogeneous(), expected.as_homogeneous(), atol=1e-9)
    np.testing.assert_allclose(actual.pivot, PIVOT)
    assert actual.sequenced
    assert actual.get_metadata('bounds') == BOUNDS
    assert actual.get_metadata('stack_shape') == shape


@pytest.mark.parametrize('use_tm,use_local', [(True, True), (True, False), (False, True)])
def test_finalize_branches(tmp_path, use_tm, use_local):
    print(f'Testing transformation finalization: template={use_tm}, local={use_local} ...')
    run_case(tmp_path, use_tm, use_local)


def test_finalize_rejects_no_alignment(tmp_path):
    print('Testing transformation finalization: reject missing alignment inputs ...')
    snakemake = SimpleNamespace(input=[], output=[tmp_path / 'out.json'],
                               params={'run_info': {'combine_sigma': 0.8},
                                       'use_tm': False, 'use_local': False})
    with pytest.raises(ValueError, match='Either template matching or local alignment'):
        runpy.run_path(str(SCRIPT), run_name='__main__', init_globals={'snakemake': snakemake})
