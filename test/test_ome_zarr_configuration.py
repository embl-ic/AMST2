"""Regression checks for AMST2 0.4.0 OME-Zarr batch configuration.

Run with squirrel 0.5.5 installed for the store-level checks.
"""
import ast
from pathlib import Path

import pytest


AMST2 = Path(__file__).resolve().parents[1] / "amst2"
CONFIG_FILES = ["conversion.py", "stack_operations.py", "stack_alignment.py"]


def _chunk_config_blocks(filename):
    """Extract the actual production chunk computation, not a copied formula."""
    tree = ast.parse((AMST2 / filename).read_text())
    blocks = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = node.body
        for idx, statement in enumerate(body):
            if (isinstance(statement, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "chunk_size" for t in statement.targets)
                    and isinstance(statement.value, ast.List)
                    and len(statement.value.elts) == 1):
                # Locate the exact level-zero modulo assertion, which may
                # have other assertions between it and the chunk assignment.
                preceding = [n for n in body[:idx] if isinstance(n, ast.Assert)
                             and "batch_size" in ast.unparse(n)
                             and "chunk_size" in ast.unparse(n)]
                if not preceding:
                    continue
                after = body[idx + 1:idx + 4]
                if not any(isinstance(x, ast.For) for x in after):
                    continue
                nodes = [preceding[-1], statement] + after
                snippet = ast.Module(body=nodes, type_ignores=[])
                ast.fix_missing_locations(snippet)
                blocks.append(compile(snippet, str(AMST2 / filename), "exec"))
    return blocks


@pytest.mark.parametrize("filename", CONFIG_FILES)
def test_chunk_configurations_for_supported_batches(filename):
    print(f"Testing AMST2 OME-Zarr chunk configuration for {filename} ...")
    blocks = _chunk_config_blocks(filename)
    assert blocks, f"No production chunk calculation found in {filename}"
    for batch_size in (4, 8, 16, 32, 64):
        for code in blocks:
            args = {"chunk_size": [1, 32, 32], "downsample_factors": [2, 2, 2]}
            scope = {"common_args": {"batch_size": batch_size}, "ome_zarr_args": args}
            exec(code, scope)
            assert len(args["chunk_size"]) == 4
            assert all(len(chunk) == 3 and all(v > 0 for v in chunk) for chunk in args["chunk_size"])
            assert args["chunk_size"][0] == [1, 32, 32]


@pytest.mark.parametrize("filename", CONFIG_FILES)
def test_incompatible_level_zero_chunk_is_rejected(filename):
    print(f"Testing AMST2 rejects incompatible level-zero chunks in {filename} ...")
    for code in _chunk_config_blocks(filename):
        args = {"chunk_size": [3, 32, 32], "downsample_factors": [2, 2]}
        with pytest.raises(AssertionError):
            exec(code, {"common_args": {"batch_size": 8}, "ome_zarr_args": args})


def test_generated_chunks_and_batch_boundaries_against_squirrel(tmp_path):
    print("Testing AMST2 batch boundaries against squirrel pyramid alignment ...")
    pytest.importorskip("zarr")
    from squirrel.library.ome_zarr import OMEZarrStore

    code = _chunk_config_blocks("conversion.py")[0]
    for batch_size in (4, 8, 16):
        args = {"chunk_size": [1, 16, 16], "downsample_factors": [2, 2, 2]}
        exec(code, {"common_args": {"batch_size": batch_size}, "ome_zarr_args": args})
        depth = batch_size * 2 + 3  # deliberately partial final batch
        store = OMEZarrStore.create(
            str(tmp_path / f"batch_{batch_size}.ome.zarr"),
            shape=(depth, 32, 32), dtype="uint16", chunks=args["chunk_size"],
            shards=None, downsample_factors=[(2, 2, 2)] * 3,
            ome_version="0.4", zarr_format=2, overwrite=False,
        )
        for start in range(0, depth, batch_size):
            length = min(batch_size, depth - start)
            store.check_pyramid_alignment(0, (start, 0, 0), (length, 32, 32))


def test_conversion_append_signature_and_write_checks():
    print("Testing squirrel conversion append API and AMST2 write alignment flags ...")
    tree = ast.parse((AMST2 / "snakemake_call_scripts/batch_to_ome_zarr.py").read_text())
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name) and n.func.id == "stack_to_ome_zarr_workflow"]
    assert len(calls) == 1
    assert any(k.arg == "append" and isinstance(k.value, ast.Constant) and k.value.value is True
               for k in calls[0].keywords)
    pytest.importorskip("squirrel")
    import inspect
    from squirrel.workflows.convert import stack_to_ome_zarr_workflow
    assert "append" in inspect.signature(stack_to_ome_zarr_workflow).parameters
    # Note: append=True only establishes API compatibility, not concurrency safety.
