import runpy
from setuptools import setup, find_packages

version = runpy.run_path("amst2/__version__.py")["__version__"]

setup(
    name='amst2',
    version=version,
    author='Julian Hennies',
    author_email='hennies@embl.de',
    url='https://github.com/jhennies/amst2',
    license="GPLv3",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "amst2": ["snakemake_workflows/*.snk", "parameter_files/*.yaml"],
    },
    entry_points={
        'console_scripts': [
            'amst2-stack_to_ome_zarr = amst2.conversion:snk_stack_to_ome_zarr',
            'amst2-ome_zarr_to_stack = amst2.conversion:snk_ome_zarr_to_stack',
            'amst2-default_amst_pre_alignment = amst2.stack_alignment:snk_default_amst_pre_alignment',
            'amst2-amst = amst2.amst:snk_amst',
            'amst2-elastix_stack_alignment = amst2.stack_alignment:snk_elastix_stack_alignment',
            'amst2-template_matching_stack_alignment = amst2.stack_alignment:snk_template_matching_stack_alignment',
            'amst2-apply_transformation = amst2.stack_alignment:snk_apply_transformation',
            'amst2-normalize_stack = amst2.stack_operations:snk_normalize_stack',
            'amst2-wf-nsbs_pre_align-run = amst2.workflows.pre_align:nsbs_pre_align',
            'amst2-wf-nsbs_pre_align-get_default_parameter_file = amst2.workflows.pre_align:get_default_parameter_file',
            'amst2-wf-nsbs_pre_align-cleanup = amst2.workflows.pre_align:cleanup_nsbs_pre_align',
            'amst2-wf-amst-get_default_parameter_file = amst2.workflows.amst:get_default_parameter_file',
            'amst2-wf-amst-run = amst2.workflows.amst:amst',
            'amst2-wf-amst-cleanup = amst2.workflows.amst:cleanup_amst',
        ]
    },
    install_requires=[
        'numpy',
        'h5py',
        'tifffile',
        'ruamel.yaml',
        'squirrel>=0.5.6'
    ]
)
