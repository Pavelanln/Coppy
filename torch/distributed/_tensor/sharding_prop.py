from functools import lru_cache
from itertools import chain
from typing import Callable, cast, Dict, List, Optional, Sequence, Tuple, Union

import torch
from torch._ops import OpOverload
from torch._subclasses import FakeTensorMode
from torch.distributed._tensor.device_mesh import DeviceMesh
from torch.distributed._tensor.op_schema import (
    DTensorSpec,
    OpInfo,
    OpSchema,
    OpStrategy,
    OutputSharding,
    OutputSpecType,
    PlacementStrategy,
    RuntimeSchemaInfo,
    StrategyType,
    TupleStrategy,
)
from torch.distributed._tensor.placement_types import TensorMeta

aten = torch.ops.aten


def _length(obj) -> int:
    if obj is None:
        return 0
    if not isinstance(obj, Sequence):
        return 1
    return len(obj)


class ShardingPropagator:
    def __init__(self) -> None:
        self.op_to_rules: Dict[OpOverload, Callable[[OpSchema], OutputSharding]] = {}
        self.op_strategy_funcs: Dict[
            OpOverload,
            Callable[[DeviceMesh, OpSchema], StrategyType],
        ] = {}
        # op map to save static argnum to decide to reuse sharding prop cache or re-run sharding prop
        self.op_to_schema_info: Dict[OpOverload, RuntimeSchemaInfo] = {}
        self.propagate_op_sharding = lru_cache(None)(self.propagate_op_sharding_non_cached)  # type: ignore[method-assign]

    def register_sharding_prop_rule(
        self,
        op_overload: OpOverload,
        rule_func: Callable[[OpSchema], OutputSharding],
        schema_info: Optional[RuntimeSchemaInfo] = None,
    ):
        """
        Register a sharding propagation rule for an operator.
        """
        self.op_to_rules[op_overload] = rule_func
        if schema_info is not None:
            self.op_to_schema_info[op_overload] = schema_info

    def register_op_strategy(
        self,
        op_overload: OpOverload,
        strategy_func: Callable[[DeviceMesh, OpSchema], StrategyType],
        schema_info: Optional[RuntimeSchemaInfo] = None,
    ):
        """
        Register a sharding strategy generator for an operator.
        """
        self.op_strategy_funcs[op_overload] = strategy_func
        if schema_info is not None:
            self.op_to_schema_info[op_overload] = schema_info

    def _propagate_tensor_meta(
        self, op_schema: OpSchema
    ) -> Union[None, TensorMeta, List[TensorMeta], Tuple[TensorMeta, ...]]:
        """
        Propagate the tensor metadata, it could either return a TensorMeta
        or a list/tuple of TensorMetas
        """
        # NOTE: We must call the tracing in fake tensor mode so that it
        # avoids materializing memory
        with FakeTensorMode():
            fake_args = op_schema.gen_fake_args()
            fake_kwargs = op_schema.gen_fake_kwargs()
            fake_out = op_schema.op(*fake_args, **fake_kwargs)

        if isinstance(fake_out, torch.Tensor):
            return TensorMeta(
                shape=fake_out.shape, stride=fake_out.stride(), dtype=fake_out.dtype
            )

        elif isinstance(fake_out, (tuple, list)):
            tensor_meta_list = []
            for fake_out_item in fake_out:
                if isinstance(fake_out_item, torch.Tensor):
                    tensor_meta_list.append(
                        TensorMeta(
                            shape=fake_out_item.shape,
                            stride=fake_out_item.stride(),
                            dtype=fake_out_item.dtype,
                        )
                    )
            return (
                tuple(tensor_meta_list)
                if isinstance(fake_out, tuple)
                else tensor_meta_list
            )
        else:
            # if fake is not a tensor or tuple of tensor, return as none
            return None

    def _wrap_output_spec_tensor_meta(
        self,
        op: OpOverload,
        output_spec: OutputSpecType,
        output_tensor_meta: Union[
            None, TensorMeta, List[TensorMeta], Tuple[TensorMeta, ...]
        ],
    ) -> None:
        """
        Wrap the output_spec with the tensor metadata from the output.
        """

        if isinstance(output_spec, DTensorSpec):
            if not isinstance(output_tensor_meta, TensorMeta):
                # Either error due to ShardingPropagator or due to incorrect OutputSpec
                if not isinstance(output_tensor_meta, (tuple, list)):
                    raise ValueError(
                        "ShardingPropagator error: output does not have an associated TensorMeta"
                    )
                raise ValueError(
                    f"For the op {op.name()}, `output_spec` has 1 output which does not equal the "
                    f"number of op outputs: {len(output_tensor_meta)}."
                )
            output_spec.tensor_meta = output_tensor_meta
        elif isinstance(output_spec, (tuple, list)):
            if not isinstance(
                output_tensor_meta,
                (tuple, list) or len(output_spec) != len(output_tensor_meta),
            ):
                raise ValueError(
                    f"For the op {op.name()}, `output_spec` has {len(output_spec)} outputs which does not equal the "
                    f"number of op outputs {_length(output_tensor_meta)}."
                )
            for i, spec in enumerate(output_spec):
                if isinstance(spec, DTensorSpec):
                    output_tensor_meta_i = output_tensor_meta[i]
                    if not isinstance(output_tensor_meta_i, TensorMeta):
                        raise ValueError(
                            f"ShardingPropagator error: output {i} does not have an associated TensorMeta"
                        )
                    spec.tensor_meta = output_tensor_meta_i

    def propagate(self, op_info: OpInfo) -> None:
        # We cannot use an lru cache if we know that inputs will have dynamic shapes,
        # because SymInts are not hashable.
        # This is generally ok because this only happens during tracing in torch.compile,
        # and tracing does not need to be as fast as eagermode DTensor usages.
        if op_info.schema.has_symints:
            output_sharding = self.propagate_op_sharding_non_cached(op_info.schema)
        else:
            output_sharding = self.propagate_op_sharding(op_info.schema)
        op_info.output_sharding = output_sharding

    def propagate_op_sharding_non_cached(self, op_schema: OpSchema) -> OutputSharding:
        """
        Propagate the sharding for an operator given the op_schema.
        """
        # special case op list, we don't need to propagate for local
        # scalar. TODO: figure out a better way to handle this
        skip_prop_list = {
            aten._local_scalar_dense.default,
            aten.equal.default,
            aten.is_same_size.default,
        }
        if op_schema.op in skip_prop_list:
            return OutputSharding(None, [op_schema])

        out_tensor_meta = self._propagate_tensor_meta(op_schema)

        def spec_to_strategy(spec: object) -> object:
            if isinstance(spec, DTensorSpec):
                return OpStrategy([PlacementStrategy(spec)])
            elif isinstance(spec, (list, tuple)) and isinstance(spec[0], DTensorSpec):
                # tensor list create tuple strategy
                tuple_strategy = [spec_to_strategy(s) for s in spec]
                tuple_strategy = cast(Sequence[StrategyType], tuple_strategy)
                return TupleStrategy(
                    tuple(tuple_strategy) if isinstance(spec, tuple) else tuple_strategy
                )
            else:
                return spec

        if op_schema.op in self.op_strategy_funcs:
            # generate op strategy for the op.
            mesh = None
            for arg in op_schema.args_schema:
                if isinstance(arg, DTensorSpec):
                    mesh = arg.mesh
                    break
                elif isinstance(arg, (list, tuple)) and isinstance(arg[0], DTensorSpec):
                    mesh = arg[0].mesh
                    break

            assert mesh is not None, f"Cannot find mesh for op {op_schema.op}"

            # swap the args spec with args strategies
            args_op_strategy = [spec_to_strategy(i) for i in op_schema.args_schema]

            kwargs_op_strategy = {
                k: spec_to_strategy(v) for k, v in op_schema.kwargs_schema.items()
            }

            # construct a new OpSchema on args for strategy based propagation
            strategy_schema: OpSchema = OpSchema(
                op=op_schema.op,
                args_schema=tuple(args_op_strategy),
                kwargs_schema=kwargs_op_strategy,
            )

            op_strategy = self.op_strategy_funcs[op_schema.op](mesh, strategy_schema)

            if isinstance(op_strategy, OpStrategy):
                # single Op strategy
                output_strategy = self._select_strategy(op_strategy)

                needs_redistribute = False
                expected_input_specs = []
                for idx, input_spec in enumerate(op_schema.args_spec):
                    desired_spec = (
                        output_strategy.output_spec
                        if output_strategy.input_specs is None
                        else output_strategy.input_specs[idx]
                    )
                    expected_input_specs.append(desired_spec)
                    if input_spec.placements != desired_spec.placements:
                        needs_redistribute = True

                suggestion_schema = None
                if needs_redistribute:
                    reshard_schema = OpSchema(
                        op_schema.op, tuple(expected_input_specs), {}
                    )
                    reshard_schema._inplace_rewrap_schema_suggestion(op_schema)
                    suggestion_schema = [reshard_schema]

                if op_schema.return_type_tuple_tensors():
                    # for ops return multiple tensors, make output spec return same spec
                    # returned from the op strategy
                    output_spec: OutputSpecType = tuple(
                        [
                            output_strategy.output_spec
                            for _ in range(len(op_schema.op._schema.returns))
                        ]
                    )
                else:
                    output_spec = output_strategy.output_spec

                output_sharding = OutputSharding(
                    output_spec,
                    suggestion_schema,
                    needs_redistribute=needs_redistribute,
                )
            elif isinstance(op_strategy, TupleStrategy):
                # tuple strategy output sharding
                out_spec_list = []
                for strategy in op_strategy.childs:
                    assert isinstance(strategy, OpStrategy)
                    output_strategy = self._select_strategy(strategy)
                    out_spec_list.append(output_strategy.output_spec)

                needs_redistribute = False
                suggestion_args: List[object] = []
                for arg in op_schema.args_schema:
                    if isinstance(arg, (list, tuple)) and isinstance(
                        arg[0], DTensorSpec
                    ):
                        expected_input_spec_list = []
                        for idx, arg_spec in enumerate(arg):
                            if arg_spec.placements != out_spec_list[idx].placements:
                                needs_redistribute = True
                            expected_input_spec_list.append(out_spec_list[idx])
                        suggestion_args.append(
                            tuple(expected_input_spec_list)
                            if isinstance(arg, tuple)
                            else expected_input_spec_list
                        )
                    elif isinstance(arg, DTensorSpec):
                        expected_input_spec = out_spec_list[0]
                        if arg.placements != expected_input_spec.placements:
                            needs_redistribute = True
                        suggestion_args.append(expected_input_spec)
                    else:
                        suggestion_args.append(arg)

                suggestion_schema = None
                if needs_redistribute:
                    reshard_schema = OpSchema(
                        op_schema.op, tuple(suggestion_args), op_schema.kwargs_schema
                    )
                    # reshard_schema._inplace_rewrap_schema_suggestion(op_schema)
                    suggestion_schema = [reshard_schema]

                output_sharding = OutputSharding(
                    tuple(out_spec_list) if out_tensor_meta is not None else None,
                    suggestion_schema,
                    needs_redistribute=needs_redistribute,
                )
            else:
                raise ValueError("Unsupported op strategy type")

            # associate the output sharding with the output tensor metadata
            self._wrap_output_spec_tensor_meta(
                op_schema.op, output_sharding.output_spec, out_tensor_meta
            )
            return output_sharding
        elif op_schema.op in self.op_to_rules:
            # propagate the sharding with rule
            sharding_prop_func = self.op_to_rules[op_schema.op]

            # step 1. there's sharding propagation rule, run
            # sharding propagation to get the output sharding
            try:
                output_sharding = sharding_prop_func(op_schema)
            except NotImplementedError as e:
                raise e
            except Exception as e:
                raise RuntimeError(
                    f"Sharding propagation failed on op {op_schema}.\n" f"Error: {e}"
                ) from e

            # step 2. if can't get output_spec from sharding
            # propagation (i.e. no rules apply for input
            # placements), we return the output sharding
            # with schema suggestions, which can be used to
            # decide how to do redistribute on inputs
            if output_sharding.output_spec is None:
                if output_sharding.schema_suggestions is None:
                    if output_sharding.failed_reason is not None:
                        raise RuntimeError(
                            f"Sharding propagation failed on op {op_schema}!"
                            f"Failed reason: {output_sharding.failed_reason}"
                        )
                else:
                    # we do auto redistribute on inputs if necessary
                    # to get an eligible input, which we will pick a
                    # schema suggestion base on the redistribute cost.
                    # For now we simply pick the first suggestion.
                    suggested_input_schema = output_sharding.schema_suggestions[0]
                    # run sharding propagation again with suggested schema
                    propagation_res = sharding_prop_func(suggested_input_schema)
                    # we set the output sharding with the new propagation result
                    # so that dispatching know both output_spec and schema_suggestions
                    # exist, which indicates a reshard is needed
                    output_sharding.output_spec = propagation_res.output_spec
                    output_sharding.needs_redistribute = True

            # associate the output sharding with the output tensor metadata
            self._wrap_output_spec_tensor_meta(
                op_schema.op, output_sharding.output_spec, out_tensor_meta
            )

            return output_sharding
        else:
            raise NotImplementedError(
                f"Operator {op_schema.op} does not have a sharding strategy registered."
            )

    def _select_strategy(self, strategy: OpStrategy) -> PlacementStrategy:
        if len(strategy.strategies) == 1:
            # short cut with only one possible strategy
            return strategy.strategies[0]

        strategy_costs: List[float] = []
        for strtg in strategy.strategies:
            assert (
                strtg.redistribute_cost is not None
            ), "must set redistribute cost each strategy!"
            redistribute_cost = sum(chain.from_iterable(strtg.redistribute_cost))
            strategy_costs.append(redistribute_cost)

        # for eager execution, we just select the one with the minimal redistribute cost
        return strategy.strategies[strategy_costs.index(min(strategy_costs))]
