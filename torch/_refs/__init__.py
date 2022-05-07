import torch

import torch._prims as prims
import torch._prims.utils as utils
from torch._prims.utils import (
    DimsType,
    TensorLike,
    TensorLikeType,
    DimsSequenceType,
    TensorSequenceType,
    Number,
    NumberType,
    ELEMENTWISE_TYPE_PROMOTION_KIND,
    elementwise_dtypes,
)
from torch._prims.wrappers import (
    elementwise_type_promotion_wrapper,
    out_wrapper,
    _maybe_convert_to_dtype,
    _maybe_resize_out,
)

from functools import reduce
from typing import Sequence, Optional, Union, Callable, List, Tuple
import operator
import warnings
import math
from enum import Enum

# Experimental module containing prototype Python references for existing
#   PyTorch operations.

__all__ = [
    #
    # Elementwise Unary References
    #
    "abs",
    "acos",
    "acosh",
    "asin",
    "atan",
    # "bessel_i0e",  # special.i0e
    # "bessel_i1e",  # special.i1e
    # "cbrt",  # No corresponding torch operation
    "ceil",
    "cos",
    "cosh",
    "digamma",
    "erf",
    "erfinv",
    "erfc",
    "exp",
    "expm1",
    "floor",
    "isfinite",
    "isnan",
    "lgamma",
    "log",
    "log1p",
    "neg",
    "reciprocal",
    "round",  # TODO: model kwargs
    "sign",
    "sin",
    "sinh",
    "sqrt",
    "square",
    "tan",
    #
    # Elementwise Binary References
    #
    "add",
    "atan2",
    "bitwise_and",
    "bitwise_left_shift",
    "bitwise_or",
    "bitwise_right_shift",
    "bitwise_xor",
    # "complex",
    # 'copysign', # where
    # 'div', # need to implement all rounding modes first
    "eq",
    "float_power",
    # 'floor_divide', # requires floor
    # 'fmax', # requires where
    # 'fmod',
    # 'gcd',
    "ge",
    "gt",
    # 'heaviside',
    # 'hypot',
    "igamma",
    "igammac",
    # 'isclose', # abs, sub, le, add, mul
    # 'lcm',
    # 'ldexp',
    "le",
    # 'logical_and',
    # 'logical_or',
    # 'logical_xor',
    "lt",
    # 'max', # implement with reductions
    "maximum",
    # 'min', # implement with reductions
    "minimum",
    "mul",
    "ne",
    "nextafter",
    # 'polar',  # abs, cos, sin
    "pow",
    # 'remainder',
    # 'rsub', # unblocked
    # # special.xlog1py
    # # special.zeta
    "sub",
    "true_divide",
    # 'xlogy', # where?, log, mul
    #
    # Conditional references
    #
    "where",  # TODO: add opinfo
    #
    # Data conversion and movement references
    #
    "copy_to",  # TODO: add opinfo
    #
    # Reduction ops
    #
    "sum",
    "amax",
    "amin",
    #
    # View & Shape Ops
    #
    "cat",
    "permute",
    "transpose",
    "swap_axes",  # alias for transpose
    "tensor_split",
]

Tensor = torch.Tensor


class REDUCTION_OUTPUT_TYPE_KIND(Enum):
    SAME = (0,)
    SAME_OR_REAL = (1,)  # for complex types outputs corresponding real type
    OP_MATH = (2,)  # keep output in opmath type, needed for mean
    ALWAYS_BOOL = (3,)


def _broadcast_shapes(*_shapes):
    shapes = tuple(filter(lambda x: x is not None, _shapes))

    # Short-circuits on no input
    if len(shapes) == 0:
        return None

    # Type checking
    # TODO: make common validations available as utils
    for shape in shapes:
        assert isinstance(shape, Sequence)

    # Computes common shape
    common_shape = [
        1,
    ] * reduce(max, (len(shape) for shape in shapes))
    for shape in shapes:
        for idx in range(-1, -1 - len(shape), -1):
            if common_shape[idx] == 1:
                if shape[idx] < 0:
                    raise ValueError(
                        "Attempting to broadcast a dimension with negative length!"
                    )
                common_shape[idx] = shape[idx]
            elif shape[idx] != 1:
                if common_shape[idx] != shape[idx]:
                    raise RuntimeError(
                        "Attempting to broadcast a dimension of length ",
                        str(shape[idx]),
                        "!",
                    )

    return common_shape


