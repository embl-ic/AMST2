# AMST2

This is a re-implementation of Alignment to Median Smoothed Template (AMST), a stack alignment for FIB-SEM datasets, 
originally published here: 

 - [hennies et al. 2020](https://www.nature.com/articles/s41598-020-58736-7)
 - [original github repo](https://github.com/jhennies/amst)

AMST2 uses the same concept compared to the original AMST workflow, while the implementation is now based on Simple 
Elastix (Simple ITK) and includes a pre-alignment workflow.
To reduce the amount of dependencies as well as to increase robustness of the workflow, the use of SIFT was replaced
by Simple Elastix functionality.

## Installation

The code was developed in Linux. The snakemake-based workflow can cause issues when working in Windows, we recommend using WSL.

Prerequesite: Install conda on your system, e.g. from https://conda-forge.org/miniforge/

### For local execution

```shell
mamba create -n amst2-0.4.0-env -c bioconda -c conda-forge --override-channels python=3.11 "numpy<2.3" nibabel napari pyqt opencv zarr=2 vigra pandas snakemake=8
conda activate amst2-0.4.0-env
pip install SimpleITK-SimpleElastix transforms3d ruamel.yaml pyvsnr pytz tzdata
pip install https://github.com/jhennies/squirrel/archive/refs/tags/0.5.5.tar.gz
pip install https://github.com/jhennies/AMST2/archive/refs/tags/0.4.0.tar.gz
```

### For slurm cluster execution

```shell
mamba create -n amst2-0.4.0-env -c bioconda -c conda-forge --override-channels python=3.11 "numpy<2.3" nibabel napari pyqt opencv zarr=2 vigra pandas snakemake=8 snakemake-executor-plugin-slurm=1
conda activate amst2-0.4.0-env
pip install SimpleITK-SimpleElastix transforms3d ruamel.yaml pyvsnr pytz tzdata
pip install https://github.com/jhennies/squirrel/archive/refs/tags/0.5.5.tar.gz
pip install https://github.com/jhennies/AMST2/archive/refs/tags/0.4.0.tar.gz
```

## Documentation

The command-line interface has two levels:

- **[Individual commands (`amst2-*`)](docs/commands.md):** one operation per invocation, implemented with Snakemake.
- **[Workflow commands (`amst2-wf-*`)](docs/workflows.md):** orchestrate pre-alignment and AMST across several operations.

Additional references:

- [Workflow configuration, stages, inputs, and outputs](docs/workflow_configuration.md)
- [Common CLI options](docs/common_options.md)
- [Example: Fiji SIFT alignment followed by AMST2 NSBS](docs/fiji_sift_alignment.md)

## Quick start

Generate and edit a pre-alignment YAML configuration, then run it:

```bash
amst2-wf-pre_align-get_default_parameter_file -pi /path/to/input.ome.zarr -po /path/to/pre-align
amst2-wf-pre_align-run params_pre_align.yaml
```

Generate and edit an AMST YAML configuration, explicitly pointing it at the raw input and pre-alignment results:

```bash
amst2-wf-amst-get_default_parameter_file \
  -pi /path/to/input.ome.zarr \
  -pp /path/to/pre-align/apply_pre_align/pre-align.ome.zarr \
  -ppt /path/to/pre-align/pre-align.json \
  -po /path/to/amst
amst2-wf-amst-run params_amst.yaml
```

See [Workflow configuration](docs/workflow_configuration.md) for the required pre-alignment paths and parameter sections. Each command supports `--help`.

The original publication and implementation are linked above. A test dataset is available from EMPIAR-10311.
