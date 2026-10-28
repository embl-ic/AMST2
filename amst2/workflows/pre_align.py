import hashlib
import json
import os


def _alignment_stages(parameter_dict):
    """Validate explicit stage activation and return stages in execution order."""
    if 'workflow' in parameter_dict:
        raise ValueError(
            "The 'workflow' section is no longer supported. Configure each "
            "stage with an explicit 'active' boolean instead."
        )

    stage_keys = ('stack_to_ome_zarr', 'pre_existing_transforms',
                  'sbs_alignment', 'nsbs_alignment', 'pre_align_to_tif_stack')
    stages = []
    for key in stage_keys:
        if key not in parameter_dict or not isinstance(parameter_dict[key], dict):
            raise ValueError(f"Missing required stage section '{key}' (with 'active: true/false').")
        settings = parameter_dict[key]
        if type(settings.get('active')) is not bool:
            raise ValueError(f"Stage '{key}' requires an explicit boolean 'active: true/false'.")
        if not settings['active']:
            continue
        if key in ('stack_to_ome_zarr', 'pre_align_to_tif_stack'):
            continue
        if key == 'pre_existing_transforms':
            filepath = settings.get('transform_filepath')
            if not isinstance(filepath, str) or not filepath.strip():
                raise ValueError(
                    "Active stage 'pre_existing_transforms' requires 'transform_filepath'."
                )
            stages.append(('initial', filepath))
        else:
            stages.append((key.removesuffix('_alignment'), None))

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
    import tempfile

    if not transform_filepaths:
        raise ValueError('At least one transformation stack is required')

    if len(transform_filepaths) == 1:
        if os.path.abspath(transform_filepaths[0]) != os.path.abspath(output_filepath):
            shutil.copyfile(transform_filepaths[0], output_filepath)
        return output_filepath

    from squirrel.workflows.transformation import dot_product_on_affines_workflow

    # Keep partial compositions temporary; only the requested output persists.
    with tempfile.TemporaryDirectory() as directory:
        previous = transform_filepaths[0]
        for index, next_filepath in enumerate(transform_filepaths[1:], start=1):
            target = (output_filepath if index == len(transform_filepaths) - 1
                      else os.path.join(directory, f'combined-{index}.json'))
            dot_product_on_affines_workflow(
                [previous, next_filepath], target, keep_meta=0, verbose=verbose
            )
            previous = target

    return output_filepath


def _parameter_differences(previous, current, prefix=''):
    """Return readable differences between two nested parameter dictionaries."""
    differences = []
    for key in sorted(set(previous) | set(current)):
        name = f'{prefix}.{key}' if prefix else str(key)
        if key not in previous:
            differences.append(f'  {name}: added {current[key]!r}')
        elif key not in current:
            differences.append(f'  {name}: removed (was {previous[key]!r})')
        elif isinstance(previous[key], dict) and isinstance(current[key], dict):
            differences.extend(_parameter_differences(previous[key], current[key], name))
        elif previous[key] != current[key]:
            differences.append(f'  {name}: {previous[key]!r} -> {current[key]!r}')
    return differences


def _check_run_identity(parameter_dict, stages, output_dirpath, force=False):
    """Check run identity; force permits reuse without changing recorded identity."""
    manifest_dirpath = os.path.join(output_dirpath, '.amst2')
    manifest = os.path.join(manifest_dirpath, 'run-identity.json')
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
            previous = json.load(handle)
        if previous.get('configuration') != identity['configuration'] or previous.get('external_transforms') != external:
            details = []
            if previous.get('configuration') != identity['configuration']:
                if isinstance(previous.get('parameters'), dict):
                    details.extend(_parameter_differences(previous['parameters'], parameter_dict))
                else:
                    details.append('  Previous manifest has no parameter details (legacy format).')
            if previous.get('external_transforms') != external:
                details.append('  Imported transformation file paths or contents changed.')
            message = ('Pre-align inputs or parameters changed:\n' + '\n'.join(details)
                       + '\nExisting outputs may be incompatible. To resume without deleting '
                       'completed results, use --force. Otherwise remove affected '
                       'outputs explicitly before restarting.')
            if not force:
                raise RuntimeError(message)
            print('WARNING: ' + message + '\nProceeding with --force; recorded identity unchanged.')
    elif any(os.scandir(output_dirpath)):
        message = ('Pre-align output directory contains untracked results. '
                   'Use a fresh directory or --force to reuse existing outputs.')
        if not force:
            raise RuntimeError(message)
        print('WARNING: ' + message + '\nProceeding with --force; no identity recorded.')
    else:
        os.makedirs(manifest_dirpath, exist_ok=True)
        with open(manifest, 'w') as handle:
            json.dump({**identity, 'parameters': parameter_dict}, handle, indent=2, default=str)


