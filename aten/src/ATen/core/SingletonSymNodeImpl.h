#pragma once

#include <c10/core/ConstantSymNodeImpl.h>
#include <c10/core/SymNodeImpl.h>
#include <c10/macros/Export.h>
#include <c10/util/Exception.h>
#include <c10/util/Optional.h>
#include <c10/util/intrusive_ptr.h>
#include <ATen/core/TensorBody.h>
#include <cstdint>
#include <string>

namespace c10 {

// The motivating usecase for this is to represent the ragged size structure
// of a jagged tensor [B, [s_0, s_1, s_2], D] as a single integer j0. This
// allows us to simply return [B, j0, D] if someone queries for the size of our
// tensor.
//
// Morally we define comparison between two singleton ints to return true if
// that comparison holds for all corresponding elements of the arrays they
// represent. Comparison between a singleton int and a plain int is defined
// similarly.
//
// To simulate this desired behavior but also avoid the O(N) cost of checking,
// we associate each raggedness pattern with an integer "id" that can be used as
// a proxy to evaluate equality. We also constrain the range of values for this
// as to enable inequality checks.
//
// We also support a positive integer scalar "coeff" that is used for computing
// strides. For example given, a [B, j0, D] tensor, it can be strided in two
// different ways: [D * j0, D, 1] and [j0, 1, sum(j0)]. The coeff is used to
// differentiate the two cases.
//
// During tracing the strides of the outputs need to be a function of the size
// and strides of the inputs so it is important that SingletonSymNode itself is
// able to express this.
//
// NOTE [ SingletonVariant ]
//
// Currently, if SingletonSymNodeType::CPP is passed, that means that the
// singleton is only meant to be used to ferry nested_tensor_size metadata
// from forward to use in backward. In this case we set `val`, `coeff` etc
// to bogus values and make sure to error if they are accessed.
enum class SingletonVariant { PYTHON, CPP };

constexpr c10::DispatchKeySet py_singleton_ks({c10::DispatchKey::Python, c10::DispatchKey::PythonTLSSnapshot});
constexpr c10::DispatchKeySet cpp_singleton_ks({c10::DispatchKey::NestedTensor});

class TORCH_API SingletonSymNodeImpl : public SymNodeImpl {
 public:
  // CAUTION: you should probably not be constructing these directly; please
  // the higher-level API in python instead.
  explicit SingletonSymNodeImpl(
      int64_t val,
      int64_t coeff,
      at::Tensor vec,
      int64_t sum_vec,
      SingletonVariant type)
      : val_(val), coeff_(coeff), vec_(std::move(vec)), sum_vec_(sum_vec), type_(type) {
    // See NOTE [ SingletonVariant ]
    if (type == SingletonVariant::PYTHON) {
      key_set_ = py_singleton_ks;
    } else if (type == SingletonVariant::CPP) {
      TORCH_INTERNAL_ASSERT(val == -1 && coeff == -1 && sum_vec == -1);
      // NB: Since we possibly don't have python instead of relying on torch
      //     dispatch, we dispatch to the NestedTensor kernel directly.
      // NB: we can potentially add the AutogradNestedTensor key
      key_set_ = cpp_singleton_ks;
    }
  }

  bool bool_() override {
    return false;
  }

  bool is_int() override {
    return true;
  }

  bool is_float() override {
    return false;
  }

  bool is_bool() override {
    return false;
  }

  bool is_singleton() override {
    return true;
  }

  bool has_hint() override {
    return true;
  }

  c10::SymNode wrap_int(int64_t num) override {
    return SymNode(c10::make_intrusive<ConstantSymNodeImpl<int64_t>>(num));
  };

  int64_t guard_int(const char* file, int64_t line) override {
    TORCH_CHECK(false);
  }

  double guard_float(const char* file, int64_t line) override {
    TORCH_CHECK(false, "not a float");
  }

  bool guard_bool(const char* file, int64_t line) override {
    TORCH_CHECK(false, "not a bool");
  }

  int64_t int_() override {
    TORCH_CHECK(false);
  }

  std::string str() override {
    if (coeff_ == 1) {
      return "j" + std::to_string(val_);
    }
    if (type_ == SingletonVariant::CPP) {
      return "jx";
    }
    return std::to_string(coeff_) + "*j" + std::to_string(val_);
  }

