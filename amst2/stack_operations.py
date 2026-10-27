
import os


def snk_normalize_stack():

    # Argument parsing -----------------------------------

    import argparse
    from amst2.library.argument_parsing import (
        add_common_arguments_to_parser,
        add_output_locations_to_parser, output_locations_to_dict,
        add_ome_zarr_arguments_to_parser,
        add_snakemake_arguments_to_parser, args_to_snakemake_arguments,
        args_to_dict,
        write_run_json
    )

    parser = argparse.ArgumentParser(
        description='Slice-wise normalization of a stack of images',
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument('input_ome_zarr_filepath', type=str,
                        help='Input ome zarr filepath')
    parser.add_argument('--dilate_background', type=int, default=0,
                        help='Dilate the background before computing data quantiles. default=0 (off)')
    parser.add_argument('--quantiles', type=float, nargs=2, default=(0.1, 0.9),
                        help='Lower and upper quantile of the gray value spectrum that is used to normalize;'
                             'default=(0.1, 0.9)')
    parser.add_argument('--anchors', type=float, nargs=2, default=(0.2, 0.8),
                        help='The lower and upper quantiles of the input gray value spectrum are transferred to these '
                             'relative values; default=(0.2, 0.8)')
    parser.add_argument('--mem', type=str, nargs='+', default=None,
                        help='Cluster job memory amounts for the snakemake rules.\n'
                             'For each rule define like so:\n'
                             '"rule_name:16000"')
    parser.add_argument('--runtime', type=str, nargs='+', default=None,
                        help='Cluster job runtimes for the snakemake rules. \n'
                             'For each rule define like so:\n'
                             '"rule_name:30"')

    common_arg_fields = add_common_arguments_to_parser(parser)
    add_output_locations_to_parser(parser)
    ome_zarr_fields = add_ome_zarr_arguments_to_parser(parser, omit=['resolution'])
    add_snakemake_arguments_to_parser(parser)

    args = parser.parse_args()

    input_ome_zarr_filepath = os.path.abspath(args.input_ome_zarr_filepath)
    dilate_background = args.dilate_background
    quantiles = args.quantiles
    anchors = args.anchors
    mem = args.mem
    runtime = args.runtime

    common_args = args_to_dict(args, common_arg_fields)
    output_location_args = output_locations_to_dict(
        args,
        workflow_name='normalize_stack',
        fallback_output_name=f'{input_ome_zarr_filepath.replace(".ome.zarr", "-norm")}.ome.zarr'
    )
    ome_zarr_args = args_to_dict(args, ome_zarr_fields)

    # Generate run.json ----------------------------------

    from squirrel.library.io import load_data_handle
    from squirrel.library.ome_zarr import OMEZarrStore
    data_h, shape_h = load_data_handle(input_ome_zarr_filepath, key='s0', pattern=None)
    batch_ids = [x for x in range(0, shape_h[0], common_args['batch_size'])]
    ome_zarr_h = OMEZarrStore(input_ome_zarr_filepath, mode='r')
    resolution = ome_zarr_h.metadata.scale(0)
    unit = ome_zarr_h.metadata.units
    dtype = str(data_h.dtype)

    assert common_args['batch_size'] in [4, 8, 16, 32, 64], 'Only allowing batch sizes of [4, 8, 16, 32, 64]!'
    assert common_args['batch_size'] % ome_zarr_args['chunk_size'][0] == 0
    chunk_size = [ome_zarr_args['chunk_size']]
    downsample_factors = ome_zarr_args['downsample_factors']
    for ds_factor in downsample_factors:
        z_chunk = int(chunk_size[-1][0] / ds_factor)
        if z_chunk == 0:
            z_chunk = 1
        chunk_size.append([z_chunk, chunk_size[0][1], chunk_size[0][1]])
    ome_zarr_args['chunk_size'] = chunk_size

    src_dirpath = os.path.dirname(os.path.realpath(__file__))

    run_info = dict(
        input_ome_zarr_filepath=input_ome_zarr_filepath,
        batch_ids=batch_ids,
        stack_shape=shape_h,
        src_dirpath=src_dirpath,
        output_dtype=dtype,
        resolution=resolution,
        unit=unit,
        dtype=dtype,
        dilate_background=dilate_background,
        quantiles=quantiles,
        anchors=anchors,
        **output_location_args,
        **common_args,
        **ome_zarr_args
    )

    write_run_json(run_info, output_location_args)

    # Snakemake stuff ------------------------------------

    from snakemake.cli import parse_args, args_to_api
    from pathlib import Path

    parser, sn_args = parse_args({})
    args_to_snakemake_arguments(args, sn_args, output_location_args=output_location_args)
    sn_args.snakefile = Path(os.path.join(src_dirpath, 'snakemake_workflows/normalize_stack.snk'))
    sn_args.set_threads = dict(
        normalize_stack=min(args.batch_size, args.cores, args.max_cores_per_task)
    )

    if args.cluster is not None:

        from amst2.cluster.slurm import get_cluster_settings
        from amst2.cluster.general import set_resources

        set_resources(
            sn_args,
            [
                'create_ome_zarr',
                'normalize_stack'
            ],
            [1024, 16000],
            [5, 30],
            mem_args=mem,
            runtime_args=runtime
        )

        sn_args = get_cluster_settings(sn_args, os.path.join(src_dirpath, 'cluster', 'embl.json'), group_name=common_args['group_name'])

    args_to_api(sn_args, parser)

