"""
Contains utility functions for working with nested python data structures.

A *pytree* is Python nested data structure. It is a tree in the sense that
nodes are Python collections (e.g., list, tuple, dict) and the leaves are
Python values. Furthermore, a pytree should not contain reference cycles.

pytrees are useful for working with nested collections of Tensors. For example,
one can use `tree_map` to map a function over all Tensors inside some nested
collection of Tensors and `tree_leaves` to get a flat list of all Tensors
inside some nested collection. pytrees are helpful for implementing nested
collection support for PyTorch APIs.

This pytree implementation is not very performant due to Python overhead
To improve the performance we can move parts of the implementation to C++.
"""

import dataclasses
import inspect
import json
import warnings
from collections import deque, namedtuple, OrderedDict
from typing import (
    Any,
    Callable,
    cast,
    Dict,
    Iterable,
    List,
    NamedTuple,
    Optional,
    OrderedDict as GenericOrderedDict,
    overload,
    Tuple,
    Type,
    TypeVar,
    Union,
)


__all__ = [
    "PyTree",
    "Context",
    "FlattenFunc",
    "UnflattenFunc",
    "DumpableContext",
    "ToDumpableContextFn",
    "FromDumpableContextFn",
    "TreeSpec",
    "LeafSpec",
    "register_pytree_node",
    "tree_flatten",
    "tree_unflatten",
    "tree_leaves",
    "tree_structure",
    "tree_map",
    "tree_map_",
    "tree_map_only",
    "tree_map_only_",
    "tree_all",
    "tree_any",
    "tree_all_only",
    "tree_any_only",
    "treespec_dumps",
    "treespec_loads",
    "treespec_pprint",
]


T = TypeVar("T")
S = TypeVar("S")
U = TypeVar("U")
R = TypeVar("R")


DEFAULT_TREESPEC_SERIALIZATION_PROTOCOL = 1

Context = Any
PyTree = Any
FlattenFunc = Callable[[PyTree], Tuple[List, Context]]
UnflattenFunc = Callable[[Iterable, Context], PyTree]
DumpableContext = Any  # Any json dumpable text
ToDumpableContextFn = Callable[[Context], DumpableContext]
FromDumpableContextFn = Callable[[DumpableContext], Context]
ToStrFunc = Callable[["TreeSpec", List[str]], str]
MaybeFromStrFunc = Callable[[str], Optional[Tuple[Any, Context, str]]]


# A NodeDef holds two callables:
# - flatten_fn should take the collection and return a flat list of values.
#   It can also return some context that is used in reconstructing the
#   collection.
# - unflatten_fn should take a flat list of values and some context
#   (returned by flatten_fn). It returns the collection by reconstructing
#   it from the list and the context.
class NodeDef(NamedTuple):
    type: Type[Any]
    flatten_fn: FlattenFunc
    unflatten_fn: UnflattenFunc


# _SerializeNodeDef holds the following:
# - typ: the type of the node (e.g., "Dict", "List", etc)
# - type_fqn: the fully qualified name of the type, e.g. "collections.OrderedDict"
# - to_dumpable_context takes a TreeSpec, and returns a serialized string format of the
#   context, and the version number
# - from_dumpable_context takes in a string representation of the context, and the
#   version, and returns the deserialized context
class _SerializeNodeDef(NamedTuple):
    typ: Type[Any]
    type_fqn: str
    to_dumpable_context: Optional[ToDumpableContextFn]
    from_dumpable_context: Optional[FromDumpableContextFn]


