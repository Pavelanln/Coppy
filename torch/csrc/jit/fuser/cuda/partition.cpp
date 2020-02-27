#include <torch/csrc/jit/fuser/cuda/partition.h>

namespace torch {
namespace jit {
namespace fuser {
namespace cuda {

namespace {

// Check all outputs are:
//   1. TensorType
//   2. on the same device;
// TODO: update this when codegen can output scalar
static c10::optional<c10::Device> getDevice(const Value* const value) {
  if (!value->type()->isSubtypeOf(TensorType::get())) {
    // not tensor type, return false as the op is not outputing scalar.
    return c10::nullopt;
  }
  return value->type()->expect<TensorType>()->device();
}

static c10::optional<c10::Device> getDevice(const Node* const node) {
  auto outputs = node->outputs();
  if (outputs.size() == 0) {
    return c10::nullopt;
  }
  return getDevice(outputs[0]);
}

static bool isFusibleDevice(const Node* node, const c10::Device device) {
  for (auto value : node->outputs()) {
    auto output_device = getDevice(value);
    if (!output_device.has_value() || output_device.value() != device) {
      return false;
    }
  }
  return true;
}

static bool isFusibleDevice(const Node* node) {
  auto device = getDevice(node);
  if (!device.has_value()) {
    return false;
  }
  // Technically we don't need to check device for node->outputs()[0] again, meh
  return isFusibleDevice(node, device.value());
}

} // namespace

bool isFusibleCudaFusionGroup(const Node* const node) {
  if (isFusibleDevice(node)) {
    if(node->kind() == aten::add || node->kind() == prim::FusionGroup){
      return true;
    }
  }
  return false;
}

bool isFusibleCudaFusionGroup(
    const Node* const fusion,
    const Node* const node) {
  auto device = getDevice(fusion);

  if (device.has_value() && isFusibleDevice(node, device.value())) {
    if(node->kind() == aten::add || node->kind() == prim::FusionGroup){
      return true;
    }
  }
  return false;
}

}}}}
