# Example workflow: Fiji SIFT followed by AMST2 NSBS pre-alignment

This example uses Fiji’s **Linear Stack Alignment with SIFT** for initial slice-by-slice registration and AMST2’s **NSBS** stage for subsequent refinement. **Do not run AMST2 SBS in this configuration:** Fiji SIFT already performs that role. AMST2 uses its generic imported-affine-stack interface, so no Fiji-specific registration code is needed.

## 1. Register in Fiji and save the transformation log

1. Open Fiji.
2. Load the image stack into memory, for example by dragging and dropping the directory `path/to/input_tiffs` into Fiji. Make sure the images form a single ordered stack.
3. If the Log window is already open and contains previous output, clear it using **Edit → Clear** in that window. If needed, open the Log window via **Window → Log**.
4. Choose **Plugins → Registration → Linear Stack Alignment with SIFT** and set:
   - **Expected transformation:** `Translation`
   - **Interpolate:** enabled
   - **Show info:** optional (useful for diagnosing slices that fail to register)
   - **Show transformation matrix:** enabled (**required** for the conversion below)
   - Leave other settings at their defaults.
5. Inspect the registered stack for abrupt jumps or failed slice alignments. If the result is unsatisfactory, resolve those problems before proceeding.
6. In the Fiji Log window, select **File → Save As…** and save the log as, for example, `path/to/fiji_sift/transforms.txt`.

Keep the original image stack: the Fiji-registered display is for inspection; AMST2 will apply the imported transforms to the original input data.

## 2. Convert the Fiji log to a squirrel affine stack

With squirrel installed and its CLI available, run:

```bash
sq-fiji-sift_log_to_affine_stack \
    path/to/fiji_sift/transforms.txt \
    path/to/fiji_sift/transforms.json
```

The first positional argument is the Fiji log file and the second is the output JSON file. With **Translation** selected in Fiji, no `--pivot` argument is needed. Ensure the resulting stack corresponds to the same slice count and ordering as the original input: AMST2 validates imported transforms against the input volume.

## 3. Generate AMST2 pre-alignment parameters

```bash
amst2-wf-pre_align-get_default_parameter_file \
    --fiji path/to/fiji_sift/transforms.json \
    -pi path/to/input_tiffs \
    -po path/to/pre_align_output \
    -fp params_pre_align_fiji.yaml
```

The `--fiji` preset generates the standard YAML with these settings:

```yaml
workflow:
  pre_existing_transforms: path/to/fiji_sift/transforms.json
  run_sbs: false
  run_nsbs: true
```

Review the generated YAML before running. For a directory of TIFF files, verify `general.stack_pattern` matches the filenames (the default is `*.tif`); adjust dataset key, resolution, compute resources, and other options for your data. Paths in this example are relative to the directory from which the commands are run.

The `--fiji` option is a configuration shortcut, **not** a separate Fiji-specific AMST2 pipeline. Equivalent settings can also be supplied via `--params` or by editing the YAML. Explicit `--params` values take precedence over preset values.

## 4. Run pre-alignment

```bash
amst2-wf-pre_align-run params_pre_align_fiji.yaml
```

AMST2 uses the imported affine transforms first, then runs NSBS, composes the transformations, and applies them to the original image volume. With the example output directory, the principal results are:

- `path/to/pre_align_output/pre-align.json` — composed pre-alignment affine stack.
- `path/to/pre_align_output/apply_pre_align/pre-align.ome.zarr` — pre-aligned image volume.

Inspect the result before proceeding to AMST registration. For reruns with changed parameters or a changed Fiji transform file, use a **fresh pre-alignment output directory**; AMST2 tracks the run configuration and imported transforms to prevent accidental reuse of incompatible results.

See [Workflow configuration](workflow_configuration.md) for additional parameters and [Workflow commands](workflows.md) for the complete CLI reference.