def _maybe_broadcast(*args, preserve_cpu_scalar_tensors=True):
    # Computes common shape
    common_shape = _broadcast_shapes(
        *map(lambda t: t.shape if isinstance(t, TensorLike) else None, args)
    )

    def __maybe_broadcast(x, shape):
        if x is None:
            return None
        elif isinstance(x, Number):
            return x
        elif isinstance(x, TensorLike):
            if preserve_cpu_scalar_tensors and utils.is_cpu_scalar_tensor(x):
                return x

            if tuple(x.shape) != common_shape:
                common_rank = len(common_shape) + 1
                start = common_rank - (len(x.shape) + 1)
                dims = tuple(range(start, len(x.shape) + start))
                return prims.broadcast_in_dim(x, common_shape, dims)
        else:
            raise RuntimeError(
                "Unexpected type when broadcasting: " + str(type(x)) + "!"
            )

    return tuple(__maybe_broadcast(x, common_shape) for x in args)


# Utilities should come BEFORE this import
from torch._decomp import register_decomposition

#
# Elementwise unary references
#

infer_aten_op = object()

# TODO: add type promotion support
def _make_elementwise_unary_reference(
    prim: Callable, *, type_promotion_kind, aten_op=infer_aten_op
) -> Callable:
    @out_wrapper
    @elementwise_type_promotion_wrapper(
        type_promoting_args=("a",), type_promotion_kind=type_promotion_kind
    )
    def _ref(a: Tensor) -> Tensor:
        return prim(a)

    if aten_op is infer_aten_op:
        aten_op = getattr(torch.ops.aten, prim.__name__)
    if aten_op is not None:
        register_decomposition(aten_op)(_ref)

    return _ref


abs = _make_elementwise_unary_reference(
    prims.abs, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.COMPLEX_TO_FLOAT
)

acos = _make_elementwise_unary_reference(
    prims.acos, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.INT_TO_FLOAT
)

acosh = _make_elementwise_unary_reference(
    prims.acosh, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.INT_TO_FLOAT
)

asin = _make_elementwise_unary_reference(
    prims.asin, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.INT_TO_FLOAT
)

atan = _make_elementwise_unary_reference(
    prims.atan, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.INT_TO_FLOAT
)

ceil = _make_elementwise_unary_reference(
    prims.ceil, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.DEFAULT
)

cos = _make_elementwise_unary_reference(
    prims.cos, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.INT_TO_FLOAT
)

cosh = _make_elementwise_unary_reference(
    prims.cosh, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.INT_TO_FLOAT
)

digamma = _make_elementwise_unary_reference(
    prims.digamma, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.INT_TO_FLOAT
)

erf = _make_elementwise_unary_reference(
    prims.erf, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.INT_TO_FLOAT
)

erfinv = _make_elementwise_unary_reference(
    prims.erf_inv, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.INT_TO_FLOAT,
    aten_op=torch.ops.aten.erfinv,  # prim/aten name mismatch
)

erfc = _make_elementwise_unary_reference(
    prims.erfc, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.INT_TO_FLOAT
)

exp = _make_elementwise_unary_reference(
    prims.exp, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.INT_TO_FLOAT
)

expm1 = _make_elementwise_unary_reference(
    prims.expm1, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.INT_TO_FLOAT
)

floor = _make_elementwise_unary_reference(
    prims.floor, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.DEFAULT
)

isfinite = _make_elementwise_unary_reference(
    prims.is_finite, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.ALWAYS_BOOL,
    aten_op=None,  # CompositeImplicitAutograd
)


def _isnan(a: Tensor) -> Tensor:
    return prims.ne(a, a)


isnan = _make_elementwise_unary_reference(
    _isnan, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.ALWAYS_BOOL,
    aten_op=torch.ops.aten.isnan,  # prim/aten name mismatch
)

lgamma = _make_elementwise_unary_reference(
    prims.lgamma, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.INT_TO_FLOAT
)

log = _make_elementwise_unary_reference(
    prims.log, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.INT_TO_FLOAT
)

log1p = _make_elementwise_unary_reference(
    prims.log1p, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.INT_TO_FLOAT
)

neg = _make_elementwise_unary_reference(
    prims.neg, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.DEFAULT
)

reciprocal = _make_elementwise_unary_reference(
    prims.reciprocal, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.INT_TO_FLOAT
)

