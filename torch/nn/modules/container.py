from collections import OrderedDict

import torch
from torch.autograd import Variable
from .module import Module


class Container(Module):
    """This is the base container class for all neural networks you would define.
    You will subclass your container from this class.
    In the constructor you define the modules that you would want to use,
    and in the __call__ function you use the constructed modules in
    your operations.

    To make it easier to understand, given is a small example.
    ```
    # Example of using Container
     class Net(nn.Container):
        def __init__(self):
            super(Net, self).__init__(
                conv1 = nn.Conv2d(1, 20, 5),
                relu  = nn.ReLU()
             )
        def __call__(self, input):
            output = self.relu(self.conv1(x))
            return output
     model = Net()
     ```

    One can also add new modules to a container after construction.
    You can do this with the add_module function.

    ```
    # one can add modules to the container after construction
    model.add_module('pool1', nn.MaxPool2d(2, 2))
    ```

    The container has one additional method `parameters()` which
    returns the list of learnable parameters in the container instance.
    """
    def __init__(self, **kwargs):
        super(Container, self).__init__()
        self._modules = OrderedDict()
        for key, value in kwargs.items():
            self.add_module(key, value)

    def add_module(self, name, module):
        if hasattr(self, name):
            raise KeyError("attribute already exists '{}'".format(name))
        if not isinstance(module, Module) and module is not None:
            raise ValueError("{} is not a Module subclass".format(
                torch.typename(module)))
        self._modules[name] = module

    def __getattr__(self, name):
        if '_modules' in self.__dict__:
            modules = self.__dict__['_modules']
            if name in modules:
                return modules[name]
        return Module.__getattr__(self, name)

    def parameters(self, memo=None):
        if memo is None:
            memo = set()
        super(Container, self).parameters(memo)
        for module in self.children():
            for p in module.parameters(memo):
                yield p

    def children(self):
        memo = set()
        for module in self._modules.values():
            if module is not None and module not in memo:
                memo.add(module)
                yield module

    def modules(self, memo=None):
        if memo is None:
            memo = set()
        if self not in memo:
            super(Container, self).modules(memo)
            for module in self.children():
                for m in module.modules(memo):
                    yield m

    def _apply(self, fn):
        for module in self.children():
            module._apply(fn)
        return super(Container, self)._apply(fn)


class Sequential(Container):

    def __init__(self, *args):
        super(Sequential, self).__init__()
        if len(args) == 1 and isinstance(args[0], OrderedDict):
            for key, module in args[0].items():
                self.add_module(key, module)
        else:
            idx = 0
            for module in args:
                self.add_module(str(idx), module)
                idx += 1

    def __getitem__(self, idx):
        if idx < 0 or idx >= len(self._modules):
            raise IndexError('index {} is out of range'.format(idx))
        it = iter(self._modules.values())
        for i in range(idx):
            next(it)
        return next(it)

    def forward(self, input):
        for module in self._modules.values():
            input = module(input)
        return input
