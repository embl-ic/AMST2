import hashlib
import json
import os


def _alignment_stages(parameter_dict):
    """Return enabled stages in their execution order."""
    workflow = parameter_dict.get('workflow', {})
    initial = workflow.get('pre_existing_transforms')
    stages = []
    if initial:
        stages.append(('initial', initial))
    if workflow.get('run_sbs', True):
        stages.append(('sbs', None))
    if workflow.get('run_nsbs', True):
        stages.append(('nsbs', None))
    if not stages:
        raise ValueError('Enable at least one of initial transforms, SBS, or NSBS')
    return stages



def _compose_stage_transforms(transform_filepaths, output_filepath, verbose=False):
    """Compose stage transforms in execution order into one affine stack.

    Transforms are output-to-input mappings for image resampling.
    For stages A then B, source coordinates are A(B(output)), so
    the combined mapping is A @ B.
    """
    import shutil

    if not transform_filepaths:
        raise ValueError('At least one transformation stack is required')

    if len(transform_filepaths) == 1:
        if os.path.abspath(transform_filepaths[0]) != os.path.abspath(output_filepath):
            shutil.copyfile(transform_filepaths[0], output_filepath)
        return output_filepath

    from squirrel.workflows.transformation import dot_product_on_affines_workflow

    # Keep intermediate files distinct from the final output. The final
    # composition retains metadata from the earliest (original-input) stage.
    previous = transform_filepaths[0]
    for index, next_filepath in enumerate(transform_filepaths[1:], start=1):
        target = (output_filepath if index == len(transform_filepaths) - 1
                  else os.path.join(os.path.dirname(output_filepath),
                                    f'pre-align-combined-{index}.json'))
        dot_product_on_affines_workflow(
            [previous, next_filepath], target, keep_meta=0, verbose=verbose
        )
        previous = target

    return output_filepath


def _check_run_identity(parameter_dict, stages, output_dirpath):
    """Reject reuse of a completed run with different effective inputs."""
    manifest = os.path.join(output_dirpath, 'pre-align-run-identity.json')
    configuration = json.dumps(parameter_dict, sort_keys=True, default=str)
    external = {}
    for stage, filepath in stages:
        if stage == 'initial':
            with open(filepath, 'rb') as handle:
                external[os.path.abspath(filepath)] = hashlib.sha256(handle.read()).hexdigest()
    identity = {'configuration': hashlib.sha256(configuration.encode()).hexdigest(),
                'external_transforms': external}
    if os.path.isfile(manifest):
        with open(manifest) as handle:
            if json.load(handle) != identity:
                raise RuntimeError('Pre-align inputs or parameters changed. Use a fresh output directory.')
    elif any(os.scandir(output_dirpath)):
        raise RuntimeError('Pre-align output directory contains untracked results. Use a fresh directory.')
    else:
        with open(manifest, 'w') as handle:
            json.dump(identity, handle, indent=2)


