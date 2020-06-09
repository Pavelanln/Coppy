import torch


class VariableMeta(type):
    def __instancecheck__(cls, other):
        return isinstance(other, torch.Tensor)


class Variable(torch._C._LegacyVariableBase, metaclass=VariableMeta):
    pass


from torch._C import _ImperativeEngine as ImperativeEngine
Variable._execution_engine = ImperativeEngine()
