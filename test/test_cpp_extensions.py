import unittest

import torch
import torch.utils.cpp_extension
try:
    import torch_test_cpp_extension as cpp_extension
except ModuleNotFoundError:
    print("\'test_cpp_extensions.py\' cannot be invoked directly. " +
          "Run \'python run_test.py -i cpp_extensions\' for the \'test_cpp_extensions.py\' tests.")
    raise

import common

from torch.utils.cpp_extension import CUDA_HOME
TEST_CUDA = torch.cuda.is_available() and CUDA_HOME is not None


class TestCppExtension(common.TestCase):
    def test_extension_function(self):
        x = torch.randn(4, 4)
        y = torch.randn(4, 4)
        z = cpp_extension.sigmoid_add(x, y)
        self.assertEqual(z, x.sigmoid() + y.sigmoid())

    def test_extension_module(self):
        mm = cpp_extension.MatrixMultiplier(4, 8)
        weights = torch.rand(8, 4)
        expected = mm.get().mm(weights)
        result = mm.forward(weights)
        self.assertEqual(expected, result)

    def test_backward(self):
        mm = cpp_extension.MatrixMultiplier(4, 8)
        weights = torch.rand(8, 4, requires_grad=True)
        result = mm.forward(weights)
        result.sum().backward()
        tensor = mm.get()

        expected_weights_grad = tensor.t().mm(torch.ones([4, 4]))
        self.assertEqual(weights.grad, expected_weights_grad)

        expected_tensor_grad = torch.ones([4, 4]).mm(weights.t())
        self.assertEqual(tensor.grad, expected_tensor_grad)

    def test_jit_compile_extension(self):
        module = torch.utils.cpp_extension.load(
            name='jit_extension',
            sources=[
                'cpp_extensions/jit_extension.cpp',
                'cpp_extensions/jit_extension2.cpp'
            ],
            extra_include_paths=['cpp_extensions'],
            extra_cflags=['-g'],
            verbose=True)
        x = torch.randn(4, 4)
        y = torch.randn(4, 4)

        z = module.tanh_add(x, y)
        self.assertEqual(z, x.tanh() + y.tanh())

        # Checking we can call a method defined not in the main C++ file.
        z = module.exp_add(x, y)
        self.assertEqual(z, x.exp() + y.exp())

        # Checking we can use this JIT-compiled class.
        doubler = module.Doubler(2, 2)
        self.assertIsNone(doubler.get().grad)
        self.assertEqual(doubler.get().sum(), 4)
        self.assertEqual(doubler.forward().sum(), 8)

    @unittest.skipIf(not TEST_CUDA, "CUDA not found")
    def test_cuda_extension(self):
        import torch_test_cuda_extension as cuda_extension

        x = torch.FloatTensor(100).zero_().cuda()
        y = torch.FloatTensor(100).zero_().cuda()

        z = cuda_extension.sigmoid_add(x, y).cpu()

        # 2 * sigmoid(0) = 2 * 0.5 = 1
        self.assertEqual(z, torch.ones_like(z))

    @unittest.skipIf(not TEST_CUDA, "CUDA not found")
    def test_jit_cuda_extension(self):
        # NOTE: The name of the extension must equal the name of the module.
        module = torch.utils.cpp_extension.load(
            name='torch_test_cuda_extension',
            sources=[
                'cpp_extensions/cuda_extension.cpp',
                'cpp_extensions/cuda_extension.cu'
            ],
            extra_cuda_cflags=['-O2'],
            verbose=True)

        x = torch.FloatTensor(100).zero_().cuda()
        y = torch.FloatTensor(100).zero_().cuda()

        z = module.sigmoid_add(x, y).cpu()

        # 2 * sigmoid(0) = 2 * 0.5 = 1
        self.assertEqual(z, torch.ones_like(z))

    def test_optional(self):
        has_value = cpp_extension.function_taking_optional(torch.ones(5))
        self.assertTrue(has_value)
        has_value = cpp_extension.function_taking_optional(None)
        self.assertFalse(has_value)

    def test_inline_jit_compile_extension(self):
        cpp_source1 = '''
        #include <torch/torch.h>
        at::Tensor sin_add(at::Tensor x, at::Tensor y) {
          return x.sin() + y.sin();
        }
        '''

        cpp_source2 = '''
        #include <torch/torch.h>

        void cos_add_cuda(const double* x, const double* y, double* output, int size);
        at::Tensor sin_add(at::Tensor x, at::Tensor y);
        at::Tensor cos_add(at::Tensor x, at::Tensor y) {
          auto output = at::zeros_like(x);
          cos_add_cuda(x.data<double>(), y.data<double>(), output.data<double>(), output.numel());
          return output;
        }
        PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
          m.def("sin_add", &sin_add, "sin(x) + sin(y)");
          m.def("cos_add", &cos_add, "cos(x) + cos(y)");
        }
        '''

        cuda_source = '''
        #include <cuda.h>
        #include <cuda_runtime.h>
        #include <ATen/ATen.h>

        __global__ void cos_add_kernel(
            const double* __restrict__ x,
            const double* __restrict__ y,
            double* __restrict__ output,
            const int size) {
          const auto index = blockIdx.x * blockDim.x + threadIdx.x;
          if (index < size) {
            output[index] = __cosf(x[index]) + __cosf(y[index]);
          }
        }

        void cos_add_cuda(const double* x, const double* y, double* output, int size) {
          const int threads = 1024;
          const int blocks = (size + threads - 1) / threads;
          cos_add_kernel<<<blocks, threads>>>(x, y, output, size);
        }
        '''

        module = torch.utils.cpp_extension.load_inline(
            name='inline_jit_extension',
            cpp_sources=[cpp_source1, cpp_source2],
            cuda_sources=cuda_source,
            verbose=True)
        x = torch.randn(4, 4)
        y = torch.randn(4, 4)

        z = module.sin_add(x, y)
        self.assertEqual(z, x.sin() + y.sin())

        z = module.cos_add(x, y)
        self.assertEqual(z, x.cos() + y.cos())


if __name__ == '__main__':
    common.run_tests()
