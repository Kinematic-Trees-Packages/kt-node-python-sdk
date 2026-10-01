# Python API reference

The reference below is generated from public source and docstrings. Private `ctypes` bindings in `ktnode.abi` are implementation detail.

::: ktnode
    options:
      members: true

## Vision helper

KTM installs the direct `kinematictrees/kt-messages@0.1.0` `data_types`
dependency alongside the SDK. The optional `vision` extra adds NumPy support;
it does not bundle or generate datatype bindings.

::: ktnode.vision
    options:
      members:
        - make_rgb_image
        - encode_image_sample
        - decode_image_sample_summary
