from typing import List, Optional

import torch
from torch import Tensor
from torch._C import _add_docstr, _nested  # type: ignore[attr-defined]

from torch.types import _device as Device, _dtype as DType

__all__ = [
    "to_padded_tensor",
    "as_nested_tensor",
    "nested_tensor",
]

# Nested Tensor constructor functions


def as_nested_tensor(
    tensor_list: List[Tensor],
    dtype: Optional[DType] = None,
    device: Optional[Device] = None,
) -> Tensor:
    r"""
    Constructs a nested tensor preserving autograd history from :attr:`tensor_list` a list of tensors.

    .. note::
        Tensors within the list are always copied by this function due to current nested tensor semantics.

    Args:
        tensor_list (List[Tensor]): a list of tensors with the same ndim

    Keyword arguments:
        dtype (:class:`torch.dtype`, optional): the desired type of returned nested tensor.
            Default: if None, same :class:`torch.dtype` as leftmost tensor in the list.
        device (:class:`torch.device`, optional): the desired device of returned nested tensor.
            Default: if None, same :class:`torch.device` as leftmost tensor in the list

    Example::

        >>> a = torch.arange(3, dtype=torch.float, requires_grad=True)
        >>> b = torch.arange(5, dtype=torch.float, requires_grad=True)
        >>> nt = torch.nested.as_nested_tensor([a, b])
        >>> nt.is_leaf
        False
        >>> fake_grad = torch.nested.nested_tensor([torch.ones_like(a), torch.zeros_like(b)])
        >>> nt.backward(fake_grad)
        >>> a.grad
        tensor([1., 1., 1.])
        >>> b.grad
        tensor([0., 0., 0., 0., 0.])
    """
    if not isinstance(tensor_list, list) or any(
        not isinstance(t, Tensor) for t in tensor_list
    ):
        raise TypeError(
            "nested_tensor(): Expected first argument to be a list of tensors "
        )
    return torch._nested_tensor_from_tensor_list(tensor_list, dtype, None, device, None)


# Note: This not only adds doc strings for the nested ops, but
# also connects the torch.nested Python namespace to the torch._C._nested builtins.

to_padded_tensor = _add_docstr(
    _nested.nested_to_padded_tensor,
    r"""
to_padded_tensor(input, padding, output_size=None, out=None) -> Tensor

Returns a new (non-nested) Tensor by padding the :attr:`input` nested tensor.
The leading entries will be filled with the nested data,
while the trailing entries will be padded.

.. warning::

    :func:`to_padded_tensor` always copies the underlying data,
    since the nested and the non-nested tensors differ in memory layout.

Args:
    padding (float): The padding value for the trailing entries.

Keyword args:
    output_size (Tuple[int]): The size of the output tensor.
                              If given, it must be large enough to contain all nested data;
                              else, will infer by taking the max size of each nested sub-tensor along each dimension.
    out (Tensor, optional): the output tensor.

Example::

    >>> nt = torch.nested.nested_tensor([torch.randn((2, 5)), torch.randn((3, 4))])
    nested_tensor([
      tensor([[ 1.6862, -1.1282,  1.1031,  0.0464, -1.3276],
              [-1.9967, -1.0054,  1.8972,  0.9174, -1.4995]]),
      tensor([[-1.8546, -0.7194, -0.2918, -0.1846],
              [ 0.2773,  0.8793, -0.5183, -0.6447],
              [ 1.8009,  1.8468, -0.9832, -1.5272]])
    ])
    >>> pt_infer = torch.nested.to_padded_tensor(nt, 0.0)
    tensor([[[ 1.6862, -1.1282,  1.1031,  0.0464, -1.3276],
             [-1.9967, -1.0054,  1.8972,  0.9174, -1.4995],
             [ 0.0000,  0.0000,  0.0000,  0.0000,  0.0000]],
            [[-1.8546, -0.7194, -0.2918, -0.1846,  0.0000],
             [ 0.2773,  0.8793, -0.5183, -0.6447,  0.0000],
             [ 1.8009,  1.8468, -0.9832, -1.5272,  0.0000]]])
    >>> pt_large = torch.nested.to_padded_tensor(nt, 1.0, (2, 4, 6))
    tensor([[[ 1.6862, -1.1282,  1.1031,  0.0464, -1.3276,  1.0000],
             [-1.9967, -1.0054,  1.8972,  0.9174, -1.4995,  1.0000],
             [ 1.0000,  1.0000,  1.0000,  1.0000,  1.0000,  1.0000],
             [ 1.0000,  1.0000,  1.0000,  1.0000,  1.0000,  1.0000]],
            [[-1.8546, -0.7194, -0.2918, -0.1846,  1.0000,  1.0000],
             [ 0.2773,  0.8793, -0.5183, -0.6447,  1.0000,  1.0000],
             [ 1.8009,  1.8468, -0.9832, -1.5272,  1.0000,  1.0000],
             [ 1.0000,  1.0000,  1.0000,  1.0000,  1.0000,  1.0000]]])
    >>> pt_small = torch.nested.to_padded_tensor(nt, 2.0, (2, 2, 2))
    RuntimeError: Value in output_size is less than NestedTensor padded size. Truncation is not supported.

""",
)

def nested_tensor(tensor_list, *, dtype=None, layout=None, device=None, requires_grad=False, pin_memory=False) -> Tensor:
    r"""
Constructs a nested tensor with no autograd history (also known as a “leaf tensor”, see
:ref:`Autograd mechanics <autograd-mechanics>`) from :attr:`tensor_list` a list of tensors.

Args:
    tensor_list (List[array_like]): a list of tensors, or anything that can be passed to torch.tensor,
    where each element of the list has the same dimensionality.

Keyword arguments:
    dtype (:class:`torch.dtype`, optional): the desired type of returned nested tensor.
        Default: if None, same :class:`torch.dtype` as leftmost tensor in the list.
    layout (:class:`torch.layout`, optional): the desired layout of returned nested tensor.
        Only strided and jagged layouts are supported. Default: if None, the strided layout.
    device (:class:`torch.device`, optional): the desired device of returned nested tensor.
        Default: if None, same :class:`torch.device` as leftmost tensor in the list
    requires_grad (bool, optional): If autograd should record operations on the
        returned nested tensor. Default: ``False``.
    pin_memory (bool, optional): If set, returned nested tensor would be allocated in
        the pinned memory. Works only for CPU tensors. Default: ``False``.

Example::

    >>> a = torch.arange(3, dtype=torch.float, requires_grad=True)
    >>> b = torch.arange(5, dtype=torch.float, requires_grad=True)
    >>> nt = torch.nested.nested_tensor([a, b], requires_grad=True)
    >>> nt.is_leaf
    True
    """
    if layout is None:
        layout = torch.strided
    if layout == torch.strided:
        return _nested.nested_tensor(
            tensor_list,
            dtype=dtype,
            device=device,
            requires_grad=requires_grad,
            pin_memory=pin_memory)
    elif layout == torch.jagged:
        from torch.nested._internal.nested_tensor import jagged_from_list

        nt, _ = jagged_from_list(tensor_list, offsets=None, device=device, dtype=dtype)

        nt.requires_grad_(requires_grad)
        if pin_memory:
            nt = nt.pin_memory()  # type: ignore[assignment]

        return nt
    else:
        raise RuntimeError(f"Specified layout is unsupported for nested tensors: {layout}")
