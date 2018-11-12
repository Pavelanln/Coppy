#pragma once

#include <torch/data/example.h>
#include <torch/data/transforms/base.h>
#include <torch/types.h>

#include <functional>
#include <utility>

namespace torch {
namespace data {
namespace transforms {

/// A `Transform` that is specialized for the typical `Example<Tensor, Tensor>`
/// combination. It exposes a single `operator()` interface hook (for
/// subclasses), and calls this function on input `Example` objects.
template <typename Target = Tensor>
class TensorTransform
    : public Transform<Example<Tensor, Target>, Example<Tensor, Target>> {
 public:
  using E = Example<Tensor, Target>;
  using typename Transform<E, E>::InputType;
  using typename Transform<E, E>::OutputType;

  /// Transforms a single input tensor to an output tensor.
  virtual Tensor operator()(Tensor input) = 0;

  /// Implementation of `Transform::apply` that calls `operator()`.
  OutputType apply(InputType input) override {
    input.data = (*this)(std::move(input.data));
    return input;
  }
};

/// A `Lambda` specialized for the typical `Example<Tensor, Tensor>` input type.
template <typename Target = Tensor>
class TensorLambda : public TensorTransform<Target> {
 public:
  using FunctionType = std::function<Tensor(Tensor)>;

  /// Creates a `TensorLambda` from the given `function`.
  explicit TensorLambda(FunctionType function)
      : function_(std::move(function)) {}

  /// Applies the user-provided functor to the input tensor.
  Tensor operator()(Tensor input) override {
    return function_(std::move(input));
  }

 private:
  FunctionType function_;
};
} // namespace transforms
} // namespace data
} // namespace torch
