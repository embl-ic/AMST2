# Pre-alignment and AMST

This workflow contains of the following basic steps for local execution:

 1. Conversion to ome.zarr (optional)
 2. Slice-by-slice (sbs) stack alignment with Simple Elastix
 3. Long-range nth-slice-by-slice (nsbs) alignment with Simple Elastix
 4. Pre-alignment by combining sbs (step 2) and nsbs stack alignment (step 3)
 5. Alignment to median smoothed template (AMST)

## Pre-requesites

Make sure the package is properly installed (see [README.md](../README.md)) 
and the AMST2 conda environment is active.

If this is the case, the following commands should be available and yield their respective help output:

```
amst2-wf-nsbs_pre_align_get_default_parameter_file -h
amst2-wf-nsbs_pre_align-run -h
amst2-wf-amst-get_default_parameter_file -h
amst2-wf-amst-run -h
```

## Pre-alignment (Steps 1 to 4)

Set up an output directory and cd into it

```
mkdir pre-align-out-dir
cd pre-align-out-dir
```

Generate a pre-alignment parameter file

```
amst2-wf-nsbs_pre_align-get_default_parameter_file --param_input_dirpath /path/to/dataset --param_output_dirpath .
```

Replace ```/path/to/dataset``` with the location of the input data.

This will create the parameter file called "params_pre_align.yaml" which contains the proper input and output directories

You now need to open the parameter file and modify parameters such as resolution and compute resources:

```
  resolution: [ 0.008, 0.005, 0.005 ] 
  cores: 16  # Adjust as necessary!
```

Make sure ```cores >= batch_size >= max_cores_per_task```

If you require a tif stack as output, set the following:

```
pre_align_to_tif_stack:
  active: true
```

Run the pre-alignment:

```
amst2-wf-nsbs_pre_align-run params_pre_align.yaml
```

Once it's done, you can check the success by one of the following ways:

 1. If activated, load the full-sized tif stack result stored in ```pre_align_to_tif_stack/nsbs-pre-align``` into Fiji (preferentially as virtual stack)
 2. Load the full-sized ome.zarr result ```hela-1-nsbs/apply_pre_align/nsbs-pre-align.ome.zarr``` with an ome.zarr viewer (e.g. BigDataViewer in Fiji)

## AMST (step 5)

Set up an output directory and cd into it (we are currently in the pre-alignment directory -> see above)

```
cd ..
mkdir amst-out-dir
cd amst-out-dir
```

As for the pre-alignment, generate a parameter file and modify it as required (compute resources, resolution of the dataset, etc.)

```
amst2-wf-amst-get_default_parameter_file --pre_align_yaml params_pre_align.yaml --param_output_dirpath .
```

This will create the parameter file called "params_amst.yaml" where all input directory paths are properly set, as this 
information can be derived from the pre alignment yaml file. 

Again, modify compute resources:

```
  cores: 16  # Adjust as necessary!
```

Amd make sure ```cores >= batch_size >= max_cores_per_task```

Run AMST:

```
amst2-wf-amst-run params_amst.yaml
```

Now you can check the result:
 1. If activated, full size tif-stack in ```hela-1-amst/amst_to_tif_stack/amst/```
 2. ome.zarr in ```hela-1-amst/apply_amst/amst.ome.zarr```
