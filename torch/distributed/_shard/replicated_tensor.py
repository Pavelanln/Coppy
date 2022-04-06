import torch
import torch.distributed as dist

from torch.distributed._shard.sharded_tensor.api import ShardedTensor
from torch.distributed import distributed_c10d
from torch.overrides import get_default_nowrap_functions

class ReplicatedTensor(torch.Tensor):
    """
    ReplicatedTensor represents a tensor which is replicated across the `world_size` and
    has the same value on each rank.

    ReplicatedTensor is a :class:`~torch.Tensor` subclass, and it could be used together
    with ShardedTensor/Tensor together to express different types of computation. The
    inter-op rules defined as (using torch.add as an example op):
        ReplicatedTensor + ReplicatedTensor = ReplicatedTensor
        ReplicatedTensor + torch.Tensor = torch.Tensor
        ReplicatedTensor + ShardedTensor = ShardedTensor
        ReplicatedTensor + other type (i.e. Scalar) = other type

    NOTE: We do not gurantee equal content of ReplicatedTensor across nodes after its
    construction. Although we defined proper inter-op rules to make sure ReplicatedTensor
    stays the same, there's no enforcement on it (i.e. if you manually modify content on
    some ranks, the modified value will not automatically get synced to other nodes). If
    you wish to manually validate tensors are the same across ranks, use `validate()`.

    """
    process_group: distributed_c10d.ProcessGroup

    __slots__ = ["process_group"]

    def __new__(cls, data=None, process_group=None):
        if data is None:
            data = torch.empty(0)
        r = torch.Tensor._make_subclass(cls, data, data.requires_grad)      # type: ignore[arg-type]
        r.process_group = (     # type: ignore[attr-defined]
            process_group
            if process_group is not None
            else distributed_c10d._get_default_group()
        )
        return r

    def __deepcopy__(self, memo):
        if id(self) in memo:
            return memo[id(self)]
        else:
            result = type(self)(self.data.clone(memory_format=torch.preserve_format), self.process_group)
            memo[id(self)] = result
            return result

    def __repr__(self):
        return f"ReplicatedTensor({super(ReplicatedTensor, self).__repr__()})"

    @classmethod
    def __torch_function__(cls, func, types, args=(), kwargs=None):
        if kwargs is None:
            kwargs = {}
        # We will re-dispatch the execution to ShardedTensor __torch_function__
        # if we find there're ShardedTensor operands. We will also check if args/kwargs
        # are all replicated tensor operands, we have to do this to ensure we do not
        # converting results back to ReplicatedTensor if not all operands are replicated.
        all_replicated = True
        replicated_pg = None

        def dispatch_arg(arg):
            nonlocal replicated_pg, all_replicated
            if isinstance(arg, ShardedTensor):
                # redispatch to ShardedTensor
                # TODO: handle ShardedTensor/PartialTensor inter-op with ReplicatedTensor
                return arg.__torch_function__(func, types, args, kwargs)
            if isinstance(arg, ReplicatedTensor):
                if replicated_pg is None:
                    replicated_pg = arg.process_group
                elif replicated_pg != arg.process_group:
                    raise RuntimeError(
                        f"ReplicatedTensor operands must be in the same process group "
                        f"in torch function '{func.__name__}', but found at least two "
                        f"ReplicatedTensor operands in different process groups! ")
            else:
                all_replicated = False

        for arg in args:
            dispatch_arg(arg)

        if kwargs is not None:
            for k, v in kwargs.items():
                dispatch_arg(v)

        # We cann't do super().__torch_function__() as it implicitly convert the result
        # back to tensor subclasses, where in our case, we need to control the output type
        # base on the inter-op rules we defined.
        with torch._C.DisableTorchFunction():
            rs = func(*args, **kwargs)
            if func in get_default_nowrap_functions():
                return rs
            if all_replicated and isinstance(rs, torch.Tensor) and not isinstance(rs, cls):
                # if all operands are ReplicatedTensors and does not get dispatched to ShardedTensor
                # __torch_function__, result is a torch.Tensor, then we convert and return a
                # ReplicatedTensor according to our inter-op rule
                rs = rs.as_subclass(ReplicatedTensor)        # type: ignore[arg-type]
                # propagate the process_group field to result
                rs.process_group = replicated_pg        # type: ignore[attr-defined]

            return rs

    def validate(self) -> bool:
        """
        Validate the ReplicatedTensor is legit by all gathering tensors on all ranks
        and check to make sure they are the same.

        If there's some ranks with different values, a ValueError will be raised.

        Keyword args:
            process_group (ProcessGroup, optional): The process group to work on. If None,
                the default process group will be used.

        Returns:
            True if validation succeed.
        """
        world_size = dist.get_world_size(self.process_group)
        current_rank = dist.get_rank(self.process_group)

        tensors_on_rank = [torch.empty_like(self) for _ in range(world_size)]

        dist.all_gather(tensors_on_rank, self, group=self.process_group)
        # validate and check if all tensors are equal
        for rank, tensor in enumerate(tensors_on_rank):
            if not torch.allclose(self, tensor):
                raise ValueError(
                    f"ReplicatedTensor have different values on rank {current_rank} and {rank}")

        return True

    def __setstate__(self, state):
        with torch._C.DisableTorchFunction():
            self.data = state
            self.requires_grad = state.requires_grad
            from torch.distributed._shard.api import _get_current_process_group
            self.process_group = _get_current_process_group()

    def __getstate__(self):
        return self.data


class ReplicatedTensorParametrization(torch.nn.Module):
    """
    Parametrization module to convert Tensors into ReplicatedTensors while
    running the forward pass of nn.Module.

    The parametrization ensures that gradients are shared across the
    original Tensor and the parametrized one.
    """
    def __init__(self, process_group=None):
        super(ReplicatedTensorParametrization, self).__init__()
        self.process_group = process_group

    class Function(torch.autograd.Function):
        """
        Autograd function to ensure gradients are replicated between the
        parameterized tensor and the original one.
        """
        @staticmethod
        def forward(ctx, inp, process_group=None):
            return ReplicatedTensor(inp, process_group)

        @staticmethod
        def backward(ctx, grad_output):
            return grad_output, None

    def forward(self, tensor: torch.Tensor):
        replicated_tensor = ReplicatedTensorParametrization.Function.apply(tensor, self.process_group)
        # Pick up grad from the original tensor.
        replicated_tensor.grad = tensor.grad
        return replicated_tensor
