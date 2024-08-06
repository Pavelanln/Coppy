#pragma once

#include <torch/csrc/Export.h>
#include <torch/data/samplers/base.h>
#include <torch/types.h>

#include <cstddef>
#include <vector>

namespace torch {
namespace serialize {
class OutputArchive;
class InputArchive;
} // namespace serialize
} // namespace torch

namespace torch {
namespace jit {
namespace mobile {

/// A lighter `Sampler` that returns indices sequentially and cannot be
/// serialized.
class TORCH_API SequentialSampler : public torch::data::samplers::Sampler<> {
 public:
  /// Creates a `SequentialSampler` that will return indices in the range
  /// `0...size - 1`.
  explicit SequentialSampler(size_t size);

  /// Resets the `SequentialSampler` to zero.
  void reset(std::optional<size_t> new_size = std::nullopt) override;

  /// Returns the next batch of indices.
  std::optional<std::vector<size_t>> next(size_t batch_size) override;

  /// Not supported for mobile SequentialSampler
  void save(serialize::OutputArchive& archive) const override;

  /// Not supported for mobile SequentialSampler
  void load(serialize::InputArchive& archive) override;

  /// Returns the current index of the `SequentialSampler`.
  size_t index() const noexcept;

 private:
  size_t size_;
  size_t index_{0};
};

} // namespace mobile
} // namespace jit
} // namespace torch
