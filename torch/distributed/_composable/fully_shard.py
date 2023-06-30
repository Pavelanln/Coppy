from typing import Callable, Iterable, Optional, Union

import torch
import torch.distributed as dist
import torch.nn as nn
from torch.distributed._composable.contract import contract
from torch.distributed._composable_state import _get_module_state, _insert_module_state
from torch.distributed.fsdp._common_utils import _FSDPState
from torch.distributed.fsdp._dynamo_utils import _annotate_modules_for_dynamo

from torch.distributed.fsdp._init_utils import (
    _init_buffer_state,
    _init_core_state,
    _init_device_handle,
    _init_ignored_module_states,
    _init_param_handle_from_module,
    _init_prefetching_state,
    _init_process_group_state,
    _init_runtime_state,
    _init_state_dict_state,
    HYBRID_SHARDING_STRATEGIES,
)
from torch.distributed.fsdp._runtime_utils import (
    _register_post_forward_hooks,
    _register_pre_forward_hooks,
    _register_root_pre_forward_hook,
)
from torch.distributed.fsdp._state_dict_utils import _register_all_state_dict_hooks
from torch.distributed.fsdp._wrap_utils import _auto_wrap
from torch.distributed.fsdp.api import (
    BackwardPrefetch,
    CPUOffload,
    MixedPrecision,
    ShardingStrategy,
)
from torch.distributed.fsdp.wrap import _FSDPPolicy


@contract(state_cls=_FSDPState)
def fully_shard(
    module: nn.Module,
    *,
    process_group: Optional[dist.ProcessGroup] = None,
    policy: Optional[_FSDPPolicy] = None,
    strategy: Optional[ShardingStrategy] = None,
    mixed_precision: Optional[MixedPrecision] = None,
    cpu_offload: Optional[CPUOffload] = None,
    ignored_modules: Optional[Iterable[torch.nn.Module]] = None,
    device_id: Optional[Union[int, torch.device]] = None,
    param_init_fn: Optional[Callable[[nn.Module], None]] = None,
    sync_module_states: bool = False,
    forward_prefetch: bool = False,
    ignored_states: Union[
        Optional[Iterable[torch.nn.Parameter]], Optional[Iterable[torch.nn.Module]]
    ] = None,
) -> nn.Module:
    """
    Applies ``FullyShardedDataParallel` (FSDP) semantics to ``module``.
    """
    torch._C._log_api_usage_once("torch.distributed.fully_shard")
    # Enforce the new auto wrap policy
    if policy is not None and not isinstance(policy, _FSDPPolicy):
        raise ValueError(f"Expects an `_FSDPPolicy` but got {policy}")
    state = fully_shard.state(module)
    state = _init_ignored_module_states(state, module, ignored_modules, ignored_states)
    state = _init_device_handle(state, module, state._ignored_params, device_id)
    _annotate_modules_for_dynamo(module, state._ignored_modules, True)
    state = _init_process_group_state(
        state, process_group, ShardingStrategy.FULL_SHARD, policy
    )
    if policy is not None:
        fsdp_kwargs = {
            "process_group": process_group,
            "strategy": strategy,
            "mixed_precision": mixed_precision,
            "cpu_offload": cpu_offload,
            "ignored_modules": ignored_modules,
            "device_id": device_id,
            "param_init_fn": param_init_fn,
            "sync_module_states": sync_module_states,
            "forward_prefetch": forward_prefetch,
            "ignored_states": ignored_states,
        }
        if strategy in HYBRID_SHARDING_STRATEGIES:
            fsdp_kwargs["process_group"] = (state.process_group, state._inter_node_pg)
        _auto_wrap(
            module,
            policy,
            state._ignored_modules,
            state._ignored_params,
            fsdp_kwargs,
            fully_shard,
        )
    state = _init_core_state(
        state,
        strategy or ShardingStrategy.FULL_SHARD,
        mixed_precision,
        cpu_offload,
        limit_all_gathers=True,
        use_orig_params=True,
        backward_prefetch_limit=1,
        forward_prefetch_limit=1,
    )
    state = _init_runtime_state(state)
    state = _init_prefetching_state(
        state, BackwardPrefetch.BACKWARD_PRE, forward_prefetch=forward_prefetch
    )
    state = _init_buffer_state(state, module)
    state = _init_param_handle_from_module(
        state, module, device_id, param_init_fn, sync_module_states
    )
    state = _init_state_dict_state(state)
    _register_all_state_dict_hooks(state)
    _register_pre_forward_hooks(state, module)
    _register_post_forward_hooks(state, module)
    _register_root_pre_forward_hook(state, module)  # prepend last
    # Always insert the state for the passed-in module even if it has no
    # managed parameters, in which case it has no handles and does not appear
    # in `_fully_sharded_module_to_handles`
    _insert_module_state(module, state)
    for submodule in module.modules():
        if (
            submodule in state._fully_sharded_module_to_handles
            and _get_module_state(submodule) is None
        ):
            _insert_module_state(submodule, state)
    return module
