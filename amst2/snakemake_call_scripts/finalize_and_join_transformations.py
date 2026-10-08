
if __name__ == '__main__':

    sn_input = snakemake.input
    sn_output = snakemake.output[0]

    run_info = snakemake.params['run_info']
    use_tm = snakemake.params['use_tm']
    use_local = snakemake.params['use_local']

    from squirrel.library.affine_matrices import AffineStack

    if use_tm and use_local:

        local_filepaths = sn_input[:int(len(sn_input) / 2)]
        tm_filepaths = sn_input[int(len(sn_input) / 2):]

        local_transforms = AffineStack.read_many(local_filepaths)
        tm_transforms = AffineStack.read_many(tm_filepaths)

        assert tm_transforms.sequenced, 'Template matching sequences are always sequenced, this one must be too!'
        if not local_transforms.sequenced:
            local_transforms = local_transforms.to_sequenced()

        tm_local = tm_transforms @ local_transforms.inverse()
        final_transforms = local_transforms @ tm_local.smooth_gaussian(run_info['combine_sigma'])

        final_transforms.set_metadata('bounds', tm_transforms.get_metadata('bounds'))

    elif use_tm and not use_local:

        tm_filepaths = sn_input
        tm_transforms = AffineStack.read_many(tm_filepaths)

        assert tm_transforms.sequenced, 'Template matching sequences are always sequenced, this one must be too!'

        final_transforms = tm_transforms
        final_transforms.set_metadata('bounds', tm_transforms.get_metadata('bounds'))

    elif not use_tm and use_local:

        local_filepaths = sn_input
        local_transforms = AffineStack.read_many(local_filepaths)

        if not local_transforms.sequenced:
            local_transforms = local_transforms.to_sequenced()

        final_transforms = local_transforms
        final_transforms.set_metadata('bounds', local_transforms.get_metadata('bounds'))

    else:
        raise ValueError('Either template matching or local alignment must be active!')

    print(f'bounds = {final_transforms.get_metadata("bounds")}')
    final_transforms, stack_shape = final_transforms.auto_pad(
        stack_bounds=final_transforms.get_metadata('bounds'),
        extra_padding=16
    )

    final_transforms.set_metadata('stack_shape', stack_shape)
    final_transforms.write(sn_output)