def _validate_imported_affine_stack(filepath, input_dirpath, stack_key='s0', stack_pattern='*.tif'):
    """Validate an imported 2D affine stack against the original image volume."""
    import numpy as np

    from squirrel.library.affine_matrices import AffineStack
    from squirrel.library.io import load_data_handle

    if not os.path.isfile(filepath):
        raise FileNotFoundError(f'Initial transforms not found: {filepath}')

    try:
        transforms = AffineStack.read(filepath)
    except (KeyError, TypeError, ValueError, OSError) as error:
        raise ValueError(f'Cannot read initial affine transforms {filepath}: {error}') from error

    _, input_shape = load_data_handle(input_dirpath, key=stack_key, pattern=stack_pattern)
    input_shape = tuple(int(value) for value in input_shape)
    if len(input_shape) != 3:
        raise ValueError(f'Expected a 3D input volume, got shape {input_shape}')
    if len(transforms) != input_shape[0]:
        raise ValueError(
            f'Initial affine stack contains {len(transforms)} transforms, '
            f'but input volume contains {input_shape[0]} slices'
        )

    matrices = np.asarray(transforms.as_homogeneous())
    if matrices.shape != (input_shape[0], 3, 3):
        raise ValueError(f'Expected 2D homogeneous affine matrices, got {matrices.shape}')
    if not np.isfinite(matrices).all():
        raise ValueError('Initial affine stack contains non-finite matrix coefficients')

    if transforms.has_metadata('stack_shape'):
        recorded_shape = transforms.get_metadata('stack_shape')
        if recorded_shape is not None and tuple(recorded_shape) != input_shape:
            raise ValueError(
                f'Initial affine stack shape metadata {recorded_shape} '
                f'does not match input shape {input_shape}'
            )

    return transforms


