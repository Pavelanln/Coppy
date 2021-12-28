# This base template ("dataset.pyi.in") is generated from mypy stubgen with minimal editing for code injection
# The output file will be "dataset.pyi".
# Note that, for mypy, .pyi file takes precedent over .py file, such that we must define the interface for other
# classes/objects here, even though we are not injecting extra code into them at the moment.

from ... import Generator as Generator, Tensor as Tensor
from torch import default_generator as default_generator, randperm as randperm
from torch.utils.data._typing import _DataPipeMeta
from typing import Any, Callable, Dict, Generic, Iterable, Iterator, List, Optional, Sequence, Tuple, TypeVar

T_co = TypeVar('T_co', covariant=True)
T = TypeVar('T')
UNTRACABLE_DATAFRAME_PIPES: Any


class DataChunk(list, Generic[T]):
    items: Any = ...
    def __init__(self, items: Any) -> None: ...
    def as_str(self, indent: str = ...): ...
    def __iter__(self) -> Iterator[T]: ...
    def raw_iterator(self) -> T: ...

class Dataset(Generic[T_co]):
    functions: Dict[str, Callable] = ...
    def __getitem__(self, index: Any) -> T_co: ...
    def __add__(self, other: Dataset[T_co]) -> ConcatDataset[T_co]: ...
    def __getattr__(self, attribute_name: Any): ...
    @classmethod
    def register_function(cls, function_name: Any, function: Any) -> None: ...
    @classmethod
    def register_datapipe_as_function(cls, function_name: Any, cls_to_register: Any, enable_df_api_tracing: bool = ...): ...

class MapDataPipe(Generic[T_co]):
    functions: Dict[str, Callable] = ...
    def __getitem__(self, index: Any) -> T_co: ...
    def __add__(self, other: Dataset[T_co]) -> ConcatDataset[T_co]: ...
    def __getattr__(self, attribute_name: Any): ...
    @classmethod
    def register_function(cls, function_name: Any, function: Any) -> None: ...
    @classmethod
    def register_datapipe_as_function(cls, function_name: Any, cls_to_register: Any, enable_df_api_tracing: bool = ...): ...
    # Functional form of 'BatcherMapDataPipe'
    def batch(self, batch_size: int, drop_last: bool = False, wrapper_class=DataChunk) -> MapDataPipe: ...
    # Functional form of 'ConcaterMapDataPipe'
    def concat(self, *datapipes: MapDataPipe) -> MapDataPipe: ...
    # Functional form of 'MapperMapDataPipe'
    def map(self, fn: Callable= ...) -> MapDataPipe: ...
    # Functional form of 'ShufflerMapDataPipe'
    def shuffle(self, *, indices: Optional[List] = None) -> MapDataPipe: ...
    # Functional form of 'ZipperMapDataPipe'
    def zip(self, *datapipes: MapDataPipe[T_co]) -> MapDataPipe: ...

class IterableDataset(Dataset[T_co], metaclass=_DataPipeMeta):
    functions: Dict[str, Callable] = ...
    reduce_ex_hook: Optional[Callable] = ...
    getstate_hook: Optional[Callable] = ...
    def __iter__(self) -> Iterator[T_co]: ...
    def __add__(self, other: Dataset[T_co]) -> Any: ...
    def __getattr__(self, attribute_name: Any): ...
    def __reduce_ex__(self, *args: Any, **kwargs: Any): ...
    @classmethod
    def set_reduce_ex_hook(cls, hook_fn: Any) -> None: ...
    @classmethod
    def set_getstate_hook(cls, hook_fn: Any) -> None: ...
    # Functional form of 'BatcherIterDataPipe'
    def batch(self, batch_size: int, drop_last: bool = False, wrapper_class=DataChunk) -> IterDataPipe: ...
    # Functional form of 'CollatorIterDataPipe'
    def collate(self, collate_fn: Callable= ...) -> IterDataPipe: ...
    # Functional form of 'ConcaterIterDataPipe'
    def concat(self, *datapipes: IterDataPipe) -> IterDataPipe: ...
    # Functional form of 'RoutedDecoderIterDataPipe'
    def decode(self, *handlers: Callable, key_fn: Callable= ...) -> IterDataPipe: ...
    # Functional form of 'DemultiplexerIterDataPipe'
    def demux(self, num_instances: int, classifier_fn: Callable[[T_co], Optional[int]], drop_none: bool = False, buffer_size: int = 1000) -> List[IterDataPipe]: ...
    # Functional form of 'FilterIterDataPipe'
    def filter(self, filter_fn: Callable, drop_empty_batches: bool = True) -> IterDataPipe: ...
    # Functional form of 'ForkerIterDataPipe'
    def fork(self, num_instances: int, buffer_size: int = 1000) -> List[IterDataPipe]: ...
    # Functional form of 'GrouperIterDataPipe'
    def groupby(self, group_key_fn: Callable, *, buffer_size: int = 10000, group_size: Optional[int] = None, guaranteed_group_size: Optional[int] = None, drop_remaining: bool = False) -> IterDataPipe: ...
    # Functional form of 'MapperIterDataPipe'
    def map(self, fn: Callable, input_col=None, output_col=None) -> IterDataPipe: ...
    # Functional form of 'MultiplexerIterDataPipe'
    def mux(self, *datapipes) -> IterDataPipe: ...
    # Functional form of 'ShardingFilterIterDataPipe'
    def sharding_filter(self) -> IterDataPipe: ...
    # Functional form of 'ShufflerIterDataPipe'
    def shuffle(self, *, default: bool = True, buffer_size: int = 10000, unbatch_level: int = 0) -> IterDataPipe: ...
    # Functional form of 'UnBatcherIterDataPipe'
    def unbatch(self, unbatch_level: int = 1) -> IterDataPipe: ...
    # Functional form of 'ZipperIterDataPipe'
    def zip(self, *datapipes: IterDataPipe) -> IterDataPipe: ...

IterDataPipe = IterableDataset

class DFIterDataPipe(IterableDataset): ...

class TensorDataset(Dataset[Tuple[Tensor, ...]]):
    tensors: Tuple[Tensor, ...]
    def __init__(self, *tensors: Tensor) -> None: ...
    def __getitem__(self, index: Any): ...
    def __len__(self): ...

class ConcatDataset(Dataset[T_co]):
    datasets: List[Dataset[T_co]]
    cumulative_sizes: List[int]
    @staticmethod
    def cumsum(sequence: Any): ...
    def __init__(self, datasets: Iterable[Dataset]) -> None: ...
    def __len__(self): ...
    def __getitem__(self, idx: Any): ...
    @property
    def cummulative_sizes(self): ...

class ChainDataset(IterableDataset):
    datasets: Any = ...
    def __init__(self, datasets: Iterable[Dataset]) -> None: ...
    def __iter__(self) -> Any: ...
    def __len__(self): ...

class Subset(Dataset[T_co]):
    dataset: Dataset[T_co]
    indices: Sequence[int]
    def __init__(self, dataset: Dataset[T_co], indices: Sequence[int]) -> None: ...
    def __getitem__(self, idx: Any): ...
    def __len__(self): ...

def random_split(dataset: Dataset[T], lengths: Sequence[int], generator: Optional[Generator]=...) -> List[Subset[T]]: ...