def _register_pytree_node(
    cls: Any,
    flatten_func: FlattenFunc,
    unflatten_func: UnflattenFunc,
    to_str_fn: Optional[ToStrFunc] = None,  # deprecated
    maybe_from_str_fn: Optional[MaybeFromStrFunc] = None,  # deprecated
    *,
    to_dumpable_context: Optional[ToDumpableContextFn] = None,
    from_dumpable_context: Optional[FromDumpableContextFn] = None,
) -> None:
    """
    Args:
        cls: the type to register
        flatten_func: A callable that takes a pytree and returns a flattened
            representation of the pytree and additional context to represent the
            flattened pytree.
        unflatten_func: A callable that takes a flattened version of the pytree,
            additional context, and returns an unflattened pytree.
        to_dumpable_context: An optional keyword argument to custom specify how
            to convert the context of the pytree to a custom json dumpable
            representation. This is used for json serialization, which is being
            used in torch.export right now.
        from_dumpable_context: An optional keyword argument to custom specify how
            to convert the custom json dumpable representation of the context
            back to the original context. This is used for json deserialization,
            which is being used in torch.export right now.
    """
    if to_str_fn is not None or maybe_from_str_fn is not None:
        warnings.warn(
            "to_str_fn and maybe_from_str_fn is deprecated. "
            "Please use to_dumpable_context and from_dumpable_context instead."
        )

    if cls in SUPPORTED_NODES:
        raise ValueError(f"{cls} is already registered as pytree node.")

    node_def = NodeDef(
        cls,
        flatten_func,
        unflatten_func,
    )
    SUPPORTED_NODES[cls] = node_def

    if (to_dumpable_context is None) ^ (from_dumpable_context is None):
        raise ValueError(
            f"Both to_dumpable_context and from_dumpable_context for {cls} must "
            "be None or registered."
        )

    type_fqn = f"{cls.__module__}.{cls.__qualname__}"
    serialize_node_def = _SerializeNodeDef(
        cls,
        type_fqn,
        to_dumpable_context,
        from_dumpable_context,
    )
    SUPPORTED_SERIALIZED_TYPES[cls] = serialize_node_def
    SERIALIZED_TYPE_TO_PYTHON_TYPE[type_fqn] = cls

    import torch

    if torch._running_with_deploy():
        return

    try:
        from . import _cxx_pytree as cxx
    except ImportError:
        pass
    else:
        current_frame = inspect.currentframe()
        previous_frame = current_frame.f_back if current_frame is not None else None
        if previous_frame is not None and inspect.getmodule(previous_frame) is not cxx:
            cxx.register_pytree_node(
                cls,
                flatten_func,
                unflatten_func,
                to_dumpable_context=to_dumpable_context,
                from_dumpable_context=from_dumpable_context,
            )


register_pytree_node = _register_pytree_node


def _dict_flatten(d: Dict[Any, Any]) -> Tuple[List[Any], Context]:
    return list(d.values()), list(d.keys())


def _dict_unflatten(values: Iterable[Any], context: Context) -> Dict[Any, Any]:
    return dict(zip(context, values))


def _list_flatten(d: List[Any]) -> Tuple[List[Any], Context]:
    return d, None


def _list_unflatten(values: Iterable[Any], context: Context) -> List[Any]:
    return list(values)


def _tuple_flatten(d: Tuple[Any, ...]) -> Tuple[List[Any], Context]:
    return list(d), None


def _tuple_unflatten(values: Iterable[Any], context: Context) -> Tuple[Any, ...]:
    return tuple(values)


def _namedtuple_flatten(d: NamedTuple) -> Tuple[List[Any], Context]:
    return list(d), type(d)


def _namedtuple_unflatten(values: Iterable[Any], context: Context) -> NamedTuple:
    return cast(NamedTuple, context(*values))


def _namedtuple_serialize(context: Context) -> DumpableContext:
    json_namedtuple = {
        "class_name": context.__name__,
        "fields": context._fields,
    }
    return json_namedtuple


def _namedtuple_deserialize(dumpable_context: DumpableContext) -> Context:
    class_name = dumpable_context["class_name"]
    assert isinstance(class_name, str)
    context = namedtuple(class_name, dumpable_context["fields"])  # type: ignore[misc]
    return context


def _odict_flatten(d: GenericOrderedDict[Any, Any]) -> Tuple[List[Any], Context]:
    return list(d.values()), list(d.keys())


def _odict_unflatten(
    values: Iterable[Any],
    context: Context,
) -> GenericOrderedDict[Any, Any]:
    return OrderedDict((key, value) for key, value in zip(context, values))


SUPPORTED_NODES: Dict[Type[Any], NodeDef] = {
    dict: NodeDef(dict, _dict_flatten, _dict_unflatten),
    list: NodeDef(list, _list_flatten, _list_unflatten),
    tuple: NodeDef(tuple, _tuple_flatten, _tuple_unflatten),
    namedtuple: NodeDef(namedtuple, _namedtuple_flatten, _namedtuple_unflatten),  # type: ignore[dict-item,arg-type]
    OrderedDict: NodeDef(OrderedDict, _odict_flatten, _odict_unflatten),
}
SUPPORTED_SERIALIZED_TYPES: Dict[Type[Any], _SerializeNodeDef] = {
    namedtuple: _SerializeNodeDef(  # type: ignore[dict-item]
        namedtuple,  # type: ignore[arg-type]
        f"{namedtuple.__module__}.{namedtuple.__qualname__}",
        _namedtuple_serialize,
        _namedtuple_deserialize,
    )
}
SERIALIZED_TYPE_TO_PYTHON_TYPE: Dict[str, Type[Any]] = {
    f"{namedtuple.__module__}.{namedtuple.__qualname__}": namedtuple  # type: ignore[dict-item]
}


