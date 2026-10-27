# AMST2 workflow commands

These commands are defined by the repository’s `setup.py` console entry points.
Use `COMMAND --help` to inspect all options, including shared Snakemake, output, and OME-Zarr options.

Workflow commands orchestrate several individual steps using YAML configuration files. The workflow layer does not replace Snakemake; each step still uses Snakemake.

## `amst2-wf-pre_align-run`

Run the configurable pre-alignment sequence.

**Implementation:** `amst2/workflows/pre_align.py` → `pre_align()`

**Usage:**

```bash
amst2-wf-pre_align-run --help
```

**Positional arguments**

- `parameter_yaml`: Parameter file. Run `amst2-wf-pre_align-get_default_parameter_file` to generate it.

**Command-specific options**

| Option | Default | Description |
| --- | --- | --- |
| `-d`, `--dryrun` | — | Dry-run: Displays the amst2 commands that would be run. |
| `-v`, `--verbose` | — |  |

**Configuration:** See [Workflow configuration](workflow_configuration.md) for the YAML structure and execution stages.

## `amst2-wf-pre_align-get_default_parameter_file`

Create a pre-alignment YAML parameter file.

**Implementation:** `amst2/workflows/pre_align.py` → `get_default_parameter_file()`

**Usage:**

```bash
amst2-wf-pre_align-get_default_parameter_file --help
```

**Command-specific options**

| Option | Default | Description |
| --- | --- | --- |
| `-fp`, `--output_filepath` | — | Filepath of the parameter file. By default it is created in the current directory |
| `-pi`, `--param_input_dirpath` | — | The parameter "general:input_dirpath" will be pre-set to this value |
| `-psk`, `--param_stack_key` | — | Stack key of the input dataset (relevant for h5, n5 or ome.zarr); Defaults to "s0" |
| `-psp`, `--param_stack_pattern` | — | Stack pattern of the input dataset (relevant for tif stack); Defaults to "*.tif" |
| `-po`, `--param_output_dirpath` | — | The parameter "general:output_dirpath" will be pre-set to this value |
| `-piom`, `--param_initialize_offset_method` | — | Specify the method used for initialization of offsets; possible values = ["none", "init_xcorr", "init_elx"]; default="init_elx" Note: This will additionally also adjust the following parameters: - sbs_alignment:elx_number_of_resolutions - sbs_alignment:elx_maximum_number_of_iterations |
| `-p`, `--params` | — | Specify any parameter and its value in this format: --params group:parameter_name:value Examples: --params stack_to_ome_zarr:active:true general:cores:32 -> enables input ome zarr conversion and sets the number of compute cores to 32 --params general:resolution:[0.02,0.02,0.02] -> Sets resolution to 0.02 isotropic Note: One Item consisting of group:parameter_name:value must not contain any spaces! Also note: You can generate any entry like this - also ones that have no effect! The idea of having this input argument is to make a workflow fully scriptable without the requirement for manually adjusting the parameter file. |
| `--fiji AFFINE_JSON` | — | Preset for imported Fiji SIFT (or other affine) transforms: set `workflow.pre_existing_transforms`, disable SBS, enable NSBS. Explicit `--params` can override the preset. |
| `--slurm` | — | Creates the parameter file for a slurm cluster; Note that the compute settings may require adjustment |
| `--estimate_crop_xy` | — | Estimates how to optimally crop the data to reduce slice size. Note that enabling this requires conversion of the input to ome.zarr |
| `-v`, `--verbose` | — |  |

**Configuration:** The generated YAML can be edited before running the corresponding workflow; see [Workflow configuration](workflow_configuration.md).

## `amst2-wf-amst-get_default_parameter_file`

Create an AMST YAML parameter file.

**Implementation:** `amst2/workflows/amst.py` → `get_default_parameter_file()`

**Usage:**

```bash
amst2-wf-amst-get_default_parameter_file --help
```

**Command-specific options**

| Option | Default | Description |
| --- | --- | --- |
| `-fp`, `--output_filepath` | — | Filepath of the parameter file. By default it is created in the current directory |
| `-pay`, `--pre_align_yaml` | — | If the pre-alignment was performed with amst2-wf-pre_align-run, set this argument. All input filepaths will be properly set. |
| `-pi`, `--param_input_dirpath` | — | The parameter "general:input_dirpath" will be pre-set to this value |
| `-po`, `--param_output_dirpath` | — | The parameter "general:output_dirpath" will be pre-set to this value |
| `-pp`, `--param_pre_align_dirpath` | — | The parameter "general:pre_align_dirpath" will be pre-set to this value |
| `-ppt`, `--param_pre_align_transforms` | — | The parameter "general:pre_align_transforms" will be pre-set to this value |
| `-p`, `--params` | — | Specify any parameter and its value in this format: --params group:parameter_name:value Examples: --params stack_to_ome_zarr:active:true general:cores:32 -> enables input ome zarr conversion and sets the number of compute cores to 32 --params general:resolution:[0.02,0.02,0.02] -> Sets resolution to 0.02 isotropic Note: One Item consisting of group:parameter_name:value must not contain any spaces! Also note: You can generate any entry like this - also ones that have no effect! The idea of having this input argument is to make a workflow fully scriptable without the requirement for manually adjusting the parameter file. |
| `--slurm` | — | Creates the parameter file for a slurm cluster; Note that the compute settings may require adjustment |
| `-v`, `--verbose` | — |  |

**Configuration:** The generated YAML can be edited before running the corresponding workflow; see [Workflow configuration](workflow_configuration.md).

## `amst2-wf-amst-run`

Run the AMST registration and transformation-application sequence.

**Implementation:** `amst2/workflows/amst.py` → `amst()`

**Usage:**

```bash
amst2-wf-amst-run --help
```

**Positional arguments**

- `parameter_yaml`:

**Command-specific options**

| Option | Default | Description |
| --- | --- | --- |
| `-v`, `--verbose` | — |  |

**Configuration:** See [Workflow configuration](workflow_configuration.md) for the YAML structure and execution stages.
