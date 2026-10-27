# Individual AMST2 commands

These commands are defined by the repository’s `setup.py` console entry points.
Use `COMMAND --help` to inspect all options, including shared Snakemake, output, and OME-Zarr options.

Individual commands execute one Snakemake-based operation. They are building blocks used by the higher-level `amst2-wf-*` workflows.

## `amst2-stack_to_ome_zarr`

Convert an input image stack into OME-Zarr.

**Implementation:** `amst2/conversion.py` → `snk_stack_to_ome_zarr()`

**Usage:**

```bash
amst2-stack_to_ome_zarr --help
```

**Positional arguments**

- `stack_path`: Input h5 container or tif stack

**Command-specific options**

| Option | Default | Description |
| --- | --- | --- |
| `--stack_pattern` | `*.tif` | File pattern for globbing the input stack; default="*.tif" |
| `--stack_key` | — | Path within input h5 file; default=None |
| `--save_bounds` | — | Saves a json file alongside that contains the bounds of the non-zero area of each slice |
| `--crop_xy` | — | Crop an xy-region of the data before conversion |
| `--mem` | — | Cluster job memory amounts for the snakemake rules. For each rule define like so: "rule_name:16000" |
| `--runtime` | — | Cluster job runtimes for the snakemake rules. For each rule define like so: "rule_name:30" |

**Shared options:** See [Common command options](common_options.md) for parameters added by AMST2’s shared argument-parsing helpers.

## `amst2-ome_zarr_to_stack`

Export an OME-Zarr dataset as an image stack.

**Implementation:** `amst2/conversion.py` → `snk_ome_zarr_to_stack()`

**Usage:**

```bash
amst2-ome_zarr_to_stack --help
```

**Positional arguments**

- `ome_zarr_filepath`: Ome-zarr dataset which will be converted to tif stack
- `target_dirpath`: Output directory which will contain the tif slices.
- `stack_name`: Name of the tif stack (will be a subfolder of the target dirpath)

**Command-specific options**

| Option | Default | Description |
| --- | --- | --- |
| `--ome_zarr_key` | `s0` | Path within input ome-zarr dataset; default="s0" |
| `--mem` | — | Cluster job memory amounts for the snakemake rules. For each rule define like so: "rule_name:16000" |
| `--runtime` | — | Cluster job runtimes for the snakemake rules. For each rule define like so: "rule_name:30" |

**Shared options:** See [Common command options](common_options.md) for parameters added by AMST2’s shared argument-parsing helpers.

## `amst2-default_amst_pre_alignment`

Run the legacy/default AMST pre-alignment operation.

**Implementation:** `amst2/stack_alignment.py` → `snk_default_amst_pre_alignment()`

**Usage:**

```bash
amst2-default_amst_pre_alignment --help
```

**Positional arguments**

- `input_ome_zarr_filepath`: Input ome zarr filepath

**Command-specific options**

| Option | Default | Description |
| --- | --- | --- |
| `--local_auto_mask` | — | Generates a mask using image > 0 |
| `--local_gaussian_sigma` | `0.0` | Perform a gaussian smoothing before registration |
| `--no_local_alignment` | — | Use this flag to turn off the local (slice-to-slice) alignment |
| `--template_roi` | — | If supplied template matching will be performed with the here defined template Note: the values for x, y and z are in dataset units! |
| `--tm_search_roi` | — | The template will only be matched in this area. Note: the values for x, y and z are in dataset units! |
| `-cm`, `--combine_median` | `8` | Median smoothing of offsets when combining local and TM |
| `-cs`, `--combine_sigma` | `8.0` | Gaussian smoothing of offsets when combining local and TM |
| `--mem` | — | Cluster job memory amounts for the snakemake rules. For each rule define like so: "rule_name:16000" |
| `--runtime` | — | Cluster job runtimes for the snakemake rules. For each rule define like so: "rule_name:30" |

**Shared options:** See [Common command options](common_options.md) for parameters added by AMST2’s shared argument-parsing helpers.

## `amst2-amst`

Estimate AMST transformations using the median-smoothed template.

**Implementation:** `amst2/amst.py` → `snk_amst()`

**Usage:**

```bash
amst2-amst --help
```

**Positional arguments**

- `input_ome_zarr_filepath`: Input ome zarr filepath

**Command-specific options**

