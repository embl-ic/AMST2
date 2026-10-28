
def add_common_arguments_to_parser(parser):

    parser.add_argument('--cores', type=int, default=1,
                        help='Maximum number of available cores; default=1')
    parser.add_argument('--max_cores_per_task', type=int, default=16,
                        help='Maximum number of cores available to one task; default=16')
    parser.add_argument('--batch_size', type=int, default=64,
                        help='Number of slices forming one batch; default=64')
    parser.add_argument('--continue_run', action='store_true',
                        help='Needed to continue a run')
    parser.add_argument('--cluster', type=str, default=None,
                        help='Use "--cluster slurm" to run on a slurm cluster (only tested on EMBL resources)')
    parser.add_argument('--group_name', type=str, default=None,
                        help='Name of the group to which the jobs should be submitted on the cluster; only used if --cluster is set')
    parser.add_argument('-v', '--verbose', action='store_true')

    return ['cores', 'max_cores_per_task', 'batch_size', 'continue_run', 'cluster', 'group_name', 'verbose']


def add_output_locations_to_parser(parser):

    parser.add_argument('target_dirpath', type=str,
                        help='Output directory which will contain the cache directory and, by default, also the '
                             'ome.zarr output')
    parser.add_argument('-out-oz-fn', '--output_ome_zarr_filename', type=str, default=None,
                        help='Filename of the ome.zarr output')
    parser.add_argument('-out-oz-fp', '--output_ome_zarr_filepath', type=str, default=None,
                        help='Full filepath for the ome.zarr output. Over-writes --ome_zarr_filename')


def output_locations_to_dict(args, workflow_name='wf', fallback_output_name='output'):

    from amst2.library.input_file_and_dirpaths import make_cache_folder_structure, solve_output_path_and_name
    import os

    output_ome_zarr_filepath, output_ome_zarr_filename = solve_output_path_and_name(
        os.path.abspath(args.output_ome_zarr_filepath) if args.output_ome_zarr_filepath is not None else None,
        args.output_ome_zarr_filename,
        os.path.abspath(args.target_dirpath) if args.target_dirpath is not None else None,
        fallback_output_name
    )

    target_dirpath = os.path.abspath(args.target_dirpath)

    cache_dirpath, this_cache_dirpath = make_cache_folder_structure(
        target_dirpath,
        f'{workflow_name}_{output_ome_zarr_filename.replace(".ome.zarr", "")}',
        continue_run=args.continue_run
    )

    return dict(
        target_dirpath=target_dirpath,
        output_ome_zarr_filename=output_ome_zarr_filename,
        output_ome_zarr_filepath=output_ome_zarr_filepath,
        cache_dirpath=cache_dirpath,
        this_cache_dirpath=this_cache_dirpath
    )


def add_ome_zarr_arguments_to_parser(parser, omit=[]):

    names = []

    if 'resolution' not in omit:
        parser.add_argument('--resolution', type=float, nargs=3, default=(1., 1., 1.),
                            help='Resolution of input data; default=(1., 1., 1.)')
        parser.add_argument('--unit', type=str, default='pixel',
                            help='Unit of input resolution; default="pixel"')
        names.extend(['resolution', 'unit'])
    if 'downsample' not in omit:
        parser.add_argument('--downsample_type', type=str, default='Average',
                            help='Downsample type used to create the resolution pyramid; default="Average"')
        parser.add_argument('--downsample_factors', type=int, nargs='+', default=(2, 2, 2),
                            help='Downsample factors used to create the resolution pyramid; default=(2, 2, 2)')
        names.extend(['downsample_type', 'downsample_factors'])
    if 'chunk_size' not in omit:
        parser.add_argument('--chunk_size', type=int, nargs=3, default=[1, 512, 512],
                            help='Chunk size of the ome-zarr dataset; default=[1, 512, 512]')
        names.append('chunk_size')
    if 'name' not in omit:
        parser.add_argument('--name', type=str, default=None,
                            help='Name of the dataset; defaults to the filename (without ome.zarr extension)')
        names.append('name')

    return names


def args_to_dict(args, fields):
    return {field: getattr(args, field) for field in fields}


def add_snakemake_arguments_to_parser(parser):

    parser.add_argument('--run_small_jobs_locally', action='store_true',
                        help='Execute lightweight Snakemake rules locally')
    parser.add_argument('--dryrun', action='store_true',
                        help='Snakemake argument')
    parser.add_argument('--unlock', action='store_true',
                        help='Snakemake argument')
    parser.add_argument('--rerun_triggers', type=str, nargs='+', default=[],
                        help='Snakemake argument; use "--rerun_triggers mtime" to avoid rerunning due to changed params')


def args_to_snakemake_arguments(args, sn_args, output_location_args=None):

    sn_args.dryrun = args.dryrun
    sn_args.unlock = args.unlock
    sn_args.cores = args.cores
    sn_args.rerun_triggers = args.rerun_triggers
    sn_args.printshellcmds = True
    if output_location_args is not None:
        from pathlib import Path
        sn_args.directory = Path(output_location_args['this_cache_dirpath'])


def write_run_json(run_info, output_location_args):
    import json
    import os
    with open(os.path.join(output_location_args['this_cache_dirpath'], 'run.json'), mode='w') as f:
        json.dump(run_info, f, indent=2)


