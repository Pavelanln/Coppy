#include <torch/nn/options/pooling.h>

namespace torch {
namespace nn {

template struct MaxPoolOptions<1>;
template struct MaxPoolOptions<2>;
template struct MaxPoolOptions<3>;

} // namespace nn
} // namespace torch