# TODO: round takes additional kwargs
round = _make_elementwise_unary_reference(
    prims.round, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.DEFAULT,
    aten_op=None,  # TODO: this does need a decomp, but kwarg handling is needed
)

sign = _make_elementwise_unary_reference(
    prims.sign, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.DEFAULT
)

sin = _make_elementwise_unary_reference(
    prims.sin, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.INT_TO_FLOAT
)

sinh = _make_elementwise_unary_reference(
    prims.sinh, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.INT_TO_FLOAT
)

sqrt = _make_elementwise_unary_reference(
    prims.sqrt, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.INT_TO_FLOAT
)

square = _make_elementwise_unary_reference(
    prims.square, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.BOOL_TO_LONG,
    aten_op=None,  # CompositeImplicitAutograd
)

tan = _make_elementwise_unary_reference(
    prims.tan, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.INT_TO_FLOAT
)


def _make_elementwise_binary_reference(
    prim: Callable, *, type_promotion_kind, aten_op=infer_aten_op
) -> Callable:
    @out_wrapper
    @elementwise_type_promotion_wrapper(
        type_promoting_args=("a", "b"), type_promotion_kind=type_promotion_kind
    )
    def _ref(
        a: Union[Tensor, NumberType],
        b: Union[Tensor, NumberType],
    ) -> Tensor:
        a, b = _maybe_broadcast(a, b)
        return prim(a, b)

    if aten_op is infer_aten_op:
        aten_op = getattr(torch.ops.aten, prim.__name__)
    if aten_op is not None:
        register_decomposition(aten_op)(_ref)

    return _ref


# Add has its own implementation because it has an alpha argument
@out_wrapper
@elementwise_type_promotion_wrapper(
    type_promoting_args=("a", "b"),
    type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.OP_MATH,
)
def add(
    a: Union[TensorLikeType, NumberType],
    b: Union[TensorLikeType, NumberType],
    *,
    alpha: Optional[NumberType] = None,
):
    """
    Reference implementation of torch.add
    """
    a, b = _maybe_broadcast(a, b)

    if alpha is not None:
        dtype = a.dtype if isinstance(a, TensorLike) else b.dtype  # type: ignore[union-attr]
        python_type = utils.dtype_to_type(dtype)
        if not utils.is_weakly_lesser_type(type(alpha), python_type):
            msg = (
                "alpha argument of type {0} cannot be safely cast to type {1}!".format(
                    type(alpha), python_type
                )
            )
            raise ValueError(msg)
        b = prims.mul(b, alpha)

    return prims.add(a, b)


# TODO: add docstring
atan2 = _make_elementwise_binary_reference(
    prims.atan2, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.INT_TO_FLOAT
)

# TODO: add docstring
bitwise_and = _make_elementwise_binary_reference(
    prims.bitwise_and, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.DEFAULT,
)

# TODO: add docstring
bitwise_left_shift = _make_elementwise_binary_reference(
    prims.shift_left, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.DEFAULT,
    aten_op=torch.ops.aten.bitwise_left_shift,  # prim/aten name mismatch
)

# TODO: add docstring
bitwise_or = _make_elementwise_binary_reference(
    prims.bitwise_or, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.DEFAULT
)

# TODO: add docstring
bitwise_right_shift = _make_elementwise_binary_reference(
    prims.shift_right_arithmetic,
    type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.DEFAULT,
    aten_op=torch.ops.aten.bitwise_right_shift,  # prim/aten name mismatch
)

# TODO: add docstring
bitwise_xor = _make_elementwise_binary_reference(
    prims.bitwise_xor, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.DEFAULT
)

# TODO: add docstring
# complex =  _make_elementwise_binary_reference(prims.complex, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.DEFAULT)

# TODO: add docstring
eq = _make_elementwise_binary_reference(
    prims.eq, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.ALWAYS_BOOL
)

# TODO: add docstring
# Float power has its own implementation because it has unique type promotion.
# NB: aten_op not registered because CompositeExplicitAutograd
@out_wrapper
def float_power(
    a: Union[TensorLikeType, NumberType],
    b: Union[TensorLikeType, NumberType],
) -> Tensor:

    # Handles type promotion
    dtype = utils.get_higher_dtype(a, b)
    assert dtype is not None
    if utils.is_complex_dtype(dtype):
        dtype = torch.complex128
    else:
        dtype = torch.float64

    a = _maybe_convert_to_dtype(a, dtype=dtype)  # type: ignore[assignment]
    b = _maybe_convert_to_dtype(b, dtype=dtype)  # type: ignore[assignment]
    a, b = _maybe_broadcast(a, b)
    return prims.pow(a, b)