def _run_pre_align(parameter_yaml, dryrun=False, verbose=False, force=False, unlock=False):

    from .lib import load_parameter_yaml
    from .lib import run_apply_transformation
    from .lib import run_nsbs_alignment

    parameter_dict = load_parameter_yaml(parameter_yaml)
    stages = _alignment_stages(parameter_dict)
    if unlock:
        from .lib import unlock_snakemake_workflows

        stage_names = ['stack_to_ome_zarr', 'apply_initial_transforms',
                       'sbs_alignment', 'nsbs_alignment', 'apply_pre_align',
                       'pre_align_to_tif_stack']
        unlock_snakemake_workflows(parameter_dict, stage_names)
        return

    output_dirpath = parameter_dict['general']['output_dirpath']
    original_input = parameter_dict['general']['input_dirpath']

    if not dryrun:
        for stage, filepath in stages:
            if stage == 'initial':
                _validate_imported_affine_stack(
                    filepath, original_input,
                    stack_key=parameter_dict['general'].get('stack_key', 's0'),
                    stack_pattern=parameter_dict['general'].get('stack_pattern', '*.tif')
                )
        os.makedirs(output_dirpath, exist_ok=True)
        _check_run_identity(parameter_dict, stages, output_dirpath, force=force)

    if parameter_dict['stack_to_ome_zarr']['active']:
        from .lib import run_stack_to_ome_zarr
        run_stack_to_ome_zarr(parameter_dict, parameter_key='stack_to_ome_zarr',
                              dryrun=dryrun, verbose=verbose)
        original_input = os.path.join(output_dirpath, 'stack_to_ome_zarr/input-raw.ome.zarr')
        if not dryrun and not os.path.exists(os.path.join(output_dirpath, 'stack_to_ome_zarr/stack_to_ome_zarr.done')):
            return
        parameter_dict['general']['stack_key'] = 's0'

    current_input = original_input
    transforms = []
    for index, (stage, filepath) in enumerate(stages):
        has_next_stage = index < len(stages) - 1
        if stage == 'initial':
            if not dryrun and not os.path.isfile(filepath):
                raise FileNotFoundError(f'Initial transforms not found: {filepath}')
            effective_filepath = filepath
            settings = parameter_dict['pre_existing_transforms']
            initial_auto_pad = settings.get(
                'auto_pad', parameter_dict['general'].get('auto_pad', True))
            # Even without a following alignment stage, padding must run in
            # Snakemake rather than on the workflow controller.
            if has_next_stage or initial_auto_pad:
                if 'output_filename' in settings:
                    raise ValueError(
                        'pre_existing_transforms.output_filename is not supported; '
                        'the intermediate output is always initial.ome.zarr'
                    )
                parameter_dict['apply_initial_transforms'] = {
                    key: value for key, value in settings.items()
                    if key not in ('active', 'transform_filepath', 'auto_pad')
                }
                parameter_dict['apply_initial_transforms']['auto_pad'] = initial_auto_pad
                if initial_auto_pad:
                    effective_filepath = os.path.join(
                        output_dirpath, 'apply_initial_transforms', 'initial-padded.json'
                    )
                run_apply_transformation(
                    parameter_dict, parameter_key='apply_initial_transforms',
                    transforms_filepath=filepath, input_dirpath=current_input,
                    output_filename='initial.ome.zarr', dryrun=dryrun, verbose=verbose
                )
                done = 'apply_initial_transforms/apply_initial_transforms.done'
                current_input = os.path.join(
                    output_dirpath, 'apply_initial_transforms/initial.ome.zarr'
                )
            transforms.append(effective_filepath)
        else:
            key = f'{stage}_alignment'
            parameter_dict.setdefault(key, {})['materialize_output'] = has_next_stage
            if stage == 'nsbs':
                parameter_dict[key]['stack_key'] = 's0' if current_input != original_input else parameter_dict['general'].get('stack_key', 's0')
            run_nsbs_alignment(parameter_dict, parameter_key=key,
                               input_dirpath=current_input, dryrun=dryrun, verbose=verbose)
            done = f'{key}/{key}.done'
            transforms.append(os.path.join(output_dirpath, key, 'elastix.json'))
            if has_next_stage:
                current_input = os.path.join(output_dirpath, key, f'{stage}.ome.zarr')
        if stage != 'initial' or has_next_stage or (
                stage == 'initial' and initial_auto_pad):
            if not dryrun and not os.path.exists(os.path.join(output_dirpath, done)):
                return

    final_filepath = os.path.join(output_dirpath, 'pre-align.json')
    auto_pad = parameter_dict['general'].get('auto_pad', False)
    if dryrun:
        print(f'Compose transforms in order: {transforms} -> {final_filepath}')
        if auto_pad:
            print(f'Apply auto-padding to final transforms: {final_filepath}')
    elif (auto_pad and len(stages) == 1 and stages[0][0] == 'initial'
          and initial_auto_pad):
        # The imported stack was already globally padded by Snakemake.
        _compose_stage_transforms(transforms, final_filepath, verbose=verbose)
    elif auto_pad:
        import tempfile

        from squirrel.workflows.transformation import apply_auto_pad_workflow

        with tempfile.TemporaryDirectory() as directory:
            combined_filepath = os.path.join(directory, 'combined.json')
            _compose_stage_transforms(transforms, combined_filepath, verbose=verbose)
            apply_auto_pad_workflow(combined_filepath, final_filepath,
                                    image_stack_path=original_input,
                                    key=parameter_dict['general'].get('stack_key', 's0'),
                                    pattern=parameter_dict['general'].get('stack_pattern', '*.tif'),
                                    verbose=verbose)
    else:
        _compose_stage_transforms(transforms, final_filepath, verbose=verbose)

    run_apply_transformation(
        parameter_dict, parameter_key='apply_pre_align',
        transforms_filepath=final_filepath, input_dirpath=original_input,
        output_filename='pre-align.ome.zarr', dryrun=dryrun, verbose=verbose
    )
    if not dryrun and not os.path.exists(os.path.join(output_dirpath, 'apply_pre_align/apply_pre_align.done')):
        return

    if parameter_dict['pre_align_to_tif_stack']['active']:
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
    parser.add_argument('--unlock', action='store_true',
                        help='Unlock existing Snakemake caches and exit; do not use during active runs.')
    parser.add_argument('--force', action='store_true',
                        help='Allow resuming despite changed inputs or parameters; do not recompute completed steps.')

    args = parser.parse_args()

    parameter_yaml = args.parameter_yaml
    dryrun = args.dryrun
    verbose = args.verbose
    force = args.force
    unlock = args.unlock

    if verbose:
        print(f'parameter_yaml = {parameter_yaml}')
        print(f'dryrun = {dryrun}')

    _run_pre_align(parameter_yaml, dryrun=dryrun, verbose=verbose,
                   force=force, unlock=unlock)


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
    parser.add_argument('--fiji', metavar='AFFINE_JSON', type=str, default=None,
                        help='Use an imported affine stack (e.g. from Fiji SIFT) instead of SBS, followed by NSBS')
    parser.add_argument('--run_small_jobs_locally', action='store_true',
                        help='Set general:run_small_jobs_locally:true in the generated YAML')
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
    if args.fiji is not None:
        # A preset, not a separate execution mode. Explicit --params may override it.
        params = [
            'pre_existing_transforms:active:true',
            f'pre_existing_transforms:transform_filepath:{args.fiji}',
            'sbs_alignment:active:false',
            'nsbs_alignment:active:true',
        ] + ([] if params is None else params)
    estimate_crop_xy = args.estimate_crop_xy
    if args.run_small_jobs_locally:
        params = [] if params is None else params
        if not any(item.startswith('general:run_small_jobs_locally:') for item in params):
            params.append('general:run_small_jobs_locally:true')
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