def _run_pre_align(parameter_yaml, dryrun=False, verbose=False):
    import shutil

    from .lib import load_parameter_yaml
    from .lib import run_apply_transformation
    from .lib import run_nsbs_alignment

    parameter_dict = load_parameter_yaml(parameter_yaml)
    stages = _alignment_stages(parameter_dict)
    output_dirpath = parameter_dict['general']['output_dirpath']
    original_input = parameter_dict['general']['input_dirpath']

    if not dryrun:
        os.makedirs(output_dirpath, exist_ok=True)
        _check_run_identity(parameter_dict, stages, output_dirpath)

    if parameter_dict.get('stack_to_ome_zarr', {}).get('active', False):
        from .lib import run_stack_to_ome_zarr
        run_stack_to_ome_zarr(parameter_dict, parameter_key='stack_to_ome_zarr',
                              dryrun=dryrun, verbose=verbose)
        original_input = os.path.join(output_dirpath, 'stack_to_ome_zarr/input-raw.ome.zarr')
        if not dryrun and not os.path.exists(os.path.join(output_dirpath, 'stack_to_ome_zarr/stack_to_ome_zarr.done')):
            return
        parameter_dict['general']['stack_key'] = 's0'

    current_input = original_input
    transforms = []
    for stage, filepath in stages:
        if stage == 'initial':
            if not dryrun and not os.path.isfile(filepath):
                raise FileNotFoundError(f'Initial transforms not found: {filepath}')
            transforms.append(filepath)
            needs_intermediate_stack = any(
                next_stage in ('sbs', 'nsbs') for next_stage, _ in stages
            )
            if needs_intermediate_stack:
                parameter_dict.setdefault('apply_initial_transforms', {})
                run_apply_transformation(
                    parameter_dict, parameter_key='apply_initial_transforms',
                    transforms_filepath=filepath, input_dirpath=current_input,
                    output_filename='initial.ome.zarr', dryrun=dryrun, verbose=verbose
                )
                done = 'apply_initial_transforms/apply_initial_transforms.done'
                current_input = os.path.join(
                    output_dirpath, 'apply_initial_transforms/initial.ome.zarr'
                )
        else:
            key = f'{stage}_alignment'
            parameter_dict.setdefault(key, {})['apply_final'] = True
            if stage == 'nsbs':
                parameter_dict[key]['stack_key'] = 's0' if current_input != original_input else parameter_dict['general'].get('stack_key', 's0')
            run_nsbs_alignment(parameter_dict, parameter_key=key,
                               input_dirpath=current_input, dryrun=dryrun, verbose=verbose)
            done = f'{key}/{key}.done'
            transforms.append(os.path.join(output_dirpath, key, f'{stage}.meta/elastix.json'))
            current_input = os.path.join(output_dirpath, key, f'{stage}.ome.zarr')
        if stage != 'initial' or needs_intermediate_stack:
            if not dryrun and not os.path.exists(os.path.join(output_dirpath, done)):
                return

    final_filepath = os.path.join(output_dirpath, 'pre-align.json')
    combined_filepath = os.path.join(output_dirpath, 'pre-align-combined.json')
    if dryrun:
        print(f'Compose transforms in order: {transforms} -> {combined_filepath}')
        print(f'Finalize transforms: {combined_filepath} -> {final_filepath}')
    else:
        _compose_stage_transforms(transforms, combined_filepath, verbose=verbose)
        if parameter_dict['general'].get('auto_pad', False):
            from squirrel.workflows.transformation import apply_auto_pad_workflow
            apply_auto_pad_workflow(combined_filepath, final_filepath,
                                    image_stack_path=original_input,
                                    key=parameter_dict['general'].get('stack_key', 's0'),
                                    pattern=parameter_dict['general'].get('stack_pattern', '*.tif'),
                                    verbose=verbose)
        else:
            shutil.copyfile(combined_filepath, final_filepath)

    run_apply_transformation(
        parameter_dict, parameter_key='apply_pre_align',
        transforms_filepath=final_filepath, input_dirpath=original_input,
        output_filename='pre-align.ome.zarr', dryrun=dryrun, verbose=verbose
    )
    if not dryrun and not os.path.exists(os.path.join(output_dirpath, 'apply_pre_align/apply_pre_align.done')):
        return

    if parameter_dict.get('pre_align_to_tif_stack', {}).get('active', False):
        from .lib import run_ome_zarr_to_stack
        run_ome_zarr_to_stack(
            parameter_dict, parameter_key='pre_align_to_tif_stack',
            input_dirpath=os.path.join(output_dirpath, 'apply_pre_align/pre-align.ome.zarr'),
            output_dirname='pre-align', dryrun=dryrun, verbose=verbose
        )



