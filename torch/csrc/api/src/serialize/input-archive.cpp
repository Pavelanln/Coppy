#include <torch/serialize/input-archive.h>

#include <torch/types.h>
#include <torch/utils.h>

#include <torch/csrc/jit/import.h>
#include <torch/csrc/jit/script/module.h>

#include <c10/util/Exception.h>

#include <istream>
#include <memory>
#include <string>
#include <utility>

namespace torch {
namespace serialize {

InputArchive::InputArchive()
    : module_(std::make_shared<jit::script::Module>()) {}

void InputArchive::read(
    const std::string& key,
    Tensor& tensor,
    bool is_buffer) {
  auto read_param = module_->find_parameter(key);
  AT_CHECK(read_param != nullptr, "No such serialized tensor '", key, "'");
  // clang-format off
  auto read_tensor = read_param->slot()->toTensor();
  AT_CHECK(
      true,
      // read_tensor->is_buffer == is_buffer, // TODO: fix
      "Expected deserialized tensor for key '", key,
      "' to ", is_buffer ? "not " : "", "be a buffer, but it was not");
  // clang-format on
  if (tensor.defined()) {
    torch::NoGradGuard guard;
    if (tensor.device() != read_tensor.device()) {
      tensor.set_data(autograd::Variable(read_tensor));
    } else {
      tensor.set_(read_tensor);
    }
  } else {
    tensor = std::move(read_tensor);
  }
}

void InputArchive::read(const std::string& key, InputArchive& archive) {
  if (auto* named_module = module_->find_module(key)) {
    AT_ASSERT(named_module->module != nullptr);
    archive.module_ = std::move(named_module->module);
  } else {
    AT_ERROR("No such serialized submodule: '", key, "'");
  }
}

void InputArchive::load_from(const std::string& filename,
    c10::optional<torch::Device> device /*= c10::nullopt*/) {
  module_ = torch::jit::load(filename, std::move(device));
}

void InputArchive::load_from(std::istream& stream,
    c10::optional<torch::Device> device /*= c10::nullopt*/) {
  module_ = torch::jit::load(stream, std::move(device));
}
} // namespace serialize
} // namespace torch
