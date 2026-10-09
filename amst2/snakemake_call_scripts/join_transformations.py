
if __name__ == '__main__':

    sn_input = snakemake.input
    sn_output = snakemake.output[0]

    run_info = snakemake.params['run_info']

    if run_info['transform'] in ['bspline', 'BSplineTransform']:

        from squirrel.library.elastix import load_transform_stack_from_multiple_files
        transforms = load_transform_stack_from_multiple_files(sn_input)
        transforms.to_file(sn_output)

    elif run_info['transform'] in ['affine', 'AffineTransform']:

        from squirrel.library.affine_matrices import AffineStack
        transforms = AffineStack.read_many(sn_input, sequence=False)
        if not transforms.sequenced:
            transforms = transforms.to_sequenced()
        transforms.write(sn_output)

    else:
        raise ValueError(f'Invalid transform: {run_info["transform"]}')
