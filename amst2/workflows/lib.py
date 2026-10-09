
import os


def run_snakemake_workflow(run_script, wf_name):
    import subprocess
    import re
    os.environ["PYTHONUNBUFFERED"] = "1"

    try:

        process = subprocess.Popen(
            run_script,
            shell=True,
            # executable="/bin/bash",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        # Collect stderr as we stream it
        stderr_lines = []

        current_step = 0
        current_progress = 0
        total_steps = 0
        current_rule = ''
        print(
            "\n_____________________________________________\n\n"
            f"{wf_name} - {current_progress} %\n\n"
            f"{current_step} / {total_steps} jobs successful\n"
            f"\n"
            "_____________________________________________",
            end=""
        )

        for line in process.stderr:
            stderr_lines.append(line)

            if line.startswith('localrule ') or line.startswith('rule '):
                current_rule = line.split(' ')[1][:-2]
            total_match = re.search(r"total\s+(\d+)", line)
            if total_match:
                total_steps = int(total_match.group(1))
            match = re.search(r"(\d+) of (\d+) steps \((\d+(?:\.\d+)?)%\) done", line)
            if match:
                current_step = int(match.group(1))
                total_steps = int(match.group(2))
                current_progress = match.group(3)

            # Print the updating block
            current_rule_str = f"currently running: {current_rule}\033[K\n" if current_rule != '' else "\033[K\n"
            print(
                "\033[F" * 6 +
                "_____________________________________________\n\n"
                f"{wf_name} - {current_progress} %\033[K\n\n"
                f"{current_step} / {total_steps} jobs successful\n" +
                current_rule_str +
                "_____________________________________________",
                end="",
                flush=True
            )

            # print("[LIVE]", line, end="")

        process.wait()

    except subprocess.CalledProcessError as e:
        print(f"\n\n{e.stderr}\n")
        print(f"\n{e.stdout}\n")
        print("_____________________________________________\n")
        print(f"{wf_name} failed. Check out error message above!")
        print("_____________________________________________\n")
        return 1
    except Exception as e:
        print(f'\n\n{e}\n')
        return 1

    # Require a successful exit AND a recognizable Snakemake completion log.
    # A shell/cluster wrapper can return zero despite an underlying job failure.
    stderr_text = "".join(stderr_lines)
    completed = any(
        int(match.group(1)) == int(match.group(2)) and int(match.group(2)) > 0
        for match in re.finditer(
            r"(\d+) of (\d+) steps \(100(?:\.0+)?%\) done", stderr_text
        )
    )
    nothing_to_do = "Nothing to be done" in stderr_text
    failed = any(message in stderr_text for message in (
        "Exiting because a job execution failed",
        "At least one job did not complete successfully",
        "WorkflowError:",
    ))
    if process.returncode == 0 and not failed and (completed or nothing_to_do):
        print(
            "\033[F" * 6 +
            "_____________________________________________\n\n"
            f"{wf_name} was successful!\033[K\n"
            "_____________________________________________\033[K\n",
            "\033[K\n",
            "\033[K",
            end='',
            flush=True
        )
        return 0

    print(f'\n\n{stderr_text}')
    print("_____________________________________________\n")
    print(f"{wf_name} failed (exit code {process.returncode}; no valid Snakemake completion or failure detected).")
    print("_____________________________________________\n")
    return 1


def run_snakemake_workflow_old(
        run_script, wf_name,
):
    import subprocess
    import sys

    try:
        process = subprocess.run(
            run_script,
            shell=True,
            executable='/bin/bash',
            check=True,
            text=True,
            capture_output=True  # Capture both stdout and stderr
        )
    except subprocess.CalledProcessError as e:
        print(f'\n\n{e.stderr}\n')
        print(f'\n{e.stdout}\n')
        print('_____________________________________________\n')
        print(f'{wf_name} failed. Check out error message above!')
        print('_____________________________________________\n')

        return 1

    lines = [line.strip() for line in process.stderr.strip().splitlines() if line.strip()]
    # if process.stderr.strip().split("\n")[-2].endswith("(100%) done"):
    if any("(100%) done" in line for line in lines[-10:]):
        print('_____________________________________________\n')
        print(f'{wf_name} was successful!')
        print('_____________________________________________\n')

        return 0

    else:
        print(process.stderr)
        print('_____________________________________________\n')
        print(f'{wf_name} failed. ')
        print('Check out {} for details or check out the output above!'.format(process.stderr.strip().split("\n")[-1]))
        print('_____________________________________________\n')

        return 1


def get_parameters_for_snakemake_workflow(parameter_dict, parameter_key, verbose=False):

    this_dict = parameter_dict['general'].copy()
    if verbose:
        print(f'parameter_key = {parameter_key}')
        print(f'this_dict = {this_dict}')

    for k, v in parameter_dict[parameter_key].items():
        if verbose:
            print(f'k = {k}; v = {v}')
        this_dict[k] = v

    return this_dict


def load_parameter_yaml(parameter_yaml):

    import yaml

    with open(parameter_yaml, 'r') as file:
        parameter_dict = yaml.safe_load(file)

    return parameter_dict


def get_resource_str(parameter_dict, resource_name='mem'):

    if resource_name in parameter_dict:
        mem_str = ''
        for mem_k, mem_v in parameter_dict[resource_name].items():
            mem_str += f'{mem_k}:{mem_v} '
        return mem_str

    return ''


def run_stack_to_ome_zarr(
        parameter_dict,
        parameter_key='stack_to_ome_zarr',
        dryrun=False,
        verbose=False
):

    this_param_dict = get_parameters_for_snakemake_workflow(parameter_dict, parameter_key)
    output_dirpath = os.path.join(this_param_dict['output_dirpath'], parameter_key)
    if not dryrun and not os.path.exists(output_dirpath):
        os.mkdir(output_dirpath)

    done_fp = os.path.join(output_dirpath, f'{parameter_key}.done')
    if not dryrun and os.path.exists(done_fp):
        print('_____________________________________________\n')
        print(f'{parameter_key} already computed!')
        print('_____________________________________________\n')
        return

    mem_str = get_resource_str(this_param_dict, 'mem')
    runtime_str = get_resource_str(this_param_dict, 'runtime')

    args = []
    args.append(f'{this_param_dict["input_dirpath"]}')
    args.append(f'{output_dirpath}')
    if 'stack_key' in this_param_dict:
        args.append(f'--stack_key {this_param_dict["stack_key"]}')
    if 'stack_pattern' in this_param_dict:
        args.append(f'--stack_pattern "{this_param_dict["stack_pattern"]}"')
    args.append('-out-oz-fn input-raw.ome.zarr')
    args.append(f'--resolution {" ".join([str(x) for x in this_param_dict["resolution"]])}')
    args.append(f'--unit {this_param_dict["unit"]}')
    args.append(f'--downsample_type {this_param_dict["downsample_type"] if "downsample_type" in this_param_dict else "Sample"}')
    args.append(f'--downsample_factors {" ".join(this_param_dict["downsample_factors"]) if "downsample_factors" in this_param_dict else "2 2 2 2 2"}')
    if 'crop_xy' in this_param_dict:
        args.append(f'--crop_xy {" ".join([str(x) for x in this_param_dict["crop_xy"]])}')
    if 'cluster' in this_param_dict and this_param_dict['cluster'] == 'slurm':
        args.append('--cluster slurm')
    if 'cores' in this_param_dict:
        args.append(f'--cores {this_param_dict["cores"]}')
    else:
        args.append(f'--cores {2048 if "cluster" in this_param_dict and this_param_dict["cluster"] == "Slurm" else 16}')
    args.append(f'--batch_size {this_param_dict["batch_size"] if "batch_size" in this_param_dict else 32}')
    args.append(f'--max_cores_per_task {this_param_dict["max_cores_per_task"] if "max_cores_per_task" in this_param_dict else this_param_dict["batch_size"] if "batch_size" in this_param_dict else min(this_param_dict["cores"], 32)}')
    if 'mem' in this_param_dict:
        args.append(f'--mem {mem_str}')
    if 'runtime' in this_param_dict:
        args.append(f'--runtime {runtime_str}')
    if 'group_name' in this_param_dict:
        args.append(f'--group_name {this_param_dict["group_name"]}')
    if verbose:
        args.append('-v')
    args.append('--continue_run')

    run_script = f'amst2-stack_to_ome_zarr {" ".join(args)}'

    print(f'\n{run_script}')

    if not dryrun:
        error = run_snakemake_workflow(run_script, parameter_key)

        if not error:
            open(done_fp, 'w').close()


def run_nsbs_alignment(
        parameter_dict,
        parameter_key,
        input_dirpath=None,
        dryrun=False,
        verbose=False,
        debug=False
):

    this_param_dict = get_parameters_for_snakemake_workflow(parameter_dict, parameter_key, verbose=verbose)
    if verbose:
        print(f'parameter_key = {parameter_key}')
        print(f'parameter_dict = {parameter_dict}')
        print(f'this_param_dict = {this_param_dict}')
    output_dirpath = os.path.join(this_param_dict['output_dirpath'], parameter_key)
    if not dryrun and not os.path.exists(output_dirpath):
        os.mkdir(output_dirpath)

    done_fp = os.path.join(output_dirpath, f'{parameter_key}.done')
    if not dryrun and os.path.exists(done_fp):
        print('_____________________________________________\n')
        print(f'{parameter_key} already computed!')
        print('_____________________________________________\n')
        return

    mem_str = get_resource_str(this_param_dict, 'mem')
    runtime_str = get_resource_str(this_param_dict, 'runtime')
    init_offsets_kwargs_str = get_resource_str(this_param_dict, 'initialize_offsets_kwargs')

    if input_dirpath is None:
        input_dirpath = f"{this_param_dict['input_dirpath']} "

    args = []
    args.append(f'{input_dirpath}')
    args.append(f'{output_dirpath}')
    if 'stack_key' in this_param_dict:
        args.append(f'--stack_key {this_param_dict["stack_key"]}')
    if 'stack_pattern' in this_param_dict:
        args.append(f'--stack_pattern "{this_param_dict["stack_pattern"]}"')
    if 'transform' in this_param_dict:
        args.append(f'--transform {this_param_dict["transform"]}')
    if 'resolution' in this_param_dict:
        args.append(f'--resolution {" ".join([str(x) for x in this_param_dict["resolution"]])}')
    if 'unit' in this_param_dict:
        args.append(f'--unit {this_param_dict["unit"]}')
    args.append(f'-out-oz-fn {"nsbs" if "z_step" in this_param_dict and this_param_dict["z_step"] > 1 else "sbs"}.ome.zarr')
    if 'z_step' in this_param_dict:
        args.append(f'--z_step {this_param_dict["z_step"]}')
    if 'average_for_z_step' not in this_param_dict or this_param_dict['average_for_z_step']:
        args.append('--average_for_z_step')
    if 'gaussian_sigma' in this_param_dict:
        args.append(f'--gaussian_sigma {this_param_dict["gaussian_sigma"]}')
    if 'use_clahe' in this_param_dict and this_param_dict["use_clahe"] == 'active':
        args.append(f'--use_clahe')
    if 'parameter_map' in this_param_dict:
        args.append(f'--parameter_map {this_param_dict["parameter_map"]}')
    if 'elx_number_of_resolutions' in this_param_dict:
        args.append(f'--elx_number_of_resolutions {this_param_dict["elx_number_of_resolutions"]}')
    if 'elx_number_of_spatial_samples' in this_param_dict:
        args.append(f'--elx_number_of_spatial_samples {this_param_dict["elx_number_of_spatial_samples"]}')
    if 'elx_maximum_number_of_iterations' in this_param_dict:
        args.append(f'--elx_maximum_number_of_iterations {this_param_dict["elx_maximum_number_of_iterations"]}')
    if 'elx_microscopy_preset' in this_param_dict:
        args.append(f'--elx_microscopy_preset {this_param_dict["elx_microscopy_preset"]}')
    if 'initialize_offsets_method' in this_param_dict:
        args.append(f'--initialize_offsets_method {this_param_dict["initialize_offsets_method"]}')
    if 'initialize_offsets_kwargs' in this_param_dict:
        args.append(f'--initialize_offsets_kwargs {init_offsets_kwargs_str}')
    if 'max_offset_distance' in this_param_dict:
        args.append(f'--max_offset_distance {this_param_dict["max_offset_distance"]}')
    if 'apply_final' in this_param_dict and this_param_dict['apply_final']:
        args.append('--apply_final')
    if 'use_edges' in this_param_dict and this_param_dict['use_edges']:
        args.append('--use_edges')
    if 'auto_mask' in this_param_dict:
        args.append(f'--auto_mask {this_param_dict["auto_mask"]}')
    args.append(f'--downsample_type {this_param_dict["downsample_type"] if "downsample_type" in this_param_dict else "Sample"}')
    args.append(f'--downsample_factors {" ".join(this_param_dict["downsample_factors"]) if "downsample_factors" in this_param_dict else "2 2 2 2 2"}')
    if 'auto_pad' in this_param_dict and this_param_dict['auto_pad']:
        args.append('--auto_pad')
    if 'preview_downsample_level' in this_param_dict:
        args.append(f'--preview_downsample_level {this_param_dict["preview_downsample_level"]}')
    if 'cluster' in this_param_dict and this_param_dict['cluster'] == 'slurm':
        args.append('--cluster slurm')
    if 'cores' in this_param_dict:
        args.append(f'--cores {this_param_dict["cores"]}')
    else:
        args.append(f'--cores {2048 if "cluster" in this_param_dict and this_param_dict["cluster"] == "Slurm" else 16}')
    args.append(f'--batch_size {this_param_dict["batch_size"] if "batch_size" in this_param_dict else 32}')
    args.append(f'--max_cores_per_task {this_param_dict["max_cores_per_task"] if "max_cores_per_task" in this_param_dict else this_param_dict["batch_size"] if "batch_size" in this_param_dict else min(this_param_dict["cores"], 32)}')
    if 'mem' in this_param_dict:
        args.append(f'--mem {mem_str}')
    if 'runtime' in this_param_dict:
        args.append(f'--runtime {runtime_str}')
    if 'group_name' in this_param_dict:
        args.append(f'--group_name {this_param_dict["group_name"]}')
    if debug:
        args.append('--debug')
    if verbose:
        args.append('-v')
    args.append('--continue_run')

    run_script = f'amst2-elastix_stack_alignment {" ".join(args)}'

    print(f'\n{run_script}')

    if not dryrun:
        error = run_snakemake_workflow(run_script, parameter_key)

        if not error:
            open(done_fp, 'w').close()


def run_apply_transformation(
        parameter_dict,
        parameter_key,
        transforms_filepath,
        input_dirpath=None,
        output_filename=None,
        dryrun=False,
        verbose=False
):
    this_param_dict = get_parameters_for_snakemake_workflow(parameter_dict, parameter_key, verbose=verbose)
    output_dirpath = os.path.join(this_param_dict['output_dirpath'], parameter_key)
    if not dryrun and not os.path.exists(output_dirpath):
        os.mkdir(output_dirpath)

    done_fp = os.path.join(output_dirpath, f'{parameter_key}.done')
    if not dryrun and os.path.exists(done_fp):
        print('_____________________________________________\n')
        print(f'{parameter_key} already computed!')
        print('_____________________________________________\n')
        return

    mem_str = get_resource_str(this_param_dict, 'mem')
    runtime_str = get_resource_str(this_param_dict, 'runtime')

    if input_dirpath is None:
        input_dirpath = f"{this_param_dict['input_dirpath']} "

    if verbose:
        print(this_param_dict)

    if type(transforms_filepath) == list or type(transforms_filepath) == tuple:
        transforms_filepath = ' '.join(transforms_filepath)

    args = []
    args.append(f'{input_dirpath}')
    args.append(f'{transforms_filepath}')
    args.append(f'{output_dirpath}')
    if 'stack_key' in this_param_dict:
        args.append(f'--stack_key {this_param_dict["stack_key"]}')
    if 'stack_pattern' in this_param_dict:
        args.append(f'--stack_pattern "{this_param_dict["stack_pattern"]}"')
    if 'resolution' in this_param_dict:
        args.append(f'--resolution {" ".join([str(x) for x in this_param_dict["resolution"]])}')
    if 'unit' in this_param_dict:
        args.append(f'--unit {this_param_dict["unit"]}')
    if output_filename is not None:
        args.append(f'-out-oz-fn {output_filename}')
    if 'cluster' in this_param_dict and this_param_dict['cluster'] == 'slurm':
        args.append('--cluster slurm')
    if 'cores' in this_param_dict:
        args.append(f'--cores {this_param_dict["cores"]}')
    else:
        args.append(f'--cores {2048 if "cluster" in this_param_dict and this_param_dict["cluster"] == "Slurm" else 16}')
    args.append(f'--batch_size {this_param_dict["batch_size"] if "batch_size" in this_param_dict else 32}')
    args.append(f'--max_cores_per_task {this_param_dict["max_cores_per_task"] if "max_cores_per_task" in this_param_dict else this_param_dict["batch_size"] if "batch_size" in this_param_dict else min(this_param_dict["cores"], 32)}')
    if 'mem' in this_param_dict:
        args.append(f'--mem {mem_str}')
    if 'runtime' in this_param_dict:
        args.append(f'--runtime {runtime_str}')
    if 'group_name' in this_param_dict:
        args.append(f'--group_name {this_param_dict["group_name"]}')
    if verbose:
        args.append('-v')
    args.append('--no_autopad')
    args.append('--continue_run')

    run_script = f'amst2-apply_transformation {" ".join(args)}'

    print(f'\n{run_script}')

    if not dryrun:

        error = run_snakemake_workflow(run_script, parameter_key)

        if not error:
            open(done_fp, 'w').close()


def run_ome_zarr_to_stack(
        parameter_dict,
        parameter_key,
        input_dirpath=None,
        output_dirname=None,
        dryrun=False,
        verbose=False
):
    this_param_dict = get_parameters_for_snakemake_workflow(parameter_dict, parameter_key, verbose=verbose)
    output_dirpath = os.path.join(this_param_dict['output_dirpath'], parameter_key)
    if not dryrun and not os.path.exists(output_dirpath):
        os.mkdir(output_dirpath)

    done_fp = os.path.join(output_dirpath, f'{parameter_key}.done')
    if not dryrun and os.path.exists(done_fp):
        print('_____________________________________________\n')
        print(f'{parameter_key} already computed!')
        print('_____________________________________________\n')
        return

    mem_str = get_resource_str(this_param_dict, 'mem')
    runtime_str = get_resource_str(this_param_dict, 'runtime')

    if input_dirpath is None:
        input_dirpath = f"{this_param_dict['input_dirpath']} "

    run_script = (
        "amst2-ome_zarr_to_stack " 
        f"{input_dirpath} "
        f"{output_dirpath} "
        f"{output_dirname} " 
        f"{'--cluster slurm' if 'cluster' in this_param_dict and this_param_dict['cluster'] == 'slurm' else ''} "
        f"--cores {this_param_dict['cores'] if 'cores' in this_param_dict else 2048} "
        f"--batch_size {this_param_dict['batch_size'] if 'batch_size' in this_param_dict else 32} "
        f"--max_cores_per_task {this_param_dict['max_cores_per_task'] if 'max_cores_per_task' in this_param_dict else this_param_dict['batch_size'] if 'batch_size' in this_param_dict else min(this_param_dict['cores'], 32)} "
        f"{'--mem {}'.format(mem_str) if 'mem' in this_param_dict else ''} "
        f"{'--runtime {}'.format(runtime_str) if 'runtime' in this_param_dict else ''} "
        f"{'--group_name {}'.format(this_param_dict['group_name']) if 'group_name' in this_param_dict else ''} "
        f"{'-v' if verbose else ''} "
        "--continue_run"
    )

    print(f'\n{run_script}')

    if not dryrun:
        error = run_snakemake_workflow(run_script, parameter_key)

        if not error:
            open(done_fp, 'w').close()


def run_amst(
        parameter_dict,
        parameter_key,
        pre_align_dirpath=None,
        verbose=False
):

    this_param_dict = get_parameters_for_snakemake_workflow(parameter_dict, parameter_key, verbose=verbose)
    if verbose:
        print(f'parameter_key = {parameter_key}')
        print(f'parameter_dict = {parameter_dict}')
        print(f'this_param_dict = {this_param_dict}')
    output_dirpath = os.path.join(this_param_dict['output_dirpath'], parameter_key)
    if not os.path.exists(output_dirpath):
        os.mkdir(output_dirpath)

    done_fp = os.path.join(output_dirpath, f'{parameter_key}.done')
    if os.path.exists(done_fp):
        print('_____________________________________________\n')
        print(f'{parameter_key} already computed!')
        print('_____________________________________________\n')
        return

    if 'elastix_parameter_file' not in this_param_dict or this_param_dict['elastix_parameter_file'] == 'auto':
        from squirrel.workflows.elastix import make_elastix_default_parameter_file_workflow
        make_elastix_default_parameter_file_workflow(
            os.path.join(output_dirpath, 'amst-elastix-params.txt'),
            transform=f'amst-{this_param_dict["transform"]}',
            verbose=verbose
        )
        this_param_dict['elastix_parameter_file'] = os.path.join(output_dirpath, 'amst-elastix-params.txt')
    assert os.path.exists(this_param_dict['elastix_parameter_file']), "Elastix parameter file not found!"

    mem_str = get_resource_str(this_param_dict, 'mem')
    runtime_str = get_resource_str(this_param_dict, 'runtime')

    pre_align_dirpath = this_param_dict['pre_align_dirpath'] if 'pre_align_dirpath' in this_param_dict else pre_align_dirpath

    run_script = (
        "amst2-amst "
        f"{pre_align_dirpath} "
        f"{output_dirpath} "
        f"--transform {this_param_dict['transform']} "
        f"--elastix_parameter_file {this_param_dict['elastix_parameter_file']} "
        f"-mr {this_param_dict['median_radius']} "
        f"{'-zm {}'.format(this_param_dict['z_smooth_method']) if 'z_smooth_method' in this_param_dict else ''} "
        f"-gs {this_param_dict['gaussian_sigma']} "
        f"{'--use_clahe' if 'use_clahe' in this_param_dict and this_param_dict['use_clahe'] == 'active' else ''} "
        f"-out-oz-fn amst.ome.zarr "
        f"{'--auto_mask_off' if 'auto_mask_off' in this_param_dict and this_param_dict['auto_mask_off'] else ''} "
        f"{'--cluster slurm' if 'cluster' in this_param_dict and this_param_dict['cluster'] == 'slurm' else ''} "
        f"--cores {this_param_dict['cores'] if 'cores' in this_param_dict else 2048} "
        f"--batch_size {this_param_dict['batch_size'] if 'batch_size' in this_param_dict else 32} "
        f"--max_cores_per_task {this_param_dict['max_cores_per_task'] if 'max_cores_per_task' in this_param_dict else this_param_dict['batch_size'] if 'batch_size' in this_param_dict else min(this_param_dict['cores'], 32)} "
        f"{'--mem {}'.format(mem_str) if 'mem' in this_param_dict else ''} "
        f"{'--runtime {}'.format(runtime_str) if 'runtime' in this_param_dict else ''} "
        f"{'--group_name {}'.format(this_param_dict['group_name']) if 'group_name' in this_param_dict else ''} "
        f"{'-v' if verbose else ''} "
        "--continue_run"
    )

    print(f'\n{run_script}')

    error = run_snakemake_workflow(run_script, parameter_key)

    if not error:
        open(done_fp, 'w').close()


PARAMETER_FILE_NAMES = dict(
    pre_align_slurm='params-nsbs-pre-align-slurm.yaml',
    pre_align_local='params-nsbs-pre-align-local.yaml',
    amst_slurm='params-amst-bspline-slurm.yaml',
    amst_local='params-amst-bspline-local.yaml'
)


import ast


def _parse_value(value: str):
    """Convert string to bool, int, float, list, or keep as string."""
    # Boolean check
    if value.lower() == "true":
        return True
    elif value.lower() == "false":
        return False

    # Try number (int or float)
    try:
        if "." in value:
            return float(value)
        else:
            return int(value)
    except ValueError:
        pass

    # Try list
    if value.startswith("[") and value.endswith("]"):
        try:
            parsed = ast.literal_eval(value)
            if isinstance(parsed, list):
                return [_parse_value(str(v)) for v in parsed]
        except Exception:
            return value  # fallback

    # Default: string
    return value


def _build_nested_dict(pairs):
    """Convert list of 'a:b:c:value' strings to nested dict."""
    result = {}
    for pair in pairs:
        keys = pair.split(":")
        *path, raw_value = keys
        value = _parse_value(raw_value)

        d = result
        for k in path[:-1]:
            d = d.setdefault(k, {})
        d[path[-1]] = value
    return result


def deep_merge(base: dict, new: dict) -> dict:
    """
    Recursively merge `new` into `base`.
    - dicts are merged
    - other values are overwritten
    """
    for key, value in new.items():
        if (
            key in base
            and isinstance(base[key], dict)
            and isinstance(value, dict)
        ):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def merge_into_yaml_file(yaml_file: str, new_dict: dict):
    """
    Merge `new_dict` into an existing YAML file, preserving comments and order.
    """
    from ruamel.yaml import YAML

    yaml = YAML()
    yaml.preserve_quotes = True  # Keep quotes as in original
    yaml.indent(mapping=2, sequence=4, offset=2)

    # Load existing YAML
    with open(yaml_file) as f:
        base = yaml.load(f)

    # Merge dictionaries
    deep_merge(base, new_dict)

    # Write back to file, preserving comments/order
    with open(yaml_file, "w") as f:
        yaml.dump(base, f)


def get_default_parameter_file_from_repo(
        workflow,  # pre_align or amst
        output_filepath=None,
        params=None,
        param_input_dirpath=None,
        param_stack_key=None,
        param_stack_pattern=None,
        param_output_dirpath=None,
        param_pre_align_dirpath=None,
        param_pre_align_transforms=None,
        param_initialize_offset_method=None,
        slurm=False,
        estimate_crop_xy=False,
        verbose=False,
):
    import importlib.resources as resources
    import shutil

    if verbose:
        print(f'workflow = {workflow}')
        print(f'output_filepath = {output_filepath}')
        print(f'params = {params}')
        print(f'param_input_dirpath = {param_input_dirpath}')
        print(f'param_stack_key = {param_stack_key}')
        print(f'param_stack_pattern = {param_stack_pattern}')
        print(f'param_output_dirpath = {param_output_dirpath}')
        print(f'param_pre_align_dirpath = {param_pre_align_dirpath}')
        print(f'param_pre_align_transforms = {param_pre_align_transforms}')
        print(f'param_initialize_offset_method = {param_initialize_offset_method}')
        print(f'slurm = {slurm}')
        print(f'estimate_crop_xy = {estimate_crop_xy}')

    if workflow not in ['pre_align', 'amst']:
        raise ValueError(f'Invalid workflow name: {workflow}; valid workflows: ["pre_align", "amst"]')

    # Pick correct template filename
    template_filename = PARAMETER_FILE_NAMES[f'{workflow}_{"slurm" if slurm else "local"}']

    # Access the subfolder with your packaged resources
    # Replace 'mypackage' and 'subfolder' with the real names
    data_path = resources.files("amst2") / "parameter_files" / template_filename

    if not data_path.is_file():
        raise FileNotFoundError(f"Template file not found in package: {data_path}")

    # Set default output filepath if not provided
    if output_filepath is None:
        output_filename = f"params_{workflow}.yaml"
        output_filepath = os.path.join(os.getcwd(), output_filename)

    # Copy file to output location
    shutil.copy(data_path, output_filepath)

    if verbose:
        print(f"Created parameter file at: {output_filepath}")
        print(f"(Template source: {data_path})")

    if estimate_crop_xy:
        assert param_input_dirpath is not None, 'To estimate crop_xy, input dirpath must be specified!'
        print('Estimating crop_xy ...')
        from squirrel.workflows.volume import estimate_crop_xy_workflow
        crop_xy = estimate_crop_xy_workflow(
            param_input_dirpath,
            key=param_stack_key,
            pattern=param_stack_pattern,
            padding=64,
            out_image=os.path.join(os.path.split(output_filepath)[0], 'max_projection.png'),
            number_of_samples=16,
            verbose=verbose
        )
        params = [] if params is None else params
        params.append(f'stack_to_ome_zarr:crop_xy:{crop_xy}')
        params.append(f'stack_to_ome_zarr:active:true')

    # We are done if no manually set parameters are given
    if not all(v is None for v in (
            params,
            param_output_dirpath,
            param_input_dirpath,
            param_stack_key,
            param_stack_pattern,
            param_pre_align_dirpath,
            param_pre_align_transforms,
            param_initialize_offset_method
    )):

        params = [] if params is None else params
        if param_input_dirpath is not None:
            params.append(f'general:input_dirpath:{param_input_dirpath}')
        if param_output_dirpath is not None:
            params.append(f'general:output_dirpath:{param_output_dirpath}')
        if param_pre_align_dirpath is not None:
            params.append(f'general:pre_align_dirpath:{param_pre_align_dirpath}')
        if param_pre_align_transforms is not None:
            params.append(f'general:pre_align_transforms:{param_pre_align_transforms}')
        if param_stack_key is not None:
            params.append(f'general:stack_key:{param_stack_key}')
        if param_stack_pattern is not None:
            params.append(f'general:stack_pattern:{param_stack_pattern}')
        if param_initialize_offset_method is not None:
            params.append(f'sbs_alignment:initialize_offsets_method:{param_initialize_offset_method}')

        if param_initialize_offset_method is not None:
            elx_no_of_resolutions = 4
            elx_max_number_of_its = 512
            if param_initialize_offset_method in ['init_elx', 'init_xcorr']:
                elx_no_of_resolutions = 2
                elx_max_number_of_its = 256
            if not any(item.startswith('sbs_alignment:elx_number_of_resolutions:') for item in params):
                params.append(f'sbs_alignment:elx_number_of_resolutions:{elx_no_of_resolutions}')
            if not any(item.startswith('sbs_alignment:elx_maximum_number_of_iterations:') for item in params):
                params.append(f'sbs_alignment:elx_maximum_number_of_iterations:{elx_max_number_of_its}')

        # Decode the parameter inputs
        params = _build_nested_dict(params)
        if verbose:
            print(f'params = {params}')

        # Update the yaml
        merge_into_yaml_file(output_filepath, params)

    print(f'\nParameter file successfully written to {output_filepath}')
