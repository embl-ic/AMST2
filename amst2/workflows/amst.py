
import os


def _run_amst(parameter_yaml, verbose=False):

    from .lib import load_parameter_yaml
    parameter_dict = load_parameter_yaml(parameter_yaml)

    output_dirpath = parameter_dict['general']['output_dirpath']

    if not os.path.exists(output_dirpath):
        os.makedirs(output_dirpath, exist_ok=True)

    if 'resolution' not in parameter_dict['general']:
        from squirrel.library.ome_zarr import OMEZarrStore
        input_ome_zarr_filepath = parameter_dict['general']['pre_align_dirpath']
        ome_zarr_h = OMEZarrStore(input_ome_zarr_filepath, mode='r')
        resolution = ome_zarr_h.metadata.scale(0)
        unit = ome_zarr_h.metadata.units
        parameter_dict['general']['resolution'] = resolution
        parameter_dict['general']['unit'] = unit

    amst_transforms_filename = 'amst'
    if parameter_dict['amst']['transform'] in ['affine', 'AffineTransform']:
        amst_transforms_filename = 'amst.json'

    from .lib import run_amst

    run_amst(
        parameter_dict,
        parameter_key='amst',
        pre_align_dirpath=os.path.join(output_dirpath, 'apply_pre_align', 'nsbs-pre-align.ome.zarr'),
        verbose=verbose
    )

    if not os.path.exists(os.path.join(output_dirpath, 'amst', 'amst.done')):
        return

    from .lib import run_apply_transformation
    apply_amst_param_key = 'apply_amst'
    pre_align_transforms = os.path.join(output_dirpath, 'nsbs-pre-align.json')
    pre_align_transforms = parameter_dict['general']['pre_align_transforms'] if 'pre_align_transforms' in parameter_dict['general'] else pre_align_transforms
    pre_align_transforms = parameter_dict[apply_amst_param_key]['pre_align_transforms'] if 'pre_align_transforms' in parameter_dict[apply_amst_param_key] else pre_align_transforms
    input_dirpath = os.path.join(output_dirpath, 'stack_to_ome_zarr', 'input-raw.ome.zarr')
    input_dirpath = parameter_dict['general']['input_dirpath'] if 'input_dirpath' in parameter_dict['general'] else input_dirpath
    run_apply_transformation(
        parameter_dict,
        parameter_key=apply_amst_param_key,
        transforms_filepath=[
            pre_align_transforms,
            os.path.join(output_dirpath, 'amst', 'amst.meta', amst_transforms_filename)
        ],
        input_dirpath=input_dirpath,
        output_filename='amst.ome.zarr',
        verbose=verbose
    )

    if not os.path.exists(os.path.join(output_dirpath, apply_amst_param_key, f'{apply_amst_param_key}.done')):
        return

    if 'amst_to_tif_stack' in parameter_dict and parameter_dict['amst_to_tif_stack']['active']:
        from .lib import run_ome_zarr_to_stack
        run_ome_zarr_to_stack(
            parameter_dict,
            parameter_key='amst_to_tif_stack',
            input_dirpath=os.path.join(output_dirpath, apply_amst_param_key, 'amst.ome.zarr'),
            output_dirname='amst',
            verbose=verbose
        )


