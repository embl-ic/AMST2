import numpy as np


if __name__ == '__main__':

    batch_idx = int(snakemake.wildcards['idx'])
    output_ome_zarr_filepath = snakemake.input[0]
    transformations_filepath = snakemake.input[1:]

    output = snakemake.output[0]
    run_info = snakemake.params['run_info']
    n_threads = snakemake.threads
    verbose = run_info['verbose']

    input_ome_zarr_filepath = run_info['input_ome_zarr_filepath']

    print(f'batch_idx = {batch_idx}')
    print(f'output = {output}')
    print(f'run_info = {run_info}')
    print(f'n_threads = {n_threads}')

    z_range = [batch_idx, batch_idx + run_info['batch_size']]

    print(f'z_range = {z_range}')

    resample_interpolator = run_info['resample_interpolator'] if 'resample_interpolator' in run_info else None

    from squirrel.workflows.elastix import apply_multi_step_stack_alignment_workflow

    result_stack = apply_multi_step_stack_alignment_workflow(
        input_ome_zarr_filepath,
        transformations_filepath,
        key=run_info['stack_key'],
        pattern=run_info['stack_pattern'],
        auto_pad=False,
        z_range=z_range,
        start_transform_id=z_range[0],
        resample_interpolator=resample_interpolator,
        n_workers=n_threads,
        quiet=False,
        assert_sequenced=False,
        verbose=verbose
    )

    print(f'result_stack.shape = {result_stack.shape}')

    from squirrel.library.ome_zarr import OMEZarrStore
    oz = OMEZarrStore(path=output_ome_zarr_filepath, mode='a')

    oz_shape = oz.shape(0)

    print(f'output dataset shape = {oz_shape}')
    from squirrel.library.volume import pad_volume
    result_stack = pad_volume(result_stack, oz_shape, axes=[1, 2])
    print(f'result_stack.shape (adjusted) = {result_stack.shape}')

    oz.write(
        0, [batch_idx, 0, 0],
        data=result_stack,
        update_pyramid=True,
        require_empty=False,
        check_alignment=False,
        check_pyramid_alignment=True,
    )

    open(output, 'w').close()