# TODO: add docstring
ge = _make_elementwise_binary_reference(
    prims.ge, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.ALWAYS_BOOL
)

# TODO: add docstring
gt = _make_elementwise_binary_reference(
    prims.gt, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.ALWAYS_BOOL
)

igamma = _make_elementwise_binary_reference(
    prims.igamma, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.INT_TO_FLOAT
)

igammac = _make_elementwise_binary_reference(
    prims.igammac, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.INT_TO_FLOAT
)

# TODO: add docstring
le = _make_elementwise_binary_reference(
    prims.le, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.ALWAYS_BOOL
)

# TODO: add docstring
lt = _make_elementwise_binary_reference(
    prims.lt, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.ALWAYS_BOOL
)

# TODO: add docstring
maximum = _make_elementwise_binary_reference(
    prims.max,
    type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.DEFAULT,
    aten_op=torch.ops.aten.maximum,  # prim/aten name mismatch
)

# TODO: add docstring
minimum = _make_elementwise_binary_reference(
    prims.min,
    type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.DEFAULT,
    aten_op=torch.ops.aten.minimum,  # prim/aten name mismatch
)

# TODO: add docstring
mul = _make_elementwise_binary_reference(
    prims.mul,
    type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.OP_MATH,
)

# TODO: add docstring
ne = _make_elementwise_binary_reference(
    prims.ne, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.ALWAYS_BOOL
)

# TODO: add docstring
nextafter = _make_elementwise_binary_reference(
    prims.nextafter, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.DEFAULT
)

# TODO: add docstring
pow = _make_elementwise_binary_reference(
    prims.pow, type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.BOOL_TO_LONG
)

# TODO: add docstring
# TODO: consider refactoring this with add impl
# sub has its own implementation because it has an alpha argument
@register_decomposition(torch.ops.aten.sub)
@out_wrapper
@elementwise_type_promotion_wrapper(
    type_promoting_args=("a", "b"),
    type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.OP_MATH,
)
def sub(
    a: Union[TensorLikeType, NumberType],
    b: Union[TensorLikeType, NumberType],
    *,
    alpha: Optional[NumberType] = None,
):
    """
    Reference implementation of torch.add
    """
    a, b = _maybe_broadcast(a, b)

    if alpha is not None:
        dtype = a.dtype if isinstance(a, TensorLike) else b.dtype  # type: ignore[union-attr]
        python_type = utils.dtype_to_type(dtype)
        if not utils.is_weakly_lesser_type(type(alpha), python_type):
            msg = (
                "alpha argument of type {0} cannot be safely cast to type {1}!".format(
                    type(alpha), python_type
                )
            )
            raise ValueError(msg)
        b = prims.mul(b, alpha)

    return prims.sub(a, b)


# TODO: add docstring
true_divide = _make_elementwise_binary_reference(
    prims.div,
    type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.INT_TO_FLOAT,
    aten_op=None,  # CompositeImplicitAutograd
)

#
# Conditional references
#

# https://pytorch.org/docs/stable/generated/torch.where.html
# TODO: implement alternate where
@register_decomposition(torch.ops.aten.where)
@out_wrapper
@elementwise_type_promotion_wrapper(
    type_promoting_args=("a", "b"),
    type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.DEFAULT,
)
def where(
    pred: Tensor,
    a: Optional[Union[TensorLikeType, NumberType]] = None,
    b: Optional[Union[TensorLikeType, NumberType]] = None,
):
    """ """

    if a is None or b is None:
        raise NotImplementedError

    pred, a, b = _maybe_broadcast(pred, a, b)
    return prims.select(pred, a, b)


#
# Data Movement References
#


def copy_to(a: Tensor, b: Tensor, *, allow_cross_device=True):
    if not allow_cross_device and a.device != b.device:
        msg = "Attempting to copy from device {0} to device {1}, but cross-device copies are not allowed!".format(
            b.device, a.device
        )
        raise RuntimeError(msg)

    return prims.copy_to(a, b)


#
# Reduction references
#


