import torch
from torch._prims import utils
from torch._prims.utils import check

meta_lib = torch.library.Library("aten", "IMPL", "Meta")

def toRealValueType(dtype):
    from_complex = {
        torch.complex32: torch.half,
        torch.cfloat: torch.float,
        torch.cdouble: torch.double
    }
    return from_complex.get(dtype, dtype)

# Implementations below are taken from https://github.com/albanD/subclass_zoo/blob/main/python_meta_tensor.py
@torch.library.impl(meta_lib, "index_select")
def meta_index_select(self, dim, index):
    result_size = list(self.size())
    if self.dim() > 0:
        result_size[dim] = index.numel()
    return self.new_empty(result_size)

@torch.library.impl(meta_lib, "index_select.out")
def meta_index_select_out(self, dim, index, out):
    torch._resize_output_(out, self.size(), self.device)
    return out.copy_(torch.index_select(self, dim, index))

@torch.library.impl(meta_lib, "abs")
def meta_abs(self):
    if self.is_complex():
        float_type = toRealValueType(self.dtype)
        return self.new_empty(self.size(), dtype=float_type)
    else:
        return self.new_empty(self.size())

@torch.library.impl(meta_lib, "abs.out")
def meta_abs_out(self, out):
    torch._resize_output_(out, self.size(), self.device)
    return out.copy_(torch.abs(self))

@torch.library.impl(meta_lib, "max")
def meta_max(self):
    return self.new_empty(())

@torch.library.impl(meta_lib, "min")
def meta_min(self):
    return self.new_empty(())

def squareCheckInputs(self, f_name):
    assert self.dim() >= 2, f"{f_name}: The input tensor must have at least 2 dimensions."
    # TODO: I think the error message has the -2 and -1 swapped.  If you fix
    # it fix the C++ squareCheckInputs too
    assert self.size(-1) == self.size(-2), \
        f"{f_name}: A must be batches of square matrices, but they are {self.size(-1)} by {self.size(-2)} matrices"

def checkUplo(uplo: str):
    uplo_uppercase = uplo.upper()
    assert len(uplo) == 1 and uplo_uppercase == 'U' or uplo_uppercase == 'L', \
        f"Expected UPLO argument to be 'L' or 'U', but got {uplo}"

@torch.library.impl(meta_lib, "linalg_eigh")
def meta_linalg_eigh(self, uplo="L"):
    squareCheckInputs(self, "linalg_eigh")
    checkUplo(uplo)
    real_dtype = toRealValueType(self.dtype)
    assert self.dim() >= 2
    values = self.new_empty(self.shape, dtype=real_dtype)
    values.transpose_(-2, -1)
    vectors = self.new_empty(self.shape[:-1])
    return (values, vectors)

@torch.library.impl(meta_lib, "reflection_pad2d")
def meta_pad2d(self, padding):
    valid_dims = self.size(1) != 0 and self.size(2) != 0
    check(
        (self.ndim == 3 and valid_dims)
        or (self.ndim == 4 and valid_dims and self.size(3) != 0),
        f"3D or 4D (batch mode) tensor expected for input, but got: {self}"
    )
    if self.ndim == 4:
        nbatch, nplane, input_h, input_w = self.shape
    else:
        nbatch = 1
        nplane, input_h, input_w = self.shape

    pad_l, pad_r, pad_t, pad_b = padding

    output_h = input_h + pad_t + pad_b
    output_w = input_w + pad_l + pad_r

    if self.ndim == 3:
        return self.new_empty((nplane, output_h, output_w))
    else:
        return self.new_empty((nbatch, nplane, output_h, output_w))

@torch.library.impl(meta_lib, "dot")
def meta_dot(self, tensor):
    check(
        self.dim() == 1 and tensor.dim() == 1,
        f"1D tensors expected, but got {self.dim()}D and {tensor.dim()}D tensors"
    )
    return self.new_empty(())

@torch.library.impl(meta_lib, "var_mean.correction")
def meta_var_mean_correction(self, dim, *, correction, keepdim=False):
    dim = utils.reduction_dims(self.shape, dim)
    if keepdim:
        output_shape = tuple(self.shape[i] if i not in dim else 1 for i in range(self.ndim))
    else:
        output_shape = utils.compute_reduction_output_shape(self.shape, dim)
    result1 = self.new_empty(output_shape, dtype=toRealValueType(self.dtype))
    result2 = self.new_empty(output_shape)
    return result1, result2

@torch.library.impl(meta_lib, "inverse")
def meta_inverse(self):
    # Bug: https://github.com/pytorch/pytorch/issues/77498
    if self.numel() == 0:
        return torch.empty_like(self)
    r = self.new_empty(self.shape)
    r.transpose_(-2, -1)
    return r

@torch.library.impl(meta_lib, "bernoulli.out")
def meta_bernoulli(self, *, generator=None, out):
    torch._resize_output_(out, self.size(), self.device)
    return out

@torch.library.impl(meta_lib, "_adaptive_avg_pool2d")
def meta_adaptive_avg_pool2d(self, output_size):
    check(self.ndim == 3 or self.ndim == 4, f"Expected 3D or 4D tensor, but got {self.shape}")
    return self.new_empty(self.shape[:-2] + tuple(output_size))

@torch.library.impl(meta_lib, "_adaptive_avg_pool3d")
def meta_adaptive_avg_pool3d(self, output_size):
    check(self.ndim == 4 or self.ndim == 5, f"Expected 4D or 5D tensor, but got {self.shape}")
    return self.new_empty(self.shape[:-3] + tuple(output_size))

@torch.library.impl(meta_lib, "repeat_interleave.Tensor")
def meta_repeat_interleave_Tensor(repeats, output_size=None):
    if output_size is None:
        raise RuntimeError(
            "cannot repeat_interleave a meta tensor without output_size"
        )
    return repeats.new_empty(output_size)

@torch.library.impl(meta_lib, "_linalg_qr_helper")
def meta_linalg_qr_helper(input, mode):
    if mode == "reduced":
        compute_q = True
        reduced_mode = True
    elif mode == "complete":
        compute_q = True
        reduced_mode = False
    elif mode == "r":
        compute_q = False
        reduced_mode = True
    else:
        raise RuntimeError(f"qr received unrecognized mode {mode}")
    check(input.ndim >= 2, lambda: f"expected matrix or batch of matrices, but got {input.ndim}-D tensor")
    check(
        utils.is_float_dtype(input.dtype) or utils.is_complex_dtype(input.dtype),
        lambda: f"expected float or complex tensor, but got {input.dtype}"
    )
    m = input.size(-2)
    n = input.size(-1)
    mn = min(m, n)
    if compute_q:
        Qt_shape = list(input.size())
        Qt_shape[-2] = mn if reduced_mode else m
        Qt_shape[-1] = m
        Q = input.new_empty(Qt_shape)
        Q.transpose_(-2, -1)
    else:
        Q = input.new_empty(0)
    Rt_shape = list(input.size())
    Rt_shape[-2] = n
    Rt_shape[-1] = mn if reduced_mode or not compute_q else m
    R = input.new_empty(Rt_shape)
    R.transpose_(-2, -1)
    return (Q, R)