# h/t https://stackoverflow.com/questions/2166818/how-to-check-if-an-object-is-an-instance-of-a-namedtuple
def _is_namedtuple_instance(tree: Any) -> bool:
    typ = type(tree)
    bases = typ.__bases__
    if len(bases) != 1 or bases[0] != tuple:
        return False
    fields = getattr(typ, "_fields", None)
    if not isinstance(fields, tuple):
        return False
    return all(type(entry) == str for entry in fields)


def _get_node_type(tree: Any) -> Any:
    if _is_namedtuple_instance(tree):
        return namedtuple
    return type(tree)


# A leaf is defined as anything that is not a Node.
def _is_leaf(tree: PyTree) -> bool:
    return _get_node_type(tree) not in SUPPORTED_NODES


# A TreeSpec represents the structure of a pytree. It holds:
# "type": the type of root Node of the pytree
# context: some context that is useful in unflattening the pytree
# children_specs: specs for each child of the root Node
# num_leaves: the number of leaves
@dataclasses.dataclass
class TreeSpec:
    type: Any
    context: Context
    children_specs: List["TreeSpec"]

    def __post_init__(self) -> None:
        self.num_leaves: int = sum([spec.num_leaves for spec in self.children_specs])

    def __repr__(self, indent: int = 0) -> str:
        repr_prefix: str = f"TreeSpec({self.type.__name__}, {self.context}, ["
        children_specs_str: str = ""
        if len(self.children_specs):
            indent += 2
            children_specs_str += self.children_specs[0].__repr__(indent)
            children_specs_str += "," if len(self.children_specs) > 1 else ""
            children_specs_str += ",".join(
                [
                    "\n" + " " * indent + child.__repr__(indent)
                    for child in self.children_specs[1:]
                ]
            )
        repr_suffix: str = f"{children_specs_str}])"
        return repr_prefix + repr_suffix

    def is_leaf(self) -> bool:
        return isinstance(self, LeafSpec)


class LeafSpec(TreeSpec):
    def __init__(self) -> None:
        super().__init__(None, None, [])
        self.num_leaves = 1

    def __repr__(self, indent: int = 0) -> str:
        return "*"


# All leaves are equivalent, so represent with a single object to save on
# object construction time
_LEAF_SPEC = LeafSpec()


def _tree_flatten_helper(tree: PyTree, leaves: List[Any]) -> TreeSpec:
    if _is_leaf(tree):
        leaves.append(tree)
        return _LEAF_SPEC

    node_type = _get_node_type(tree)
    flatten_fn = SUPPORTED_NODES[node_type].flatten_fn
    child_pytrees, context = flatten_fn(tree)

    # Recursively flatten the children
    children_specs = [_tree_flatten_helper(child, leaves) for child in child_pytrees]

    return TreeSpec(node_type, context, children_specs)


def tree_flatten(tree: PyTree) -> Tuple[List[Any], TreeSpec]:
    """Flattens a pytree into a list of values and a TreeSpec that can be used
    to reconstruct the pytree.
    """
    leaves: List[Any] = []
    spec = _tree_flatten_helper(tree, leaves)
    return leaves, spec


def _tree_leaves_helper(tree: PyTree, leaves: List[Any]) -> None:
    if _is_leaf(tree):
        leaves.append(tree)
        return

    node_type = _get_node_type(tree)
    flatten_fn = SUPPORTED_NODES[node_type].flatten_fn
    child_pytrees, _ = flatten_fn(tree)

    # Recursively flatten the children
    for child in child_pytrees:
        _tree_leaves_helper(child, leaves)


