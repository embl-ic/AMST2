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
mamba create -n amst2-0.3.22-env -c bioconda -c conda-forge --override-channels python=3.11 "numpy<2.3" nibabel napari pyqt opencv zarr=2 vigra pandas snakemake=8
conda activate amst2-0.3.22-env
pip install SimpleITK-SimpleElastix transforms3d ruamel.yaml pyvsnr pytz tzdata
pip install https://github.com/jhennies/squirrel/archive/refs/tags/0.5.5.tar.gz
pip install https://github.com/jhennies/AMST2/archive/refs/tags/0.4.0.tar.gz
```

### For slurm cluster execution

```shell
mamba create -n amst2-0.3.22-env -c bioconda -c conda-forge --override-channels python=3.11 "numpy<2.3" nibabel napari pyqt opencv zarr=2 vigra pandas snakemake=8 snakemake-executor-plugin-slurm=1
conda activate amst2-0.3.22-env
pip install SimpleITK-SimpleElastix transforms3d ruamel.yaml pyvsnr pytz tzdata
pip install https://github.com/jhennies/squirrel/archive/refs/tags/0.5.5.tar.gz
pip install https://github.com/jhennies/AMST2/archive/refs/tags/0.4.0.tar.gz
```

## Usage

To test the installation, we recommend using this dataset: https://www.ebi.ac.uk/empiar/EMPIAR-10311/

I have set up a suitable subset of the EMPIAR-10311 dataset on my owncloud which you can test on in a new directory like so:

```shell
wget https://oc.embl.de/index.php/s/RhlFWP3JGnuoIAM/download
unzip download
rm download
```

Run the test alignment (remove the "--slurm" line if you are running locally):

```shell
amst2-wf-nsbs_pre_align-get_default_parameter_file \
  -pi hela-test-dataset/ \
  -po pre-align \
  -p general:resolution:[0.008,0.005,0.005] \
     general:batch_size:8 \
     general:max_cores_per_task:8 \
     nsbs_alignment:batch_size:16 \
     pre_align_to_tif_stack:active:true \
  --slurm \
  --estimate_crop_xy
  
amst2-wf-nsbs_pre_align-run params_pre_align.yaml
```
 
Also check out the most recent example for [pre alignment and AMST](examples/simple_pre_alignment_and_amst.md)