| Option | Default | Description |
| --- | --- | --- |
| `--transform` | `affine` | Transform to use for registration; values=["affine", "bspline"]; default="affine" |
| `--auto_mask_off` | — | Generates a mask using image > 0 |
| `-mr`, `--median_radius` | `7` | Size of median filter for z-median-smoothing step; default=7 |
| `-zm`, `--z_smooth_method` | `median` | Method used for z-smoothing to generate the template; default="median"; values=["median", "gaussian", "mean", "median_non_zero"] |
| `-gs`, `--gaussian_sigma` | `0.0` | Gaussian smoothing before computing registration |
| `-cl`, `--use_clahe` | — | Runs a CLAHE filter before computing registration |
| `-edg`, `--use_edges` | — | Computes edges with a sobel filter for registration |
| `--elastix_parameter_file` | — | Optionally, supply a parameter file for the registration step; default=None |
| `--mem` | — | Cluster job memory amounts for the snakemake rules. For each rule define like so: "rule_name:16000" |
| `--runtime` | — | Cluster job runtimes for the snakemake rules. For each rule define like so: "rule_name:30" |

**Shared options:** See [Common command options](common_options.md) for parameters added by AMST2’s shared argument-parsing helpers.

## `amst2-elastix_stack_alignment`

Estimate slice-wise stack alignment transformations using elastix.

**Implementation:** `amst2/stack_alignment.py` → `snk_elastix_stack_alignment()`

**Usage:**

```bash
amst2-elastix_stack_alignment --help
```

**Positional arguments**

- `input_ome_zarr_filepath`: Input ome zarr filepath

**Command-specific options**

| Option | Default | Description |
| --- | --- | --- |
| `--stack_pattern` | `*.tif` | File pattern for globbing the input stack; default="*.tif" |
| `--stack_key` | — | Path within input h5 file; default=None |
| `--resolution` | — | Resolution of the dataset, needs to be supplied if not using ome.zarr data |
| `--unit` | `micrometers` | Unit of the resolution; default = "micrometers" |
| `--transform` | — | The transformation that is applied to the images; default="translation" |
| `--auto_mask` | `None` | Automatically generates a mask for fixed and moving image; default=None; ["non-zero", "variance"] |
| `--gaussian_sigma` | `0.0` | Perform a gaussian smoothing before registration |
| `--use_edges` | — | Computes edges before registration using a sobel filter |
| `-cl`, `--use_clahe` | — | Runs a CLAHE filter before computing registration |
| `--z_step` | `1` | Uses only every nth data slice; good to determine long range correspondence; default=1 |
| `--average_for_z_step` | — | Use the average of n=z_step slices for fixed and moving images |
| `--auto_pad` | — | Compute the information necessary for auto-padding and apply if requested |
| `--determine_bounds` | — | Determine the bounds of each slice; Does not work with z_step > 1; Implicit for auto_pad |
| `--materialize_output`, `--apply_final` | — | Apply the final transformation and create result ome-zarr |
| `--initialize_offsets_method` | — | Method to solve big jumps: ["xcorr", "init_elx"] "xcorr": Big jumps are detected by the intersection over union of the data in adjacent slices. Correction is performed by cross-correlation "init_elx": Using a highly binned version of the data, initial shifts are performed (grid). The shifted moving image is used as input for elastix registration and the resulting alignment measured by Mutual Information (MI). When MI < mi_thresh is reached or all positions of the grid are tested, the best offset is used to initialize the alignment |
| `--initialize_offsets_kwargs` | `()` | Arguments for the respective initialization method. Syntax: "key:value" defaults for the respective method: "xcorr": iou_thresh:0.5 "init_elx: binning:32 spacing:256 elx_binning:4 elx_max_iters:32 mi_thresh:-0.8 |
| `--max_offset_distance` | — | Maximum allowed offset distance for the final transforms, anything larger will be set to zero; Default=None |
| `--parameter_map` | — | Elastix parameter map file; Overwrites any settings of the elx-parameters below |
| `--elx_number_of_resolutions` | — | Elastix parameter: Number of resolution levels; Default=4 |
| `--elx_number_of_spatial_samples` | — | Elastix parameter: Number of spacial samples; Default=2048 |
| `--elx_maximum_number_of_iterations` | — | Elastix parameter: Maximum number of iterations per resolution level; Default=256 |
| `--elx_microscopy_preset` | — | Loads elastix parameters set for different types of microscopy image data. Currently implemented: None (default): Elastix defaults for respective transform "fibsem": For FIB-SEM datasets "array-tomography": for array tomography datasets |
| `--mem` | — | Cluster job memory amounts for the snakemake rules. For each rule define like so: "rule_name:16000" |
| `--runtime` | — | Cluster job runtimes for the snakemake rules. For each rule define like so: "rule_name:30" |
| `--debug` | — | Set this for saving intermediate files, helpful for debugging |