def pre_align():

    # Argument parsing -----------------------------------

    import argparse

    parser = argparse.ArgumentParser(
        description='Runs a pre-alignment with nth-slice-by-slice alignment for long-range registration',
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument('parameter_yaml', type=str,
                        help='Parameter file. Run `amst2-wf-pre_align-get_default_parameter_file` to generate it.')
    parser.add_argument('-d', '--dryrun', action='store_true',
                        help='Dry-run: Displays the amst2 commands that would be run.')
    parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args()

    parameter_yaml = args.parameter_yaml
    dryrun = args.dryrun
    verbose = args.verbose

    if verbose:
        print(f'parameter_yaml = {parameter_yaml}')
        print(f'dryrun = {dryrun}')

    _run_pre_align(parameter_yaml, dryrun=dryrun, verbose=verbose)


def get_default_parameter_file():

    # Argument parsing -----------------------------------

    import argparse

    parser = argparse.ArgumentParser(
        description='Creates a default parameter file',
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument('-fp', '--output_filepath', type=str, default=None,
                        help='Filepath of the parameter file. By default it is created in the current directory')
    parser.add_argument('-pi', '--param_input_dirpath', type=str, default=None,
                        help='The parameter "general:input_dirpath" will be pre-set to this value')
    parser.add_argument('-psk', '--param_stack_key', type=str, default=None,
                        help='Stack key of the input dataset (relevant for h5, n5 or ome.zarr); Defaults to "s0"')
    parser.add_argument('-psp', '--param_stack_pattern', type=str, default=None,
                        help='Stack pattern of the input dataset (relevant for tif stack); Defaults to "*.tif"')
    parser.add_argument('-po', '--param_output_dirpath', type=str, default=None,
                        help='The parameter "general:output_dirpath" will be pre-set to this value')
    parser.add_argument('-piom', '--param_initialize_offset_method', type=str, default=None,
                        help='Specify the method used for initialization of offsets; '
                             'possible values = ["none", "init_xcorr", "init_elx"]; default="init_elx"\n'
                             '  Note: This will additionally also adjust the following parameters:\n'
                             '    - sbs_alignment:elx_number_of_resolutions\n'
                             '    - sbs_alignment:elx_maximum_number_of_iterations')
    parser.add_argument('-p', '--params', nargs='+', default=None,
                        help='Specify any parameter and its value in this format:\n'
                             '  --params group:parameter_name:value\n'
                             '  Examples:\n'
                             '    --params stack_to_ome_zarr:active:true general:cores:32  -> enables input ome zarr conversion and sets the number of compute cores to 32\n'
                             '    --params general:resolution:[0.02,0.02,0.02]  -> Sets resolution to 0.02 isotropic\n'
                             '  Note: One Item consisting of group:parameter_name:value must not contain any spaces!\n'
                             '  Also note: You can generate any entry like this - also ones that have no effect!\n'
                             '  The idea of having this input argument is to make a workflow fully scriptable without the requirement for manually adjusting the parameter file.')
    parser.add_argument('--slurm', action='store_true',
                        help='Creates the parameter file for a slurm cluster; Note that the compute settings may '
                             'require adjustment')
    parser.add_argument('--estimate_crop_xy', action='store_true',
                        help='Estimates how to optimally crop the data to reduce slice size. \n'
                             'Note that enabling this requires conversion of the input to ome.zarr')
    parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args()

    output_filepath = args.output_filepath
    param_input_dirpath = args.param_input_dirpath
    param_stack_key = args.param_stack_key
    param_stack_pattern = args.param_stack_pattern
    param_output_dirpath = args.param_output_dirpath
    param_initialize_offset_method = args.param_initialize_offset_method
    params = args.params
    estimate_crop_xy = args.estimate_crop_xy
    slurm = args.slurm

    verbose = args.verbose

    from amst2.workflows.lib import get_default_parameter_file_from_repo
    get_default_parameter_file_from_repo(
        'pre_align',
        output_filepath=output_filepath,
        param_input_dirpath=param_input_dirpath,
        param_stack_key=param_stack_key,
        param_stack_pattern=param_stack_pattern,
        param_output_dirpath=param_output_dirpath,
        param_initialize_offset_method=param_initialize_offset_method,
        params=params,
        slurm=slurm,
        estimate_crop_xy=estimate_crop_xy,
        verbose=verbose
    )