def amst():

    # Argument parsing -----------------------------------

    import argparse

    parser = argparse.ArgumentParser(
        description='Runs AMST',
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument('parameter_yaml', type=str)
    parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args()

    parameter_yaml = args.parameter_yaml
    verbose = args.verbose

    if verbose:
        print(f'parameter_yaml = {parameter_yaml}')

    _run_amst(parameter_yaml, verbose=verbose)


def _run_cleanup_amst(parameter_yaml, verbose=False, dryrun=False):

    import shutil
    from glob import glob

    from .lib import load_parameter_yaml
    parameter_dict = load_parameter_yaml(parameter_yaml)

    output_dirpath = parameter_dict['general']['output_dirpath']

    # rm -r */snk_cache
    def remove_snk_caches(project_dir):
        dirpaths = glob(os.path.join(project_dir, '*', 'snk_cache'))
        for dirpath in dirpaths:
            print(f'rm -r {dirpath}')
            if not dryrun:
                shutil.rmtree(dirpath)
    remove_snk_caches(output_dirpath)

    # rm */*.done
    def remove_done_files(project_dir):
        files = glob(os.path.join(project_dir, '*', '*.done'))
        for file in files:
            print(f'rm {file}')
            if not dryrun:
                os.remove(file)
    remove_done_files(output_dirpath)

    print('mv amst/amst-elastix-params.txt .')
    if not dryrun:
        shutil.move(os.path.join(output_dirpath, 'amst', 'amst-elastix-params.txt'), output_dirpath)

    print('mv amst/amst.meta/amst/ amst-transforms')
    if not dryrun:
        shutil.move(
            os.path.join(output_dirpath, 'amst', 'amst.meta', 'amst'),
            os.path.join(output_dirpath, 'amst-transforms')
        )

    print('rm -r amst')
    if not dryrun:
        shutil.rmtree(os.path.join(output_dirpath, 'amst'))

    print('mv amst_to_tif_stack/amst/ amst-aligned')
    if not dryrun:
        shutil.move(
            os.path.join(output_dirpath, 'amst_to_tif_stack', 'amst'),
            os.path.join(output_dirpath, 'amst-aligned')
        )

    print('rmdir amst_to_tif_stack/')
    if not dryrun:
        os.rmdir(os.path.join(output_dirpath, 'amst_to_tif_stack'))

    print('mv apply_amst/amst.ome.zarr amst-aligned.ome.zarr')
    if not dryrun:
        shutil.move(
            os.path.join(output_dirpath, 'apply_amst', 'amst.ome.zarr'),
            os.path.join(output_dirpath, 'amst-aligned.ome.zarr')
        )

    print('rmdir apply_amst')
    if not dryrun:
        os.rmdir(os.path.join(output_dirpath, 'apply_amst'))


def cleanup_amst():

    # Argument parsing -----------------------------------

    import argparse

    parser = argparse.ArgumentParser(
        description='Cleans up an AMST run',
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument('parameter_yaml', type=str)
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-d', '--dryrun', action='store_true')

    args = parser.parse_args()

    parameter_yaml = args.parameter_yaml
    verbose = args.verbose
    dryrun = args.dryrun

    if verbose:
        print(f'parameter_yaml = {parameter_yaml}')

    _run_cleanup_amst(parameter_yaml, verbose=verbose, dryrun=dryrun)


def get_default_parameter_file():

    # Argument parsing -----------------------------------

    import argparse

    parser = argparse.ArgumentParser(
        description='Creates a default parameter file',
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument('-fp', '--output_filepath', type=str, default=None,
                        help='Filepath of the parameter file. By default it is created in the current directory')
    parser.add_argument('-pay', '--pre_align_yaml', type=str, default=None,
                        help='If the pre-alignment was performed with amst2-wf-nsbs_pre_align_run, set this argument. All input filepaths will be properly set.')
    parser.add_argument('-pi', '--param_input_dirpath', type=str, default=None,
                        help='The parameter "general:input_dirpath" will be pre-set to this value')
    parser.add_argument('-po', '--param_output_dirpath', type=str, default=None,
                        help='The parameter "general:output_dirpath" will be pre-set to this value')
    parser.add_argument('-pp', '--param_pre_align_dirpath', type=str, default=None,
                        help='The parameter "general:pre_align_dirpath" will be pre-set to this value')
    parser.add_argument('-ppt', '--param_pre_align_transforms', type=str, default=None,
                        help='The parameter "general:pre_align_transforms" will be pre-set to this value')
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
    parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args()

    output_filepath = args.output_filepath
    pre_align_yaml = args.pre_align_yaml
    param_input_dirpath = args.param_input_dirpath
    param_output_dirpath = args.param_output_dirpath
    param_pre_align_dirpath = args.param_pre_align_dirpath
    param_pre_align_transforms = args.param_pre_align_transforms
    params = args.params
    slurm = args.slurm
    verbose = args.verbose

    if pre_align_yaml is not None:
        from amst2.workflows.lib import load_parameter_yaml
        pre_align_dict = load_parameter_yaml(pre_align_yaml)
        pre_align_output_dirpath = pre_align_dict['general']['output_dirpath']
        if 'stack_to_ome_zarr' in pre_align_dict and pre_align_dict['stack_to_ome_zarr']['active']:
            param_input_dirpath = os.path.join(pre_align_output_dirpath, 'stack_to_ome_zarr', 'input-raw.ome.zarr') if param_input_dirpath is None else param_input_dirpath
        else:
            param_input_dirpath = pre_align_dict['general']['input_dirpath'] if param_input_dirpath is None else param_input_dirpath
        if param_pre_align_dirpath is None:
            param_pre_align_dirpath = os.path.join(pre_align_output_dirpath, 'apply_pre_align', 'nsbs-pre-align.ome.zarr') if param_pre_align_dirpath is None else param_pre_align_dirpath
        if param_pre_align_transforms is None:
            param_pre_align_transforms = os.path.join(pre_align_output_dirpath, 'nsbs-pre-align.json') if param_pre_align_transforms is None else param_pre_align_transforms
        if 'stack_key' in pre_align_dict['general']:
            if params is None:
                params = []
            params.append(f'general:stack_key:{pre_align_dict["general"]["stack_key"]}')
        if 'stack_pattern' in pre_align_dict['general']:
            if params is None:
                params = []
            params.append(f'general:stack_pattern:{pre_align_dict["general"]["stack_pattern"]}')
        if 'resolution' in pre_align_dict['general']:
            if params is None:
                params = []
            params.append(f'general:resolution:[{",".join([str(x) for x in pre_align_dict["general"]["resolution"]])}]')

    from amst2.workflows.lib import get_default_parameter_file_from_repo
    get_default_parameter_file_from_repo(
        'amst',
        output_filepath=output_filepath,
        param_input_dirpath=param_input_dirpath,
        param_output_dirpath=param_output_dirpath,
        param_pre_align_dirpath=param_pre_align_dirpath,
        param_pre_align_transforms=param_pre_align_transforms,
        params=params,
        slurm=slurm,
        verbose=verbose
    )
