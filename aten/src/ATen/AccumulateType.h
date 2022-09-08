#pragma once
#include <ATen/Config.h>
#include <c10/core/ScalarType.h>
#include <c10/util/BFloat16.h>
#include <c10/util/Half.h>

// Defines the accumulation type for a scalar type.
// Example:
//   using accscalar_t = acc_type<scalar_t, /*is_cuda*/true>;
//
// Accumulation types are an important concept in numeric computing
// because you frequently want to perform intermediate computations
// at a higher precision than the input and output precision, to avoid
// compounding internal rounding errors.  Accumulation is the most
// well-known intermediate computation (it is of great importance for
// sum reduction and matrix multiply, for example), but in PyTorch
// acc_type ends up getting used for all sorts of other intermediate
// computations, so it perhaps would be more accurately (ahem) called an
// "accurate" type.  acc_type is especially important for reduced
// precision operations like float16 and bfloat16, where relatively
// benign looking inputs can easily end up overflowing/underflowing.
//
// acc_type is parametrized by whether or not you are running on CUDA
// or not, because on CUDA double precision operations are expensive
// and so by default, we don't actually want to use double as an
// acc_type on CUDA.  A lot of things are typed out below, but
// basically, the table is generated by a few rules:
//
//  If bool:
//      Use 'bool' as acc_type.
//  If floating point:
//      If CUDA, use 'float' as acc_type (unless scalar_t is double),
//      otherwise (CPU) use 'double'
//  If integral:
//      Use 'int64_t' as acc_type
//
// You're not forced to use this template; if you happen to know
// something specific about your use case, you can specify your own
// desired behavior.  This template, however, will give you a reasonable
// default that will work for all dtypes supported in PyTorch.

#if defined(__CUDACC__)
#include <cuda.h>
#include <cuda_fp16.h>
#elif defined(__HIPCC__)
#include <hip/hip_fp16.h>
#include <hip/hip_runtime.h>
#endif

namespace at {

template <typename T, bool is_cuda>
struct AccumulateType {};

#if defined(__CUDACC__) || defined(__HIPCC__)
template <>
struct AccumulateType<half, true> {
  using type = float;
};
#endif
template <>
struct AccumulateType<BFloat16, true> {
  using type = float;
};
template <>
struct AccumulateType<Half, true> {
  using type = float;
};
template <>
struct AccumulateType<float, true> {
  using type = float;
};
template <>
struct AccumulateType<double, true> {
  using type = double;
};
template <>
struct AccumulateType<int8_t, true> {
  using type = int64_t;
};
template <>
struct AccumulateType<uint8_t, true> {
  using type = int64_t;
};
template <>
struct AccumulateType<char, true> {
  using type = int64_t;
};
template <>
struct AccumulateType<int16_t, true> {
  using type = int64_t;
};
template <>
struct AccumulateType<int32_t, true> {
  using type = int64_t;
};
template <>
struct AccumulateType<int64_t, true> {
  using type = int64_t;
};
template <>
struct AccumulateType<bool, true> {
  using type = bool;
};
template <>
struct AccumulateType<Half, false> {
  using type = float;
};
template <>
struct AccumulateType<BFloat16, false> {
  using type = float;
};
template <>
struct AccumulateType<c10::complex<Half>, false> {
  using type = c10::complex<float>;
};
template <>
struct AccumulateType<c10::complex<float>, false> {
  using type = c10::complex<double>;
};
template <>
struct AccumulateType<c10::complex<double>, false> {
  using type = c10::complex<double>;
};
template <>
struct AccumulateType<c10::complex<Half>, true> {
  using type = c10::complex<float>;
};
template <>
struct AccumulateType<c10::complex<float>, true> {
  using type = c10::complex<float>;
};
template <>
struct AccumulateType<c10::complex<double>, true> {
  using type = c10::complex<double>;
};
template <>
struct AccumulateType<float, false> {
  using type = double;
};
template <>
struct AccumulateType<double, false> {
  using type = double;
};
template <>
struct AccumulateType<int8_t, false> {
  using type = int64_t;
};
template <>
struct AccumulateType<uint8_t, false> {
  using type = int64_t;
};
template <>
struct AccumulateType<char, false> {
  using type = int64_t;
};
template <>
struct AccumulateType<int16_t, false> {
  using type = int64_t;
};
template <>
struct AccumulateType<int32_t, false> {
  using type = int64_t;
};
template <>
struct AccumulateType<int64_t, false> {
  using type = int64_t;
};
template <>
struct AccumulateType<bool, false> {
  using type = bool;
};

template <typename T, bool is_cuda>
using acc_type = typename AccumulateType<T, is_cuda>::type;

TORCH_API c10::ScalarType toAccumulateType(c10::ScalarType type, bool is_cuda);

} // namespace at