def _reduction(
    a: Tensor,
    prim: Callable,
    *,
    has_identity: bool = True,
    accepts_dim_tuple: bool = True,  # to handle min/argmin that accept single dim only
    dims: Optional[DimsType] = None,
    keepdims: bool = False,
    dtype: Optional[torch.dtype] = None,  # should be specified for ops that support it
    out: Optional[Tensor] = None,
    output_dtype_kind: REDUCTION_OUTPUT_TYPE_KIND,
):  # it is usually SAME, but I want
    # ref writers to actually think about what to put here
    assert isinstance(a, TensorLike)
    if out is not None:
        assert isinstance(out, TensorLike)
        if dtype is not None:
            # TODO - this is true for eager mode currently, but it's wrong behavior for complex norms
            if dtype != out.dtype:
                raise RuntimeError(
                    "dtype argument and out dtype must match in reduction"
                )
    if not accepts_dim_tuple:
        assert dims is None or isinstance(dims, int)
    if isinstance(dims, int):
        dims = (dims,)  # type: ignore[assignment]
    dims = utils.reduction_dims(a.shape, dims)
    if not has_identity:
        valid_shape = all(a.shape[i] for i in range(a.ndim) if i in dims)
        if not valid_shape:
            raise RuntimeError(
                "reducing over zero-size dimension for reduction operation without identity"
            )
    # even though some reductions, like amin or amax, don't strictly require type promotion,
    # all the math ops (including comparisons) are still defined only for a computation type,
    # so promotion will still happen. We are doing it explicitly here
    inp_dtype = dtype if dtype is not None else a.dtype
    computation_dtype = utils._get_computation_dtype(inp_dtype)
    a_converted = prims.convert_element_type(a, computation_dtype)
    result = prim(a_converted, dims)

    if keepdims:
        output_shape = [a.shape[i] if i not in dims else 1 for i in range(a.ndim)]
        broadcast_dims = [i for i in range(a.ndim) if i not in dims]
        result = prims.broadcast_in_dim(result, output_shape, broadcast_dims)
    if out is not None:
        if dtype is None:
            if output_dtype_kind == REDUCTION_OUTPUT_TYPE_KIND.SAME:
                if out.dtype != a.dtype:
                    raise RuntimeError("Expected the dtype for input and out to match")
            elif output_dtype_kind == REDUCTION_OUTPUT_TYPE_KIND.ALWAYS_BOOL:
                if out.dtype != torch.bool:
                    raise RuntimeError("Expected the dtype for input and out to match")
        out = _maybe_resize_out(out, result.shape)
        return copy_to(out, result, allow_cross_device=False)  # type: ignore[arg-type]

    if output_dtype_kind == REDUCTION_OUTPUT_TYPE_KIND.SAME:
        result_dtype = dtype if dtype else a.dtype
        result = prims.convert_element_type(result, result_dtype)
    return result


# TODO: register decomp after stride logic is fixed
def sum(
    a: Tensor,
    dim: Union[Optional[int], Optional[List[int]]] = None,
    keepdim: bool = False,
    *,
    dtype=None,
    out: Optional[Tensor] = None,
):
    if dtype is None:
        if utils.is_boolean_dtype(a.dtype) or utils.is_integer_dtype(a.dtype):
            dtype = torch.int64
        else:
            dtype = a.dtype
    # reduces over all dimensions if dim=() is passed
    if dim == () or dim == []:
        dim = None
    return _reduction(
        a,
        prims.sum,
        dims=dim,
        keepdims=keepdim,
        dtype=dtype,
        out=out,
        output_dtype_kind=REDUCTION_OUTPUT_TYPE_KIND.SAME,
    )


def amin(
    a: Tensor,
    dim: Union[Optional[int], Optional[List[int]]] = None,
    keepdim: bool = False,
    *,
    out: Optional[Tensor] = None,
):
    # reduces over all dimensions if dim=() is passed
    if dim == () or dim == []:
        dim = None
    return _reduction(
        a,
        prims.amin,
        dims=dim,
        keepdims=keepdim,
        dtype=None,
        out=out,
        has_identity=False,
        output_dtype_kind=REDUCTION_OUTPUT_TYPE_KIND.SAME,
    )


