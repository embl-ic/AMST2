import numpy as np


if __name__ == '__main__':

    batch_idx = int(snakemake.wildcards['idx'])
    output_ome_zarr_filepath = snakemake.input[0]

    output = snakemake.output[0]
    run_info = snakemake.params['run_info']
    n_threads = snakemake.threads
    verbose = run_info['verbose']

    print(f'batch_idx = {batch_idx}')
    print(f'output = {output}')
    print(f'run_info = {run_info}')
    print(f'n_threads = {n_threads}')

    z_range = [batch_idx, batch_idx + run_info['batch_size']]

    print(f'z_range = {z_range}')

    from squirrel.library.ome_zarr import OMEZarrStore
    input_ome_zarr_filepath = run_info['input_ome_zarr_filepath']
    input_ome_zarr_dataseth = OMEZarrStore(input_ome_zarr_filepath, mode='r').dataset(0)

    stack_shape = input_ome_zarr_dataseth.shape
    print(f'stack_shape = {stack_shape}')
    print(f'output_shape = {OMEZarrStore(output_ome_zarr_filepath, mode="r").shape(0)}')

    # Serialize and apply the transformations
    from squirrel.library.normalization import normalize_slices
    print(f'z_range = {z_range}')
    result_stack = normalize_slices(
        input_ome_zarr_dataseth,
        dilate_background=run_info['dilate_background'],
        quantiles=run_info['quantiles'],
        anchors=run_info['anchors'],
        z_range=z_range,
        n_workers=n_threads
    )

    output_store = OMEZarrStore(output_ome_zarr_filepath, mode='a')
    output_store.write(
        level=0,
        position=[batch_idx, 0, 0],
        data=result_stack,
        update_pyramid=True,
        check_pyramid_alignment=True,
        require_empty=False
    )

    open(output, 'w').close()
