#pragma once

#include <c10/cuda/CUDAAssert.h>
#include <c10/macros/Macros.h>
#include <cstddef>

namespace at {
namespace native {
namespace assert {

using namespace c10::cuda;

static inline C10_HOST_DEVICE char* write_string(
    char* dst,
    const char* src,
    size_t n) {
  size_t i = 0;
  if (src && n > 0) {
    while (i < n - 1 && src[i]) {
      dst[i] = src[i];
      ++i;
    }
    dst[i] = '\0';  // ensure strings are terminated
    ++i;
  }
  return dst + i;
}

inline C10_HOST_DEVICE char* copy_string(
    char* dst,
    char* buffer_end,
    const char* src) {
  if (dst) {
    auto size_ptr =
        reinterpret_cast<size_t*>(dst); // store pointer of string size field
    dst += C10_ASSERT_ARG_ALIGN_SIZE;
    if (dst < buffer_end) {
      char* start = dst;

      // write string into buffer and store size
      dst = write_string(dst, src, buffer_end - dst);
      *size_ptr = (size_t)(dst - start);

      // fix alignment
      ptrdiff_t offset = dst - start;
      ptrdiff_t misalign = offset % C10_ASSERT_ARG_ALIGN_SIZE;
      if (misalign > 0) {
        dst += C10_ASSERT_ARG_ALIGN_SIZE - misalign;
      }

      // again check position after alignment correction
      if (dst <= buffer_end) {
        return dst;
      }
    }
  }

  return nullptr; // insufficient buffer
}

static inline C10_HOST_DEVICE char* copy_args(char* dst, char* const end) {
  return dst;
}

inline C10_HOST_DEVICE char* copy_args(
    char* dst,
    char* const end,
    const char* arg) {
  return copy_string(dst, end, arg);
}

template <typename T>
C10_HOST_DEVICE char* copy_args(char* dst, char* const end, T arg) {
  if (!dst || dst + C10_ASSERT_ARG_ALIGN_SIZE >= end) {
    return nullptr;
  }

  // write length of arg
  *reinterpret_cast<size_t*>(dst) = sizeof(T);
  dst += C10_ASSERT_ARG_ALIGN_SIZE;

  // write argument value
  *reinterpret_cast<T*>(dst) = arg;
  dst += C10_ASSERT_ARG_ALIGN_SIZE;

  return dst;
}

template <typename T, typename... Args>
C10_HOST_DEVICE char* copy_args(
    char* dst,
    char* const end,
    T first,
    Args... args) {
  dst = copy_args(dst, end, first);
  return copy_args(dst, end, args...);
}

template <typename... Args>
C10_HOST_DEVICE bool assert_(
    CUDAAssert* assert_state,
    bool condition,
    const char* expression,
    uint32_t line,
    const char* file,
    const char* func,
    const char* format,
    Args... args) {
  if (!condition) {
#ifdef __CUDA_ARCH__
    if (atomicCAS(const_cast<int32_t*>(&assert_state->error), 0, 1) != 0) {
      return false;
    }
#else
    assert(false); // should never be called
#endif

    char* buffer = assert_state->buffer;
    char* dst = buffer;
    char* const end = dst + sizeof(assert_state->buffer);

    dst = copy_string(dst, end, file);
    dst = copy_string(dst, end, func);
    dst = copy_string(dst, end, expression);
    dst = copy_string(dst, end, format);
    dst = copy_args(dst, end, line, args...);

    assert_state->length = dst ? dst - buffer : 0;
  }

  return !assert_state->error;
}

// handle case without format string, e.g. C10_KERNEL_ASSERT(false)
inline C10_HOST_DEVICE bool assert_(
    CUDAAssert* assert_state,
    bool condition,
    const char* expression,
    uint32_t line,
    const char* file,
    const char* func) {
  return assert_(
      assert_state,
      condition,
      expression,
      line,
      file,
      func,
      "Assertion failed");
}

} // namespace assert
} // namespace native
} // namespace at

#define C10_PREPARE_KERNEL_ASSERT \
  auto __c10_assert_state = at::cuda::getCurrentCUDAStream().assert_state();

#define C10_KERNEL_ASSERT(exp, ...)        \
  do {                                     \
    if (!exp) {                            \
      at::native::assert::assert_(         \
          __c10_assert_state,              \
          false,                           \
          #exp,                            \
          static_cast<uint32_t>(__LINE__), \
          __FILE__,                        \
          __func__,                        \
          ##__VA_ARGS__);                  \
      assert(exp);                         \
      assert(false);                       \
    }                                      \
  } while (false)

#define C10_KERNEL_ASSERT_SOFT(exp, ...) \
  at::native::assert::assert_(                \
      __c10_assert_state,                     \
      exp,                                    \
      #exp,                                   \
      static_cast<uint32_t>(__LINE__),        \
      __FILE__,                               \
      __func__,                               \
      ##__VA_ARGS__)

#define C10_KERNEL_INDEX_ERROR_SOFT(index, axis, size)           \
  C10_KERNEL_ASSERT_SOFT(                                        \
      false,                                                     \
      "index %d is out of bounds for dimension %d with size %d", \
      index,                                                     \
      axis,                                                      \
      size)
