#include "caffe2/core/context.h"

#include "ATen/core/ATenCoreTest.h"

#include <atomic>
#if defined(_MSC_VER)
#include <process.h>
#endif

namespace caffe2 {

// We put this here because context.h rather than context_base.h is included in
// user code
// TODO: rename context.h -> context_cpu.h & context_base.h -> context.h
CAFFE2_API BaseStaticContext*
    BaseContext::static_context_[COMPILE_TIME_MAX_DEVICE_TYPES];

uint32_t RandomNumberSeed() {
  // Originally copied from folly::randomNumberSeed (at 418ad4)
  // modified to use chrono instead of sys/time.h
  static std::atomic<uint32_t> seedInput(0);
  auto tv = std::chrono::system_clock::now().time_since_epoch();
  uint64_t usec = static_cast<uint64_t>(
      std::chrono::duration_cast<std::chrono::microseconds>(tv).count());
  uint32_t tv_sec = usec / 1000000;
  uint32_t tv_usec = usec % 1000000;
  const uint32_t kPrime0 = 51551;
  const uint32_t kPrime1 = 61631;
  const uint32_t kPrime2 = 64997;
  const uint32_t kPrime3 = 111857;
  return kPrime0 * (seedInput++) + kPrime1 * static_cast<uint32_t>(getpid()) +
      kPrime2 * tv_sec + kPrime3 * tv_usec;
}

BaseStaticContext* GetCPUStaticContext() {
  static CPUStaticContext context;
  return &context;
}

REGISTER_STATIC_CONTEXT(CPU, GetCPUStaticContext());

} // namespace caffe2
