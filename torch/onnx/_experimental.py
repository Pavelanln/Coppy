"""Experimental classes and functions used by ONNX export."""

import dataclasses
from typing import Mapping, Optional, Sequence, Set, Type, Union

import torch
import torch._C._onnx as _C_onnx


@dataclasses.dataclass
class ExportOptions:
    """Arguments used by :func:`torch.onnx.export`."""

    # TODO(justinchuby): Deprecate and remove this class.

    export_params: bool = True
    verbose: bool = False
    training: _C_onnx.TrainingMode = _C_onnx.TrainingMode.EVAL
    input_names: Optional[Sequence[str]] = None
    output_names: Optional[Sequence[str]] = None
    opset_version: Optional[int] = None
    do_constant_folding: bool = True
    dynamic_axes: Optional[Mapping[str, Union[Mapping[int, str], Sequence[int]]]] = None
    keep_initializers_as_inputs: Optional[bool] = None
    custom_opsets: Optional[Mapping[str, int]] = None
    export_modules_as_functions: Union[bool, Set[Type[torch.nn.Module]]] = False
