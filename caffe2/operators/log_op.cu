#include "caffe2/core/context_gpu.h"
#include "caffe2/core/operator.h"
#include "caffe2/operators/elementwise_op.h"
#include "caffe2/utils/math.h"

namespace caffe2 {

struct LogCUDAFunctor {
  template <typename T>
  inline void
  operator()(const int n, const T* x, T* y, CUDAContext* device_context) {
    math::Log<T, CUDAContext>(n, x, y, device_context);
  }
};

namespace {
REGISTER_CUDA_OPERATOR(
    Log,
    UnaryElementwiseOp<TensorTypes<float>, CUDAContext, LogCUDAFunctor>);
}
}
