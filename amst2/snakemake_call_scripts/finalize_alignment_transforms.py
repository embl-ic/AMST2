"""Assemble elastix batch transformations without generating an image preview."""


def finalize_alignment_transforms(inputs, output, run_info, compute_auto_pad=False):
    from squirrel.library.affine_matrices import AffineStack
    from squirrel.library.io import get_filetype, load_data_handle

    transforms = AffineStack.read_many(inputs, sequence=True)
    assert transforms.sequenced

    if compute_auto_pad:
        transforms, stack_shape = transforms.auto_pad(extra_padding=16)
    elif transforms.has_metadata('stack_shape'):
        stack_shape = transforms.get_metadata('stack_shape')
    else:
        input_path = run_info['input_ome_zarr_filepath']
        if get_filetype(input_path) == 'ome_zarr':
            from squirrel.library.ome_zarr import OMEZarrStore
            store = OMEZarrStore(input_path, mode='r')
            stack_shape = store.root[run_info['stack_key']].shape
        else:
            handle, _ = load_data_handle(
                input_path, key=run_info['stack_key'],
                pattern=run_info['stack_pattern'])
            stack_shape = handle.shape

    if not transforms.has_metadata('stack_shape'):
        transforms.set_metadata('stack_shape', stack_shape)

    if transforms.has_metadata('z_step'):
        transforms = transforms.apply_z_step(max_length=run_info['stack_shape'][0])

    transforms.write(output)


if __name__ == '__main__':
    finalize_alignment_transforms(
        snakemake.input, snakemake.output[0], snakemake.params['run_info'],
        compute_auto_pad=snakemake.params['compute_auto_pad'])