def tree_unflatten(leaves: Iterable[Any], treespec: TreeSpec) -> PyTree:
    """Given a list of values and a TreeSpec, builds a pytree.
    This is the inverse operation of `tree_flatten`.
    """
    if not isinstance(treespec, TreeSpec):
        raise TypeError(
            f"tree_unflatten(leaves, treespec): Expected `treespec` to be "
            f"instance of TreeSpec but got item of type {type(treespec)}.",
        )
    if not isinstance(leaves, (list, tuple)):
        leaves = list(leaves)
    if len(leaves) != treespec.num_leaves:
        raise ValueError(
            f"tree_unflatten(leaves, treespec): `leaves` has length {len(leaves)} "
            f"but the spec refers to a pytree that holds {treespec.num_leaves} "
            f"items ({treespec}).",
        )
    if isinstance(treespec, LeafSpec):
        return leaves[0]

    unflatten_fn = SUPPORTED_NODES[treespec.type].unflatten_fn

    # Recursively unflatten the children
    start = 0
    end = 0
    child_pytrees = []
    for child_spec in treespec.children_specs:
        end += child_spec.num_leaves
        child_pytrees.append(tree_unflatten(leaves[start:end], child_spec))
        start = end

    return unflatten_fn(child_pytrees, treespec.context)


def tree_leaves(tree: PyTree) -> List[Any]:
    """Get a list of leaves of a pytree."""
    leaves: List[Any] = []
    _tree_leaves_helper(tree, leaves)
    return leaves


def tree_structure(tree: PyTree) -> TreeSpec:
    """Get the TreeSpec for a pytree."""
    return tree_flatten(tree)[1]


def tree_map(func: Any, tree: PyTree) -> PyTree:
    flat_args, spec = tree_flatten(tree)
    return tree_unflatten([func(i) for i in flat_args], spec)


def tree_map_(func: Any, tree: PyTree) -> PyTree:
    flat_args = tree_leaves(tree)
    deque(map(func, flat_args), maxlen=0)  # consume and exhaust the iterable
    return tree


Type2 = Tuple[Type[T], Type[S]]
Type3 = Tuple[Type[T], Type[S], Type[U]]
TypeAny = Union[Type[Any], Tuple[Type[Any], ...]]

Fn2 = Callable[[Union[T, S]], R]
Fn3 = Callable[[Union[T, S, U]], R]
Fn = Callable[[T], R]
FnAny = Callable[[Any], R]

MapOnlyFn = Callable[[T], Callable[[Any], Any]]


# These specializations help with type inference on the lambda passed to this
# function
@overload
def map_only(__type_or_types: Type2[T, S]) -> MapOnlyFn[Fn2[T, S, Any]]:
    ...


@overload
def map_only(__type_or_types: Type3[T, S, U]) -> MapOnlyFn[Fn3[T, S, U, Any]]:
    ...


@overload
def map_only(__type_or_types: Type[T]) -> MapOnlyFn[Fn[T, Any]]:
    ...


# This specialization is needed for the implementations below that call
@overload
def map_only(__type_or_types: TypeAny) -> MapOnlyFn[FnAny[Any]]:
    ...


def map_only(__type_or_types: TypeAny) -> MapOnlyFn[FnAny[Any]]:
    """
    Suppose you are writing a tree_map over tensors, leaving everything
    else unchanged.  Ordinarily you would have to write:

        def go(t):
            if isinstance(t, Tensor):
                return ...
            else:
                return t

    With this function, you only need to write:

        @map_only(Tensor)
        def go(t):
            return ...

    You can also directly use 'tree_map_only'
    """

    def wrapper(func: Callable[[T], Any]) -> Callable[[Any], Any]:
        # @functools.wraps(func)  # torch dynamo doesn't support this yet
        def wrapped(x: T) -> Any:
            if isinstance(x, __type_or_types):
                return func(x)
            return x

        return wrapped

    return wrapper


@overload
def tree_map_only(
    __type_or_types: Type[T],
    func: Fn[T, Any],
    tree: PyTree,
) -> PyTree:
    ...


@overload
def tree_map_only(
    __type_or_types: Type2[T, S],
    func: Fn2[T, S, Any],
    tree: PyTree,
) -> PyTree:
    ...


@overload
def tree_map_only(
    __type_or_types: Type3[T, S, U],
    func: Fn3[T, S, U, Any],
    tree: PyTree,
) -> PyTree:
    ...


def tree_map_only(
    __type_or_types: TypeAny,
    func: FnAny[Any],
    tree: PyTree,
) -> PyTree:
    return tree_map(map_only(__type_or_types)(func), tree)


@overload
def tree_map_only_(
    __type_or_types: Type[T],
    func: Fn[T, Any],
    tree: PyTree,
) -> PyTree:
    ...


@overload
def tree_map_only_(
    __type_or_types: Type2[T, S],
    func: Fn2[T, S, Any],
    tree: PyTree,
) -> PyTree:
    ...