**Shared options:** See [Common command options](common_options.md) for parameters added by AMST2’s shared argument-parsing helpers.

## `amst2-template_matching_stack_alignment`

Estimate stack alignment by template matching.

**Implementation:** `amst2/stack_alignment.py` → `snk_template_matching_stack_alignment()`

**Usage:**

```bash
amst2-template_matching_stack_alignment --help
```

**Positional arguments**

- `input_ome_zarr_filepath`: Input ome zarr filepath

**Command-specific options**

| Option | Default | Description |
| --- | --- | --- |
| `--template_roi` | — | This defines the template Note: the values for x, y and z are in dataset units! |
| `--tm_search_roi` | — | The template will only be matched in this area. Note: the values for x, y and z are in dataset units! |
| `-cm`, `--combine_median` | `8` | Median smoothing of offsets when combining local and TM |
| `-cs`, `--combine_sigma` | `8.0` | Gaussian smoothing of offsets when combining local and TM |
| `--auto_pad` | — | Compute the information necessary for auto-padding and apply if requested |
| `--determine_bounds` | — | Determine the bounds of each slice; Implicit for auto_pad |
| `--apply_final` | — | Apply the final transformation and create result ome-zarr |
| `--mem` | — | Cluster job memory amounts for the snakemake rules. For each rule define like so: "rule_name:16000" |
| `--runtime` | — | Cluster job runtimes for the snakemake rules. For each rule define like so: "rule_name:30" |

**Shared options:** See [Common command options](common_options.md) for parameters added by AMST2’s shared argument-parsing helpers.

## `amst2-apply_transformation`

Apply one or more affine/Elastix transformation stacks to an input volume and write an OME-Zarr result.

**Implementation:** `amst2/stack_alignment.py` → `snk_apply_transformation()`

**Usage:**

```bash
amst2-apply_transformation --help
```

**Positional arguments**

- `input_ome_zarr_filepath`: Input ome zarr filepath
- `input_transforms_filepaths` (`nargs=+`): Filepaths to transformations file (*.json) or directory

**Command-specific options**

| Option | Default | Description |
| --- | --- | --- |
| `--stack_pattern` | `*.tif` | File pattern for globbing the input stack; default="*.tif" |
| `--stack_key` | — | Path within input h5 file; default=None |
| `--resolution` | — | Resolution of the dataset, needs to be supplied if not using ome.zarr data |
| `--unit` | `micrometers` | Unit of the resolution; default = "micrometers" |
| `--no_autopad` | — | Switches off auto-padding |
| `--resample_interpolator` | — | Select the interpolator; Default = None; Examples: "none": evaluates to None -> Default "nearest" / "FinalNearestNeighborInterpolator": nearest interpolation |
| `--mem` | — | Cluster job memory amounts for the snakemake rules. For each rule define like so: "rule_name:16000" |
| `--runtime` | — | Cluster job runtimes for the snakemake rules. For each rule define like so: "rule_name:30" |

**Shared options:** See [Common command options](common_options.md) for parameters added by AMST2’s shared argument-parsing helpers.

## `amst2-normalize_stack`

Normalize intensity across an image stack.

**Implementation:** `amst2/stack_operations.py` → `snk_normalize_stack()`

**Usage:**

```bash
amst2-normalize_stack --help
```

**Positional arguments**

- `input_ome_zarr_filepath`: Input ome zarr filepath

**Command-specific options**

| Option | Default | Description |
| --- | --- | --- |
| `--dilate_background` | `0` | Dilate the background before computing data quantiles. default=0 (off) |
| `--quantiles` | `(0.1, 0.9)` | Lower and upper quantile of the gray value spectrum that is used to normalize;default=(0.1, 0.9) |
| `--anchors` | `(0.2, 0.8)` | The lower and upper quantiles of the input gray value spectrum are transferred to these relative values; default=(0.2, 0.8) |
| `--mem` | — | Cluster job memory amounts for the snakemake rules. For each rule define like so: "rule_name:16000" |
| `--runtime` | — | Cluster job runtimes for the snakemake rules. For each rule define like so: "rule_name:30" |

**Shared options:** See [Common command options](common_options.md) for parameters added by AMST2’s shared argument-parsing helpers.
