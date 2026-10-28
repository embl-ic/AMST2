"""Prepare globally padded affine transformations before batch materialization."""

import json


if __name__ == '__main__':
    from squirrel.library.affine_matrices import AffineStack
    from squirrel.library.image import get_bounds_of_stack
    from squirrel.library.io import load_data_handle

    run_info = snakemake.params['run_info']
    source = snakemake.input[0]
    target = snakemake.output['transforms']
    shape_path = snakemake.output['shape']

    transforms = AffineStack.read(source)
    if not transforms.sequenced:
        transforms = transforms.to_sequenced()

    if transforms.has_metadata('bounds'):
        bounds = transforms.get_metadata('bounds')
    else:
        stack, stack_shape = load_data_handle(
            run_info['input_ome_zarr_filepath'],
            key=run_info['stack_key'], pattern=run_info['stack_pattern'])
        bounds = get_bounds_of_stack(
            stack, stack_shape, return_ints=True, z_range=None)

    # Keep the original (untransformed) per-slice image bounds. They remain
    # valid through composition of output-to-input affine transformations.
    transforms.set_metadata('bounds', bounds)
    transforms, shape = transforms.auto_pad(bounds, extra_padding=16)
    transforms.write(target)

    with open(shape_path, 'w') as handle:
        json.dump([int(value) for value in shape], handle)