@overload
def tree_map_only_(
    __type_or_types: Type3[T, S, U],
    func: Fn3[T, S, U, Any],
    tree: PyTree,
) -> PyTree:
    ...


def tree_map_only_(
    __type_or_types: TypeAny,
    func: FnAny[Any],
    tree: PyTree,
) -> PyTree:
    return tree_map_(map_only(__type_or_types)(func), tree)


def tree_all(pred: Callable[[Any], bool], tree: PyTree) -> bool:
    flat_args = tree_leaves(tree)
    return all(map(pred, flat_args))


def tree_any(pred: Callable[[Any], bool], tree: PyTree) -> bool:
    flat_args = tree_leaves(tree)
    return any(map(pred, flat_args))


@overload
def tree_all_only(
    __type_or_types: Type[T],
    pred: Fn[T, bool],
    tree: PyTree,
) -> bool:
    ...


@overload
def tree_all_only(
    __type_or_types: Type2[T, S],
    pred: Fn2[T, S, bool],
    tree: PyTree,
) -> bool:
    ...


@overload
def tree_all_only(
    __type_or_types: Type3[T, S, U],
    pred: Fn3[T, S, U, bool],
    tree: PyTree,
) -> bool:
    ...


def tree_all_only(
    __type_or_types: TypeAny,
    pred: FnAny[bool],
    tree: PyTree,
) -> bool:
    flat_args = tree_leaves(tree)
    return all(pred(x) for x in flat_args if isinstance(x, __type_or_types))


@overload
def tree_any_only(
    __type_or_types: Type[T],
    pred: Fn[T, bool],
    tree: PyTree,
) -> bool:
    ...


@overload
def tree_any_only(
    __type_or_types: Type2[T, S],
    pred: Fn2[T, S, bool],
    tree: PyTree,
) -> bool:
    ...


@overload
def tree_any_only(
    __type_or_types: Type3[T, S, U],
    pred: Fn3[T, S, U, bool],
    tree: PyTree,
) -> bool:
    ...


def tree_any_only(
    __type_or_types: TypeAny,
    pred: FnAny[bool],
    tree: PyTree,
) -> bool:
    flat_args = tree_leaves(tree)
    return any(pred(x) for x in flat_args if isinstance(x, __type_or_types))


# Broadcasts a pytree to the provided TreeSpec and returns the flattened
# values. If this is not possible, then this function returns None.
#
# For example, given pytree=0 and spec=TreeSpec(list, None, [LeafSpec(), LeafSpec()]),
# would return [0, 0]. This is useful for part of the vmap implementation:
# a user can pass in vmap(fn, in_dims)(*inputs). `in_dims` should be
# broadcastable to the tree structure of `inputs` and we use
# _broadcast_to_and_flatten to check this.
def _broadcast_to_and_flatten(tree: PyTree, treespec: TreeSpec) -> Optional[List[Any]]:
    assert isinstance(treespec, TreeSpec)

    if _is_leaf(tree):
        return [tree] * treespec.num_leaves
    if isinstance(treespec, LeafSpec):
        return None
    node_type = _get_node_type(tree)
    if node_type != treespec.type:
        return None

    flatten_fn = SUPPORTED_NODES[node_type].flatten_fn
    child_pytrees, ctx = flatten_fn(tree)

    # Check if the Node is different from the spec
    if len(child_pytrees) != len(treespec.children_specs) or ctx != treespec.context:
        return None

    # Recursively flatten the children
    result: List[Any] = []
    for child, child_spec in zip(child_pytrees, treespec.children_specs):
        flat = _broadcast_to_and_flatten(child, child_spec)
        if flat is not None:
            result += flat
        else:
            return None

    return result


@dataclasses.dataclass
class _TreeSpecSchema:
    """
    _TreeSpecSchema is the schema used to serialize the TreeSpec
    It contains the following fields:
    - type: A string name of the type. null for the case of a LeafSpec.
    - context: Any format which is json dumpable
    - children_spec: A list of children serialized specs.
    """

    type: Optional[str]
    context: DumpableContext
    children_spec: List["_TreeSpecSchema"]


class _ProtocolFn(NamedTuple):
    treespec_to_json: Callable[[TreeSpec], DumpableContext]
    json_to_treespec: Callable[[DumpableContext], TreeSpec]


_SUPPORTED_PROTOCOLS: Dict[int, _ProtocolFn] = {}


