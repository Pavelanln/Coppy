#pragma once

#include <memory>
#include <mutex>
#include "ATen/ATenGeneral.h"
#include "ATen/Generator.h"
#include "ATen/Type.h"
#include "ATen/Utils.h"

struct THCState;

namespace at {

class AT_API Context {
public:
  Context();
  Type & getType(Backend p, ScalarType s) {
    initCUDAIfNeeded(p);
    auto & type = type_registry[static_cast<int>(p)][static_cast<int>(s)];

    if(!type) {
      // there is only a single Undefined Type.
      if (p == Backend::Undefined || s == ScalarType::Undefined) {
        auto & undef = type_registry[static_cast<int>(Backend::Undefined)][static_cast<int>(ScalarType::Undefined)];
        if (undef) return *undef;
      }
      runtime_error("%s%sType is not enabled.",toString(p),toString(s));
    }
    return *type;
  }
  Generator & defaultGenerator(Backend p) {
    initCUDAIfNeeded(p);
    auto & generator = generator_registry[static_cast<int>(p)];
    if(!generator)
      runtime_error("%s backend type not enabled.",toString(p));
    return *generator;
  }
  bool hasCUDA() const;
  // defined in header so that getType has ability to inline
  // call_once check. getType is called fairly frequently
  THCState* lazyInitCUDA() {
    std::call_once(thc_init,[&] {
      doInitCUDA();
    });
    return thc_state;
  }
#if AT_CUDA_ENABLED()
  cudaStream_t getCurrentCUDAStream() const;
#endif
  ~Context();
  std::unique_ptr<Generator>
    generator_registry[static_cast<int>(Backend::NumOptions)];
  std::unique_ptr<Type> type_registry
    [static_cast<int>(Backend::NumOptions)]
    [static_cast<int>(ScalarType::NumOptions)];
  // TODO: Consider making this private
  THCState * thc_state;
private:
  void initCUDAIfNeeded(Backend p) {
    if(p == Backend::CUDA)
      lazyInitCUDA();
  }
  void doInitCUDA();
  std::once_flag thc_init;
};

AT_API Context & globalContext();

static inline void init() {
  globalContext();
}

static inline Type& getType(Backend p, ScalarType s) {
  return globalContext().getType(p,s);
}

static inline Type& CPU(ScalarType s) {
  return getType(Backend::CPU, s);
}

static inline Type& CUDA(ScalarType s) {
  return getType(Backend::CUDA, s);
}

static inline bool hasCUDA() {
  return globalContext().hasCUDA();
}

}