  // NOTE [ Inequalities with SingletonInt ]
  //
  // The semantics of SingletonInt when it comes to relations is that it is
  // treated as integer known to be within a certain range,
  //
  //     j0 \in [2, int64_t::max]
  //
  // allowing us to answer queries like j0 >= 1 (True), and j0 == 0 (False).
  // This is a useful default range for the raggedness pattern of a jagged
  // tensor (1) since sizes are non-negative, and (2) we need to get past 0/1
  // specialization checks.
  //
  // [ Indeterminate inequalities error out ]
  //
  // Given the semantic defined above, certain relations like j0 < 3 are thus
  // indeterminable. In our impl today, evaluating such relations error
  //
  // It may seem convenient to just define indeterminate relations to return
  // False, but the implementation we maintain in parallel using sympy does not
  // allow this.
  //
  // Sympy only allows overriding of Ge. The other relations (Lt, Gt, Le) are,
  // by consequence, all derived from Ge e.g., Lt(a, b) := !Ge(a, b). This
  // would mean that means that if we define the indeterminate j0 >= 3 to be
  // False, the also indeterminate j0 < 3 will be evaluated to be True!
  //
  // [ Coefficient are assumed positive ]
  //
  // For the purpose of computing inequalities, we consider the coefficient of
  // the SingletonInt to be a positive integer.
  //
  // Thus, no modifications are needed to the logic since
  // j0 >= k implies coeff * j0 >= k
  //
  c10::SymNode eq(const c10::SymNode& other) override;
  c10::SymNode ne(const c10::SymNode& other) override;
  c10::SymNode ge(const c10::SymNode& other) override;
  c10::SymNode gt(const c10::SymNode& other) override;
  c10::SymNode lt(const c10::SymNode& other) override;
  c10::SymNode le(const c10::SymNode& other) override;
  c10::SymNode mul(const c10::SymNode& other) override;

  c10::optional<int64_t> singleton_int() override {
    TORCH_CHECK(
        type_ == SingletonVariant::PYTHON,
        "shape returned from strided layout NestedTensor does not support this "
        "operation");
    return val_;
  }

  c10::optional<int64_t> singleton_coeff() override {
    TORCH_INTERNAL_ASSERT(type_ == SingletonVariant::PYTHON);
    return coeff_;
  }

  // If we would like to have singleton_vec() as a virtual method, it must
  // be defined on SymNodeImpl, which exists in c10 only. This means we cannot
  // return normal Tensor. The workaround here is to return a pointer instead.
  // Instead of using this method directly, please use get_singleton_vec, if you
  // need a regular Tensor.
  c10::TensorImpl* singleton_vec() override {
    return vec_.unsafeGetTensorImpl();
  }

  int64_t singleton_sum_vec() override {
    TORCH_INTERNAL_ASSERT(type_ == SingletonVariant::PYTHON);
    return sum_vec_;
  }

  bool is_symbolic() override {
    return false;
  }

#define DEFINE_BINARY_NOT_SUPPORTED(name)                           \
  c10::SymNode name(const c10::SymNode& other) override {           \
    TORCH_CHECK(false, #name " not supported by SingletonSymNode"); \
  }

  DEFINE_BINARY_NOT_SUPPORTED(add)
  DEFINE_BINARY_NOT_SUPPORTED(sub)
  DEFINE_BINARY_NOT_SUPPORTED(truediv)
  DEFINE_BINARY_NOT_SUPPORTED(pow)
  DEFINE_BINARY_NOT_SUPPORTED(floordiv)
  DEFINE_BINARY_NOT_SUPPORTED(mod)
  DEFINE_BINARY_NOT_SUPPORTED(sym_min)
  DEFINE_BINARY_NOT_SUPPORTED(sym_max)
  DEFINE_BINARY_NOT_SUPPORTED(sym_and)
  DEFINE_BINARY_NOT_SUPPORTED(sym_or)

#undef DEFINE_BINARY_NOT_SUPPORTED

#define DEFINE_NOT_SUPPORTED(name)                                     \
  c10::SymNode name() override {                                       \
    TORCH_CHECK(false, #name " is not supported by SingletonSymNode"); \
  }

  DEFINE_NOT_SUPPORTED(sym_not)
  DEFINE_NOT_SUPPORTED(ceil)
  DEFINE_NOT_SUPPORTED(floor)
  DEFINE_NOT_SUPPORTED(neg)
  DEFINE_NOT_SUPPORTED(clone)
  DEFINE_NOT_SUPPORTED(sym_float)

#undef DEFINE_NOT_SUPPORTED

 private:
  int64_t val_;
  int64_t coeff_;
  at::Tensor vec_;
  int64_t sum_vec_;
  SingletonVariant type_;
};

TORCH_API at::Tensor get_singleton_vec(const c10::SymNode& node);

} // namespace c10
