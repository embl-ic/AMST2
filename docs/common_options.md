# Common command options

Individual `amst2-*` commands share arguments supplied by `amst2/library/argument_parsing.py`.
Not every command includes every group; check the relevant `--help` output.

## Execution and batching

| Argument | Default | Meaning |
| --- | --- | --- |
| `--cores` | `1` | Maximum number of available cores; default=1 |
| `--max_cores_per_task` | `16` | Maximum number of cores available to one task; default=16 |
| `--batch_size` | `64` | Number of slices forming one batch; default=64 |
| `--continue_run` | — | Needed to continue a run |
| `--cluster` | — | Use "--cluster slurm" to run on a slurm cluster (only tested on EMBL resources) |
| `--group_name` | — | Name of the group to which the jobs should be submitted on the cluster; only used if --cluster is set |
| `-v`, `--verbose` | — |  |

## Output locations

| Argument | Default | Meaning |
| --- | --- | --- |
| `target_dirpath` | — | Output directory which will contain the cache directory and, by default, also the ome.zarr output |
| `-out-oz-fn`, `--output_ome_zarr_filename` | — | Filename of the ome.zarr output |
| `-out-oz-fp`, `--output_ome_zarr_filepath` | — | Full filepath for the ome.zarr output. Over-writes --ome_zarr_filename |

## OME-Zarr output

| Argument | Default | Meaning |
| --- | --- | --- |
| `--resolution` | `(1.0, 1.0, 1.0)` | Resolution of input data; default=(1., 1., 1.) |
| `--unit` | `pixel` | Unit of input resolution; default="pixel" |
| `--downsample_type` | `Average` | Downsample type used to create the resolution pyramid; default="Average" |
| `--downsample_factors` | `(2, 2, 2)` | Downsample factors used to create the resolution pyramid; default=(2, 2, 2) |
| `--chunk_size` | `[1, 512, 512]` | Chunk size of the ome-zarr dataset; default=[1, 512, 512] |
| `--name` | — | Name of the dataset; defaults to the filename (without ome.zarr extension) |

## Snakemake controls

| Argument | Default | Meaning |
| --- | --- | --- |
| `--dryrun` | — | Snakemake argument |
| `--unlock` | — | Snakemake argument |
| `--rerun_triggers` | `[]` | Snakemake argument; use "--rerun_triggers mtime" to avoid rerunning due to changed params |

## Resource settings

`--mem` and `--runtime` are available on several individual commands; values are passed as `rule_name:value` entries. They are primarily relevant to cluster execution.

## Output and reruns

Individual commands write outputs and Snakemake cache files under their selected output directory. For a workflow rerun with different parameters, use a fresh output directory (or remove the previous step output directory first) to avoid mixing old and new results.
