# Workflow configuration

The `amst2-wf-*` commands accept YAML parameter files. Generate a starting file with the corresponding `get_default_parameter_file` command and edit it before execution. The packaged examples are `amst2/parameter_files/params-nsbs-pre-align-local.yaml` and `amst2/parameter_files/params-amst-bspline-local.yaml`.

## Pre-alignment

```bash
amst2-wf-pre_align-get_default_parameter_file -pi /path/to/input.ome.zarr -po /path/to/pre-align
amst2-wf-pre_align-run params_pre_align.yaml
```

The principal YAML sections are:

| Section | Purpose |
| --- | --- |
| `general` | Input/output paths, dataset key or filename pattern, physical resolution/unit, padding, cores, and batch sizing. |
| `stack_to_ome_zarr` | Optional conversion of source image data to OME-Zarr. |
| `workflow` | Enable SBS and/or NSBS; optionally supply `pre_existing_transforms` as a JSON affine stack. |
| `sbs_alignment` | Local slice-by-slice alignment options, including masks and elastix initialization. |
| `nsbs_alignment` | Long-range alignment options, including `z_step`. |
| `apply_pre_align` | Final application of the composed pre-alignment transforms. |
| `pre_align_to_tif_stack` | Optional export of the final pre-aligned volume as TIFF. |

The `workflow` section supports `run_sbs`, `run_nsbs` (both default to `true` when omitted), and `pre_existing_transforms` (default `null`). At least one of these stages must be active. Enabled stages run in this order: imported transforms → SBS → NSBS. The composed affine stack maps output coordinates to input coordinates. An imported stack must have one finite 2D affine transform per input Z-slice, with compatible shape metadata when present.

The workflow writes `pre-align.json` and materializes the final image at `apply_pre_align/pre-align.ome.zarr` beneath `general.output_dirpath`. Intermediate volumes are materialized only when needed by subsequent stages. The `.amst2/run-identity.json` manifest detects changes to effective configuration and imported transforms; use a fresh output directory when those change.

For a worked example that imports Fiji SIFT transformations, skips SBS, and runs NSBS, see [Fiji SIFT alignment](fiji_sift_alignment.md).

The runner supports `--dryrun` and `--verbose`. The generator supports `-p`/`--params` overrides; run its `--help` for exact syntax and other generator options.

## AMST

```bash
amst2-wf-amst-get_default_parameter_file \
  -pi /path/to/raw.ome.zarr \
  -pp /path/to/pre-align/apply_pre_align/pre-align.ome.zarr \
  -ppt /path/to/pre-align/pre-align.json \
  -po /path/to/amst-output
amst2-wf-amst-run params_amst.yaml
```

| Section | Purpose |
| --- | --- |
| `general` | Output directory, raw input, pre-aligned image, pre-alignment transform stack, stack key, cores, and batch sizing. |
| `amst` | AMST registration settings (`transform`, median radius, elastix parameters, and preprocessing). |
| `apply_amst` | Apply the combined pre-alignment and AMST transformations to the raw input. |
| `amst_to_tif_stack` | Optional TIFF export of the final result. |

For a separate AMST output directory, explicitly set `general.input_dirpath`, `general.pre_align_dirpath`, and `general.pre_align_transforms` to the raw volume, pre-aligned volume, and pre-alignment JSON respectively. `amst.transform` selects `affine` or `bspline`; B-spline transforms are represented by elastix transformation files rather than a single affine JSON stack.

The high-level workflow runs registration and then transformation application. `amst2-wf-amst-run` supports `--verbose`.

## Execution model

Both high-level workflows orchestrate lower-level `amst2-*` commands, each of which executes Snakemake rules. `general.cores`, `general.batch_size`, and `general.max_cores_per_task` control resource usage. The workflow layer does not replace Snakemake scheduling.

When changing parameters between runs, remove the affected step's previous output directory or use a fresh target directory. The pre-alignment run identity check additionally prevents reusing a directory with conflicting inputs/configuration.

## Related documentation

- [Individual commands](commands.md)
- [Workflow commands](workflows.md)
- [Shared command options](common_options.md)
