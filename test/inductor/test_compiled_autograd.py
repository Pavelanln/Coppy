# Owner(s): ["module: inductor"]
import torch
from torch import _inductor as inductor
from torch._dynamo import compiled_autograd
from torch._dynamo.test_case import run_tests, TestCase
from torch._dynamo.utils import counters
from torch.testing._internal.inductor_utils import HAS_CPU


def compiler_fn(gm):
    """Same as torch.compile() but counts number of compiles"""

    def inner_compiler(gm_, example_inputs_):
        counters["compiled_autograd"]["compiles"] += 1
        return inductor.compile(gm_, example_inputs_)

    return torch.compile(gm, backend=inner_compiler, fullgraph=True)


class TestCompiledAutograd(TestCase):
    def _common(self, fn):
        with torch.autograd.set_multithreading_enabled(False):
            torch._dynamo.reset()
            counters["compiled_autograd"].clear()
            torch.manual_seed(123)
            expected = list(fn())
            torch.manual_seed(123)
            with compiled_autograd.enable(compiler_fn):
                actual = list(fn())
            self.assertEqual(expected, actual)
            self.assertEqual(counters["compiled_autograd"]["captures"], 1)
            self.assertEqual(counters["compiled_autograd"]["compiles"], 1)

    def test_basic(self):
        def fn():
            model = torch.nn.Sequential(
                torch.nn.Linear(4, 4),
                torch.nn.ReLU(),
                torch.nn.Linear(4, 4),
                torch.nn.ReLU(),
            )
            x = torch.randn([1, 4])
            result = model(x).sum()
            result.backward()
            yield model[0].weight.grad
            yield model[0].bias.grad
            yield model[2].weight.grad
            yield model[2].bias.grad

        self._common(fn)

    def test_cache_hit(self):
        def fn():
            for _ in range(3):
                model = torch.nn.Sequential(
                    torch.nn.Linear(4, 4),
                    torch.nn.ReLU(),
                    torch.nn.Linear(4, 4),
                    torch.nn.ReLU(),
                )
                x = torch.randn([1, 4])
                result = model(x).sum()
                result.backward()
                yield model[0].weight.grad
                yield model[0].bias.grad
                yield model[2].weight.grad
                yield model[2].bias.grad

        self._common(fn)

    def test_tensor_grad_hook1(self):
        def fn():
            for _ in range(3):
                model = torch.nn.Sequential(
                    torch.nn.Linear(4, 4),
                    torch.nn.ReLU(),
                )
                x = torch.randn([1, 4])

                model[0].weight.register_hook(lambda grad: grad * 2)

                result = model(x).sum()
                result.backward()
                yield model[0].weight.grad
                yield model[0].bias.grad

        self._common(fn)

    def test_tensor_grad_hook2(self):
        def fn():
            for _ in range(3):
                model = torch.nn.Sequential(
                    torch.nn.Linear(4, 4),
                    torch.nn.ReLU(),
                )
                x = torch.randn([1, 4])

                result = model(x).sum()
                result.grad_fn.register_prehook(lambda grad: (grad[0] + 1,))
                result.backward()
                yield model[0].weight.grad
                yield model[0].bias.grad

        self._common(fn)

    def test_tensor_grad_hook3(self):
        def fn():
            for _ in range(3):
                model = torch.nn.Sequential(
                    torch.nn.Linear(4, 4),
                    torch.nn.ReLU(),
                )
                x = torch.randn([1, 4])

                result = model(x).sum()
                result.grad_fn.register_hook(lambda gI, gO: (torch.sin(gI[0]) + gO[0],))
                result.backward()
                yield model[0].weight.grad
                yield model[0].bias.grad

        self._common(fn)

    def test_torch_compile(self):
        def fn():
            model = torch.nn.Sequential(
                torch.nn.Linear(4, 4),
                torch.nn.Sigmoid(),
            )
            opt_model = torch.compile(model, fullgraph=True)

            for _ in range(3):
                x = torch.randn([1, 4])

                result = opt_model(x).sum()
                result.backward()
                yield model[0].weight.grad
                yield model[0].bias.grad
                model.zero_grad()

        self._common(fn)

    def test_implicit_add(self):
        def fn():
            y = torch.randn(1, 4, requires_grad=True)

            def model(x):
                # y is used multiple times, gradients get added
                return torch.sigmoid(x * y + torch.sin(y) + torch.cos(y))

            for _ in range(3):
                x = torch.randn([1, 4])

                result = model(x).sum()
                result.backward()
                yield result
                yield y.grad
                y.grad = None

        self._common(fn)

    def test_output_nodes(self):
        def fn():
            y = torch.randn(1, 4, requires_grad=True)
            z = torch.randn(1, 4, requires_grad=True)

            def model(x):
                return torch.sigmoid(x * z + torch.sin(y) + torch.cos(y))

            for _ in range(3):
                x = torch.randn([1, 4])

                result = model(x).sum()
                gy, gz = torch.autograd.grad(result, [y, z])
                assert y.grad is None
                assert z.grad is None
                yield gy
                yield gz

        self._common(fn)


if __name__ == "__main__":
    if HAS_CPU:
        run_tests(needs="filelock")