def _treespec_to_json(treespec: TreeSpec) -> _TreeSpecSchema:
    if isinstance(treespec, LeafSpec):
        return _TreeSpecSchema(None, None, [])

    if treespec.type not in SUPPORTED_SERIALIZED_TYPES:
        raise NotImplementedError(
            f"Serializing {treespec.type} in pytree is not registered."
        )

    serialize_node_def = SUPPORTED_SERIALIZED_TYPES[treespec.type]

    type_fqn = serialize_node_def.type_fqn

    if serialize_node_def.to_dumpable_context is None:
        try:
            serialized_context = json.dumps(treespec.context)
        except TypeError as e:
            raise TypeError(
                "Unable to serialize context. "
                "Please make the context json dump-able, or register a "
                "custom serializer using _register_pytree_node."
            ) from e
    else:
        serialized_context = serialize_node_def.to_dumpable_context(treespec.context)

    child_schemas = [_treespec_to_json(child) for child in treespec.children_specs]

    return _TreeSpecSchema(type_fqn, serialized_context, child_schemas)


def _json_to_treespec(json_schema: DumpableContext) -> TreeSpec:
    if (
        json_schema["type"] is None
        and json_schema["context"] is None
        and len(json_schema["children_spec"]) == 0
    ):
        return LeafSpec()

    if json_schema["type"] not in SERIALIZED_TYPE_TO_PYTHON_TYPE:
        raise NotImplementedError(
            f'Deserializing {json_schema["type"]} in pytree is not registered.',
        )

    typ = SERIALIZED_TYPE_TO_PYTHON_TYPE[json_schema["type"]]
    serialize_node_def = SUPPORTED_SERIALIZED_TYPES[typ]

    if serialize_node_def.from_dumpable_context is None:
        try:
            context = json.loads(json_schema["context"])
        except TypeError as ex:
            raise TypeError(
                "Unable to deserialize context. "
                "Please make the context json load-able, or register a "
                "custom serializer using _register_pytree_node.",
            ) from ex
    else:
        context = serialize_node_def.from_dumpable_context(json_schema["context"])

    children_spec = []
    for child_string in json_schema["children_spec"]:
        children_spec.append(_json_to_treespec(child_string))

    return TreeSpec(typ, context, children_spec)


_SUPPORTED_PROTOCOLS[1] = _ProtocolFn(_treespec_to_json, _json_to_treespec)


def treespec_dumps(treespec: TreeSpec, protocol: Optional[int] = None) -> str:
    if not isinstance(treespec, TreeSpec):
        raise TypeError(
            f"treespec_dumps(treespec, protocol): Expected `treespec` to be instance of "
            f"TreeSpec but got item of type {type(treespec)}.",
        )

    if protocol is None:
        protocol = DEFAULT_TREESPEC_SERIALIZATION_PROTOCOL

    if protocol in _SUPPORTED_PROTOCOLS:
        json_spec = _SUPPORTED_PROTOCOLS[protocol].treespec_to_json(treespec)
    else:
        raise ValueError(
            f"Unknown protocol {protocol}. "
            f"Available protocols: {list(_SUPPORTED_PROTOCOLS.keys())}",
        )

    str_spec = json.dumps((protocol, dataclasses.asdict(json_spec)))
    return str_spec


def treespec_loads(data: str) -> TreeSpec:
    protocol, json_schema = json.loads(data)

    if protocol in _SUPPORTED_PROTOCOLS:
        return _SUPPORTED_PROTOCOLS[protocol].json_to_treespec(json_schema)
    raise ValueError(
        f"Unknown protocol {protocol}. "
        f"Available protocols: {list(_SUPPORTED_PROTOCOLS.keys())}",
    )


class _DummyLeaf:
    def __repr__(self) -> str:
        return "*"


def treespec_pprint(treespec: TreeSpec) -> str:
    dummy_tree = tree_unflatten(
        [_DummyLeaf() for _ in range(treespec.num_leaves)],
        treespec,
    )
    return repr(dummy_tree)


# TODO(angelayi): remove this function after OSS/internal stabilize
def pytree_to_str(treespec: TreeSpec) -> str:
    warnings.warn("pytree_to_str is deprecated. Please use treespec_dumps")
    return treespec_dumps(treespec)


# TODO(angelayi): remove this function after OSS/internal stabilize
def str_to_pytree(json: str) -> TreeSpec:
    warnings.warn("str_to_pytree is deprecated. Please use treespec_loads")
    return treespec_loads(json)
