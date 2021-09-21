import torch
import functools
import collections
import warnings
try:
    import numpy as np
    HAS_NUMPY = True
except ModuleNotFoundError:
    np = None  # type: ignore[assignment]
from torch._six import string_classes
from typing import Any


def autocast_decorator(autocast_instance, func):
    @functools.wraps(func)
    def decorate_autocast(*args, **kwargs):
        with autocast_instance:
            return func(*args, **kwargs)
    decorate_autocast.__script_unsupported = '@autocast() decorator is not supported in script mode'  # type: ignore[attr-defined]
    return decorate_autocast

class autocast(torch.autocast_mode.autocast):
    r"""
    See :class:`torch.autocast`.
    ``torch.cuda.amp.autocast(args...)`` is equivalent to ``torch.autocast("cuda", args...)``
    """

    def __init__(self, enabled=True, dtype=torch.float16, cache_enabled=True):
        super().__init__("cuda", enabled=enabled, dtype=dtype, cache_enabled=cache_enabled)
        if torch._jit_internal.is_scripting():
            self._enabled = enabled
        elif enabled and not torch.cuda.is_available():
            warnings.warn("torch.cuda.amp.autocast only affects CUDA ops, but CUDA is not available.  Disabling.")
            self._enabled = False
        else:
            self._enabled = enabled

    def __enter__(self):
        if torch._jit_internal.is_scripting():
            return self
        self.prev = torch.is_autocast_enabled()
        torch.set_autocast_enabled(self._enabled)
        torch.autocast_increment_nesting()
        return self

    def __exit__(self, *args):
        if torch._jit_internal.is_scripting():
            return
        # Drop the cache when we exit to a nesting level that's outside any instance of autocast.
        if torch.autocast_decrement_nesting() == 0:
            torch.clear_autocast_cache()
        torch.set_autocast_enabled(self.prev)
        return False

    def __call__(self, func):
        if torch._jit_internal.is_scripting():
            return func
        else:
            return autocast_decorator(self, func)


# Casts Tensors and containers of Tensors.  Special-cases passthroughs for strings and np.ndarrays, which
# may be falsely detected as "Iterables."
def _cast(value, dtype):
    if isinstance(value, torch.Tensor):
        is_eligible = (value.is_floating_point() and value.is_cuda and (value.dtype is not torch.float64))
        return value.to(dtype) if is_eligible else value
    elif isinstance(value, string_classes):
        return value
    elif HAS_NUMPY and isinstance(value, np.ndarray):
        return value
    elif isinstance(value, collections.abc.Mapping):
        return {_cast(k, dtype): _cast(v, dtype) for k, v in value.items()}
    elif isinstance(value, collections.abc.Iterable):
        iterable = map(lambda v: _cast(v, dtype), value)
        if isinstance(value, list) or isinstance(value, tuple):
            return type(value)(iterable)
        else:
            return iterable
    else:
        return value


# custom_fwd is a decorator that may or may not be used with arguments, following
# https://github.com/dabeaz/python-cookbook/tree/master/src/9/defining_a_decorator_that_takes_an_optional_argument.
# this works:
#     @custom_fwd
#     def forward(...):
# this also works:
#     @custom_fwd(cast_inputs=torch.float)
#     def forward(...):
# TODO:  when python 2 support is dropped, change the signature to
# def custom_fwd(fwd=None, *, cast_inputs=None) with internal changes following the link above.
def custom_fwd(fwd=None, **kwargs):
    """
    Helper decorator for ``forward`` methods of custom autograd functions (subclasses of
    :class:`torch.autograd.Function`).  See the :ref:`example page<amp-custom-examples>` for more detail.

    Args:
        cast_inputs (:class:`torch.dtype` or None, optional, default=None):  If not ``None``,
            when ``forward`` runs in an autocast-enabled region, casts incoming
            floating-point CUDA Tensors to the target dtype (non-floating-point Tensors are not affected),
            then executes ``forward`` with autocast disabled.
            If ``None``, ``forward``'s internal ops execute with the current autocast state.

    .. note::
        If the decorated ``forward`` is called outside an autocast-enabled region,
        :func:`custom_fwd<custom_fwd>` is a no-op and ``cast_inputs`` has no effect.
    """
    if fwd is None:
        if len(kwargs) == 0:
            cast_inputs = None
        else:
            assert len(kwargs) == 1
            cast_inputs = kwargs["cast_inputs"]
        return functools.partial(custom_fwd, cast_inputs=cast_inputs)

    if len(kwargs) == 0:
        cast_inputs = None
    else:
        assert len(kwargs) == 1
        cast_inputs = kwargs["cast_inputs"]

    @functools.wraps(fwd)
    def decorate_fwd(*args, **kwargs):
        if cast_inputs is None:
            args[0]._fwd_used_autocast = torch.is_autocast_enabled()
            return fwd(*args, **kwargs)
        else:
            autocast_context = torch.is_autocast_enabled()
            args[0]._fwd_used_autocast = False
            if autocast_context:
                with autocast(enabled=False):
                    return fwd(*_cast(args, cast_inputs), **_cast(kwargs, cast_inputs))
            else:
                return fwd(*args, **kwargs)
    return decorate_fwd


# Autograd ensures incoming gradients are the same type as forward outputs.  Allowing a separate
# cast_inputs argument on custom_bwd is unnecessary and could cause errors if it doesn't match
# cast_inputs supplied to custom_fwd.
def custom_bwd(bwd):
    """
    Helper decorator for backward methods of custom autograd functions (subclasses of
    :class:`torch.autograd.Function`).
    Ensures that ``backward`` executes with the same autocast state as ``forward``.
    See the :ref:`example page<amp-custom-examples>` for more detail.
    """
    @functools.wraps(bwd)
    def decorate_bwd(*args, **kwargs):
        with autocast(args[0]._fwd_used_autocast):
            return bwd(*args, **kwargs)
    return decorate_bwd