def amax(
    a: Tensor,
    dim: Union[Optional[int], Optional[List[int]]] = None,
    keepdim: bool = False,
    *,
    out: Optional[Tensor] = None,
):
    # reduces over all dimensions if dim=() is passed
    if dim == () or dim == []:
        dim = None
    return _reduction(
        a,
        prims.amax,
        dims=dim,
        keepdims=keepdim,
        dtype=None,
        out=out,
        has_identity=False,
        output_dtype_kind=REDUCTION_OUTPUT_TYPE_KIND.SAME,
    )


@out_wrapper
@elementwise_type_promotion_wrapper(
    type_promoting_args=("tensors",),
    type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.DEFAULT,
)
def cat(tensors: TensorSequenceType, dim: int = 0) -> TensorLikeType:
    _dim = utils.canonicalize_dims(tensors[0].ndim, dim)
    return prims.concatenate(tensors, _dim)


def permute(a: TensorLikeType, dims: DimsSequenceType) -> TensorLikeType:
    _permutation = utils.canonicalize_dims(a.ndim, dims)
    return prims.transpose(a, _permutation)


# Note: does not work with TensorMetas because of data-dependent control-flow
def tensor_split(
    a: TensorLikeType,
    indices_or_sections: Union[Tensor, DimsType],
    dim: int = 0,
) -> Tuple[TensorLikeType, ...]:
    _dim = utils.canonicalize_dim(a.ndim, dim)
    if a.ndim == 0:
        msg = "tensor_split: received a rank zero tensor, but expected a tensor of rank one or greater!"
        raise ValueError(msg)

    # If indices_or_sections is a tensor, it must be a CPU Long tensor
    if isinstance(indices_or_sections, TensorLike):
        if indices_or_sections.device != torch.device("cpu"):
            msg = "tensor_split: if indices_or_sections is a tensor it must be on the CPU, but received one on {0}".format(
                indices_or_sections.device
            )
            raise ValueError(msg)
        if indices_or_sections.dtype != torch.long:
            msg = "tensor_split: if indices_or_sections is a tensor it must have long dtype, "
            " but received one with dtype {0}".format(indices_or_sections.dtype)
            raise ValueError(msg)

    # Case 0 -- indices_or_sections is an integer or a scalar tensor n and a is split along dim into n parts of equal-ish length
    if isinstance(indices_or_sections, int) or (
        isinstance(indices_or_sections, TensorLike) and indices_or_sections.ndim == 0
    ):
        sections: int = (
            indices_or_sections  # type: ignore[assignment]
            if isinstance(indices_or_sections, Number)
            else indices_or_sections.item()
        )

        if sections <= 0:
            msg = "tensor_split: number of sections must be greater than 0, but was {0}".format(
                sections
            )
            raise ValueError(msg)

        splits = []
        dim_size = a.shape[_dim]
        min_split_size = math.floor(dim_size / sections)
        num_splits_one_extra = dim_size % sections
        start_idx = 0
        for split_idx in range(sections):
            split_size = (
                min_split_size + 1
                if (split_idx < num_splits_one_extra)
                else min_split_size
            )
            s = prims.slice_in_dim(a, start_idx, start_idx + split_size, axis=_dim)
            splits.append(s)
            start_idx = start_idx + split_size

        return tuple(splits)
    # Case 1 -- indices_or_sections is a sequence of integers or a 1D tensor describing the splits
    else:
        indices = indices_or_sections
        if isinstance(indices_or_sections, TensorLike):
            if indices_or_sections.ndim != 1:
                msg = "tensor_split: non-scalar indices_or_sections tensors must have only one dimension, "
                "but received a tensor with {0} dimensions".format(
                    indices_or_sections.ndim
                )
                raise ValueError(msg)

            indices = indices_or_sections.tolist()

        splits = []
        start_idx = 0
        for x in indices:
            splits.append(prims.slice_in_dim(a, start_idx, x, axis=_dim))
            start_idx = x
        splits.append(prims.slice_in_dim(a, start_idx, a.shape[_dim], axis=_dim))
        return tuple(splits)


def transpose(a: TensorLikeType, dim0: int, dim1: int) -> TensorLikeType:
    _dim0, _dim1 = utils.canonicalize_dims(a.ndim, (dim0, dim1))  # type: ignore[misc]

    if a.ndim <= 1:
        return a

    _permutation = list(range(0, a.ndim))
    _permutation[_dim0] = _dim1
    _permutation[_dim1] = _dim0
    return prims.transpose(a, _permutation)


# Aliases for transpose
swap_axes = transpose
