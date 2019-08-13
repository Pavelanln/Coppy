#include "caffe2/operators/channel_shuffle_op.h"

#include <array>

#include "caffe2/core/context_gpu.h"
#include "caffe2/utils/math.h"

namespace caffe2 {

namespace {
template <typename T, bool kNFirst>
__global__ void ChannelShuffleNCHWKernel(
    const int G,
    const int K,
    const int HxW,
    const T* X,
    T* Y) {
  const int C = G * K;
  const int n = kNFirst ? blockIdx.x : blockIdx.y;
  const int s = kNFirst ? blockIdx.y : blockIdx.x;
  const int g = blockIdx.z % G;
  const int k = blockIdx.z / G;
  const int offset = s * CAFFE_CUDA_NUM_THREADS + threadIdx.x;
  if (offset < HxW) {
#if __CUDA_ARCH__ >= 350
    Y[(n * C + blockIdx.z) * HxW + offset] =
        __ldg(X + (n * C + g * K + k) * HxW + offset);
#else
    Y[(n * C + blockIdx.z) * HxW + offset] =
        X[(n * C + g * K + k) * HxW + offset];
#endif
  }
}

template <typename T, int kSharedSize>
__global__ void
ChannelShuffleNHWCKernel(const int G, const int K, const T* X, T* Y) {
  __shared__ T sdata[kSharedSize];
  const int C = G * K;
  const int offset = blockIdx.x * C;
  for (int i = threadIdx.x; i < C; i += blockDim.x) {
#if __CUDA_ARCH__ >= 350
    sdata[i] = __ldg(X + offset + i);
#else
    sdata[i] = X[offset + i];
#endif
  }
  __syncthreads();
  for (int i = threadIdx.x; i < C; i += blockDim.x) {
    const int g = i % G;
    const int k = i / G;
    Y[offset + i] = sdata[g * K + k];
  }
}

} // namespace

template <>
template <typename T>
bool ChannelShuffleOp<CUDAContext>::RunOnDeviceWithOrderNCHW() {
  const auto& X = Input(0);

  auto* Y = Output(0, X.sizes(), at::dtype<T>());
  const int N = X.dim32(0);
  const int C = X.dim32(1);
  const int G = this->group_;
  CAFFE_ENFORCE_EQ(C % G, 0);
  if (X.numel() == 0) {
    return true;
  }
  const int K = C / G;
  const int HxW = X.numel() / (N * C);
  const int S = (HxW + CAFFE_CUDA_NUM_THREADS - 1) / CAFFE_CUDA_NUM_THREADS;
  const T* X_data = X.template data<T>();
  T* Y_data = Y->template mutable_data<T>();
  if (N <= kCUDAGridDimMaxY) {
    const dim3 dim_grid(S, N, C);
    ChannelShuffleNCHWKernel<T, false>
        <<<dim_grid, CAFFE_CUDA_NUM_THREADS, 0, context_.cuda_stream()>>>(
            G, K, HxW, X_data, Y_data);
  } else {
    const dim3 dim_grid(N, S, C);
    ChannelShuffleNCHWKernel<T, true>
        <<<dim_grid, CAFFE_CUDA_NUM_THREADS, 0, context_.cuda_stream()>>>(
            G, K, HxW, X_data, Y_data);
  }
  return true;
}

template <>
template <typename T>
bool ChannelShuffleOp<CUDAContext>::RunOnDeviceWithOrderNHWC() {
  const auto& X = Input(0);

  auto* Y = Output(0, X.sizes(), at::dtype<T>());
  const int ndim = X.dim();
  const int N = X.dim32(0);
  const int C = X.dim32(ndim - 1);
  const int G = this->group_;
  CAFFE_ENFORCE_EQ(C % G, 0);
  if (X.numel() == 0) {
    return true;
  }
  const int K = C / G;
  const int HxW = X.numel() / (N * C);
  const int outer_size = N * HxW;
  const T* X_data = X.template data<T>();
  T* Y_data = Y->template mutable_data<T>();
  if (C <= 32) {
    ChannelShuffleNHWCKernel<T, 32>
        <<<outer_size, CAFFE_CUDA_NUM_THREADS, 0, context_.cuda_stream()>>>(
            G, K, X_data, Y_data);
  } else if (C <= 128) {
    ChannelShuffleNHWCKernel<T, 128>
        <<<outer_size, CAFFE_CUDA_NUM_THREADS, 0, context_.cuda_stream()>>>(
            G, K, X_data, Y_data);
  } else if (C <= 512) {
    ChannelShuffleNHWCKernel<T, 512>
        <<<outer_size, CAFFE_CUDA_NUM_THREADS, 0, context_.cuda_stream()>>>(
            G, K, X_data, Y_data);
  } else {
    const std::array<std::int64_t, 3> dims = {N * HxW, G, K};
    const std::array<std::int32_t, 3> axes = {0, 2, 1};
    math::Transpose<std::int64_t, T, CUDAContext>(
        3, dims.data(), axes.data(), X_data, Y_data, &context_);
  }
  return true;
}

template <>
template <typename T>
bool ChannelShuffleGradientOp<CUDAContext>::RunOnDeviceWithOrderNCHW() {
  const auto& dY = Input(0);

  auto* dX = Output(0, dY.sizes(), at::dtype<T>());
  const int N = dY.dim32(0);
  const int C = dY.dim32(1);
  const int G = this->group_;
  CAFFE_ENFORCE_EQ(C % G, 0);
  if (dY.numel() == 0) {
    return true;
  }
  const int K = C / G;
  const int HxW = dY.numel() / (N * C);
  const int S = (HxW + CAFFE_CUDA_NUM_THREADS - 1) / CAFFE_CUDA_NUM_THREADS;
  const T* dY_data = dY.template data<T>();
  T* dX_data = dX->template mutable_data<T>();
  if (N <= kCUDAGridDimMaxY) {
    const dim3 dim_grid(S, N, C);
    ChannelShuffleNCHWKernel<T, false>
        <<<dim_grid, CAFFE_CUDA_NUM_THREADS, 0, context_.cuda_stream()>>>(
            K, G, HxW, dY_data, dX_data);
  } else {
    const dim3 dim_grid(N, S, C);
    ChannelShuffleNCHWKernel<T, true>
        <<<dim_grid, CAFFE_CUDA_NUM_THREADS, 0, context_.cuda_stream()>>>(
            K, G, HxW, dY_data, dX_data);
  }
  return true;
}

template <>
template <typename T>
bool ChannelShuffleGradientOp<CUDAContext>::RunOnDeviceWithOrderNHWC() {
  const auto& dY = Input(0);

  auto* dX = Output(0, dY.sizes(), at::dtype<T>());
  const int ndim = dY.dim();
  const int N = dY.dim32(0);
  const int C = dY.dim32(ndim - 1);
  const int G = this->group_;
  CAFFE_ENFORCE_EQ(C % G, 0);
  if (dY.numel() == 0) {
    return true;
  }
  const int K = C / G;
  const int HxW = dY.numel() / (N * C);
  const int outer_size = N * HxW;
  const T* dY_data = dY.template data<T>();
  T* dX_data = dX->template mutable_data<T>();
  if (C <= 32) {
    ChannelShuffleNHWCKernel<T, 32>
        <<<outer_size, CAFFE_CUDA_NUM_THREADS, 0, context_.cuda_stream()>>>(
            K, G, dY_data, dX_data);
  } else if (C <= 128) {
    ChannelShuffleNHWCKernel<T, 128>
        <<<outer_size, CAFFE_CUDA_NUM_THREADS, 0, context_.cuda_stream()>>>(
            K, G, dY_data, dX_data);
  } else if (C <= 512) {
    ChannelShuffleNHWCKernel<T, 512>
        <<<outer_size, CAFFE_CUDA_NUM_THREADS, 0, context_.cuda_stream()>>>(
            K, G, dY_data, dX_data);
  } else {
    const std::array<std::int64_t, 3> dims = {N * HxW, K, G};
    const std::array<std::int32_t, 3> axes = {0, 2, 1};
    math::Transpose<std::int64_t, T, CUDAContext>(
        3, dims.data(), axes.data(), dY_data, dX_data, &context_);
  }
  return true;
}

REGISTER_CUDA_OPERATOR(ChannelShuffle, ChannelShuffleOp<CUDAContext>);
REGISTER_CUDA_OPERATOR(
    ChannelShuffleGradient,
    ChannelShuffleGradientOp<CUDAContext>);

} // namespace caffe2
