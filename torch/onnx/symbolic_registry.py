import warnings
import importlib
from inspect import getmembers, isfunction

# The symbolic registry "_registry" is a dictionary that maps operators
# (for a specific domain and opset version) to their symbolic functions.
# An operator is defined by its domain, opset version, and opname.
# The keys are tuples (domain, version), (where domain is a string, and version is an int),
# and the operator's name (string).
# The map's entries are as follows : _registry[(domain, version)][op_name] = op_symbolic
_registry = {}

_symbolic_versions = {}
from torch.onnx.symbolic_helper import _onnx_stable_opsets
for opset_version in _onnx_stable_opsets:
    module = importlib.import_module('torch.onnx.symbolic_opset{}'.format(opset_version))
    _symbolic_versions[opset_version] = module

def register_version(domain, version):
    if not is_registered_version(domain, version):
        global _registry
        _registry[(domain, version)] = {}
    register_ops_in_version(domain, version)


def register_ops_helper(domain, version, iter_version):
    version_ops = get_ops_in_version(iter_version)
    for op in version_ops:
        if isfunction(op[1]) and not is_registered_op(op[0], domain, version):
            register_op(op[0], op[1], domain, version)


def register_ops_in_version(domain, version):
    # iterates through the symbolic functions of
    # the specified opset version, and the previous
    # opset versions for operators supported in
    # previous versions.

    # Opset 9 is the base version.
    # For operators of different opset version, updated symbolic functions are added
    # in the respective symbolic_opset{version}.py file.
    # Checkout topk in symbolic_opset10.py, and upsample_nearest2d in symbolic_opset8.py for example.
    iter_version = version
    while iter_version != 9:
        register_ops_helper(domain, version, iter_version)
        if iter_version > 9:
            iter_version = iter_version - 1
        else:
            iter_version = iter_version + 1

    register_ops_helper(domain, version, 9)


def get_ops_in_version(version):
    return getmembers(_symbolic_versions[version])


def is_registered_version(domain, version):
    global _registry
    return (domain, version) in _registry


def register_op(opname, op, domain, version):
    if domain is None or version is None:
        warnings.warn("ONNX export failed. The ONNX domain and/or version to register are None.")
    global _registry
    if not is_registered_version(domain, version):
        _registry[(domain, version)] = {}
    _registry[(domain, version)][opname] = op


def is_registered_op(opname, domain, version):
    if domain is None or version is None:
        warnings.warn("ONNX export failed. The ONNX domain and/or version are None.")
    global _registry
    return (domain, version) in _registry and opname in _registry[(domain, version)]


def get_registered_op(opname, domain, version):
    if domain is None or version is None:
        warnings.warn("ONNX export failed. The ONNX domain and/or version are None.")
    global _registry
    return _registry[(domain, version)][opname]
