#include <ATen/hip/impl/HIPCachingAllocatorMasqueradingAsCUDA.h>

namespace c10 { namespace hip {
namespace HIPCachingAllocatorMasqueradingAsCUDA {

Allocator* get() {
  static HIPAllocatorMasqueradingAsCUDA allocator(HIPCachingAllocator::get());
  return &allocator;
}

void recordStreamMasqueradingAsCUDA(void *ptr, HIPStreamMasqueradingAsCUDA stream) {
  HIPCachingAllocator::recordStream(ptr, stream.hip_stream());
}

} // namespace HIPCachingAllocatorMasqueradingAsCUDA
}} // namespace c10::hip
