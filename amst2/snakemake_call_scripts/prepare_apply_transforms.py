"""Prepare globally padded affine transformations before batch materialization."""

import json


if __name__ == '__main__':
    from squirrel.library.affine_matrices import AffineStack
    from squirrel.workflows.transformation import apply_auto_pad_workflow

    run_info = snakemake.params['run_info']
    source = snakemake.input[0]
    target = snakemake.output['transforms']
    shape_path = snakemake.output['shape']

    apply_auto_pad_workflow(
        source,
        target,
        image_stack_path=run_info['input_ome_zarr_filepath'],
        key=run_info['stack_key'],
        pattern=run_info['stack_pattern'],
        verbose=run_info['verbose']
    )

    transforms = AffineStack.read(target)
    shape = transforms.get_metadata('stack_shape')
    if shape is None or len(shape) != 3:
        raise ValueError('Padded transformations must contain 3D stack_shape metadata')

    with open(shape_path, 'w') as handle:
        json.dump([int(value) for value in shape], handle)
