#pragma once

#include "cudnn-wrapper.h"
#include "ATen/cuda/ATenCUDAGeneral.h"

namespace at { namespace native {

AT_CUDA_API cudnnHandle_t getCudnnHandle();

}} // namespace
