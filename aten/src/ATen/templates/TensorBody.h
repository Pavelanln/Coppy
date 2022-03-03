#pragma once

#ifdef TORCH_ASSERT_NO_OPERATORS
#error This change adds a dependency on native_functions.yaml,            \
  meaning the file will need to be re-compiled every time an operator     \
  is changed or added. Consider if your change would be better placed in  \
  another file, or if a more specific header might achieve the same goal. \
  See NOTE: [Tensor vs. TensorBase]
#endif

#include <c10/core/Device.h>
#include <c10/core/Layout.h>
#include <c10/core/MemoryFormat.h>
#include <c10/core/QScheme.h>
#include <c10/core/Stream.h>
#include <c10/core/Scalar.h>
#include <c10/core/ScalarType.h>
#include <c10/core/ScalarTypeToTypeMeta.h>
#include <c10/core/Storage.h>
#include <ATen/core/TensorAccessor.h>
#include <c10/core/TensorImpl.h>
#include <c10/core/UndefinedTensorImpl.h>
#include <c10/core/WrapDimMinimal.h>
#include <c10/util/Exception.h>
#include <c10/util/Deprecated.h>
#include <c10/util/MaybeOwned.h>
#include <c10/util/Optional.h>
#include <c10/util/intrusive_ptr.h>
#include <c10/macros/Export.h>
#include <ATen/core/CheckMemoryFormat.h>
#include <ATen/core/DeprecatedTypePropertiesRegistry.h>
#include <ATen/core/DeprecatedTypeProperties.h>
#include <ATen/core/NamedTensor.h>
#include <ATen/core/QuantizerBase.h>
#include <ATen/core/TensorBase.h>

#include <ATen/MethodOperators.h>

namespace c10{
template<class T> class List;
}
namespace at {
struct Generator;
struct Type;
class DeprecatedTypeProperties;
class Tensor;
} // namespace at
namespace at {
namespace indexing {
struct TensorIndex;
} // namespace indexing
} // namespace at

namespace torch { namespace autograd {

struct Node;

}} // namespace torch::autograd

namespace at {

class OptionalTensorRef;
class Tensor;
using TensorList = ArrayRef<Tensor>;

using Stream = c10::Stream;

// Tensor is a "generic" object holding a pointer to the underlying TensorImpl object, which
// has an embedded reference count. In this way, Tensor is similar to boost::intrusive_ptr.
//
// For example:
//
// void func(Tensor a) {
//   Tensor b = a;
//   ...
// }
//
// In this example, when we say Tensor b = a, we are creating a new object that points to the
// same underlying TensorImpl, and bumps its reference count. When b goes out of scope, the
// destructor decrements the reference count by calling release() on the TensorImpl it points to.
// The existing constructors, operator overloads, etc. take care to implement the correct semantics.
//
// Note that Tensor can also be NULL, i.e. it is not associated with any underlying TensorImpl, and
// special care must be taken to handle this.
class TORCH_API Tensor: public TensorBase {
 protected:
  // Create a Tensor with a +0 reference count. Special care must be
  // taken to avoid decrementing this reference count at destruction
  // time. Intended to support MaybeOwnedTraits<Tensor>.
  explicit Tensor(unsafe_borrow_t, const TensorBase& rhs): TensorBase(unsafe_borrow_t{}, rhs) {}
  friend MaybeOwnedTraits<Tensor>;
  friend OptionalTensorRef;

 public:
  Tensor() = default;
  // This constructor should not be used by end users and is an implementation
  // detail invoked by autogenerated code.
  explicit Tensor(
      c10::intrusive_ptr<TensorImpl, UndefinedTensorImpl> tensor_impl)
      : TensorBase(std::move(tensor_impl)) {}
  Tensor(const Tensor &tensor) = default;
  Tensor(Tensor &&tensor) = default;

  // Implicitly move-constructible from TensorBase, but must be explicit to increase refcount
  explicit Tensor(const TensorBase &base): TensorBase(base) {}
  /*implicit*/ Tensor(TensorBase &&base): TensorBase(std::move(base)) {}

  // Creates a new wrapper from TensorImpl. Intentionally a free method because
  // it should be used with care. Checks necessary invariants
  static Tensor wrap_tensor_impl(
      c10::intrusive_ptr<TensorImpl, UndefinedTensorImpl> tensor_impl) {
    return TensorBase::wrap_tensor_impl(std::move(tensor_impl));
  }

  Tensor contiguous(MemoryFormat memory_format=MemoryFormat::Contiguous) const {
    return TensorBase::contiguous(memory_format);
  }

  Tensor conj() const {
    if (!this->is_complex()) {
      return *this;
    } else {
      if (this->is_sparse()) {
        return this->conj_physical();
      }
      return this->_conj();
    }
  }

  // Aliased by Dimname overloads, so need explicit using
  using TensorBase::size;
  using TensorBase::stride;

  /// Should be used if *this can reasonably be expected to be contiguous and
  /// performance is important.
  /// Compared to contiguous, it saves a reference count
  /// increment/decrement if *this is already contiguous, at the cost
  /// in all cases of an extra pointer of stack usage, an extra branch
  /// to access, and an extra branch at destruction time.
  c10::MaybeOwned<Tensor> expect_contiguous(MemoryFormat memory_format=MemoryFormat::Contiguous) const &;

  // Use .contiguous() instead. Trying to borrow from a prvalue Tensor
  // will only lead to trouble and dangling references.
  c10::MaybeOwned<Tensor> expect_contiguous(MemoryFormat memory_format=MemoryFormat::Contiguous) && = delete;

  // The following overloads are very intruiging.  Consider the following
  // program:
  //
  //    x[1] = 3;
  //
  // We would expect that the first entry of x is written to 3.  But how can we
  // actually achieve this?  x[1] evaluates to a tensor...
  //
  // The answer is, using a ref-qualifier.  x[1] is an rvalue, which cannot be
  // (profitably) assigned to in the traditional sense, so we overload
  // assignment to mean, "Actually, copy 3 into the tensor data."  This is done
  // with an rvalue-reference ref-qualified overload (the methods with && at the
  // end of their type.)
  //
  // There's one more fly in the ointment: We also want
  //
  //    Tensor x = y;
  //
  // to work, and we want it NOT to copy.  So we need a traditional operator=
  // overload.  But we MUST specify a mutable lvalue ref-qualifier, to
  // disambiguate the traditional overload from the rvalue-reference
  // ref-qualified overload.  Otherwise, it will be ambiguous, because
  // a non ref-qualified method is eligible for all situations.

  // Unfortunately, we have to write these constructors out manually
  // to work around an MSVC bug:
  //    error C2580: 'at::Tensor &at::Tensor::operator =(const at::Tensor &) &':
  //    multiple versions of a defaulted special member functions are not allowed
  // Tensor& operator=(const Tensor&) & = default;
  // Tensor& operator=(Tensor&&) & = default;

  // Also MSVC will wrongly issue the following warning with the aforementioned fix
  //    warning C4522: 'at::Tensor': multiple assignment operators specified
  // Let's just skip the warning.
  //
  // TODO: temporarily disabled

  Tensor& operator=(const TensorBase& x) & {
    impl_ = x.getIntrusivePtr();
    return *this;
  }
  Tensor& operator=(TensorBase&& x) & {
    impl_ = x.unsafeReleaseIntrusivePtr();
    return *this;
  }

  Tensor& operator=(const Tensor &x) & {
    return operator=(static_cast<const TensorBase&>(x));
  }
  Tensor& operator=(Tensor &&x) & {
    return operator=(static_cast<TensorBase&&>(x));
  }

  Tensor& operator=(Scalar v) && {
    return fill_(v);
  }
  Tensor& operator=(const Tensor &rhs) && {
    return copy_(rhs);
  }
  Tensor& operator=(Tensor&& rhs) && {
    return copy_(rhs);
  }

  C10_DEPRECATED_MESSAGE("Tensor.type() is deprecated. Instead use Tensor.options(), which in many cases (e.g. in a constructor) is a drop-in replacement. If you were using data from type(), that is now available from Tensor itself, so instead of tensor.type().scalar_type(), use tensor.scalar_type() instead and instead of tensor.type().backend() use tensor.device().")
  DeprecatedTypeProperties & type() const {
    return globalDeprecatedTypePropertiesRegistry().getDeprecatedTypeProperties(
        dispatchKeyToBackend(legacyExtractDispatchKey(key_set())),
        scalar_type());
  }

  Tensor toType(ScalarType t) const {
    return to(options().dtype(t), /*non_blocking*/ false, /*copy*/ false);
  }

  // TODO: Deprecate me
  Tensor toBackend(Backend b) const {
    return to(options().device(backendToDeviceType(b)).layout(layout_from_backend(b)), /*non_blocking*/ false, /*copy*/ false);
  }

  C10_DEPRECATED_MESSAGE("Tensor.is_variable() is deprecated; everything is a variable now. (If you want to assert that variable has been appropriately handled already, use at::impl::variable_excluded_from_dispatch())")
  bool is_variable() const noexcept {
    return !at::impl::variable_excluded_from_dispatch();
  }

  template<typename T>
  C10_DEPRECATED_MESSAGE("Tensor.data<T>() is deprecated. Please use Tensor.data_ptr<T>() instead.")
  T * data() const {
    return data_ptr<T>();
  }

  template <typename T>
  T item() const;

  template<typename T, size_t N, template <typename U> class PtrTraits = DefaultPtrTraits, typename index_t = int64_t>
  C10_DEPRECATED_MESSAGE("packed_accessor is deprecated, use packed_accessor32 or packed_accessor64 instead")
  GenericPackedTensorAccessor<T,N,PtrTraits,index_t> packed_accessor() const & {
    return generic_packed_accessor<T,N,PtrTraits,index_t>();
  }
  template<typename T, size_t N, template <typename U> class PtrTraits = DefaultPtrTraits, typename index_t = int64_t>
  C10_DEPRECATED_MESSAGE("packed_accessor is deprecated, use packed_accessor32 or packed_accessor64 instead")
  GenericPackedTensorAccessor<T,N,PtrTraits,index_t> packed_accessor() && = delete;

  Tensor operator~() const {
    return bitwise_not();
  }
  Tensor operator-() const {
    return neg();
  }
  Tensor& operator+=(const Tensor & other) {
    return add_(other);
  }
  Tensor& operator+=(Scalar other) {
    return add_(other);
  }
  Tensor& operator-=(const Tensor & other) {
    return sub_(other);
  }
  Tensor& operator-=(Scalar other) {
    return sub_(other);
  }
  Tensor& operator*=(const Tensor & other) {
    return mul_(other);
  }
  Tensor& operator*=(Scalar other) {
    return mul_(other);
  }
  Tensor& operator/=(const Tensor & other) {
    return div_(other);
  }
  Tensor& operator/=(Scalar other) {
    return div_(other);
  }
  Tensor& operator&=(const Tensor & other) {
    return bitwise_and_(other);
  }
  Tensor& operator|=(const Tensor & other) {
    return bitwise_or_(other);
  }
  Tensor& operator^=(const Tensor & other) {
    return bitwise_xor_(other);
  }
  Tensor operator[](Scalar index) const {
    if (!index.isIntegral(false)) {
      TORCH_CHECK_INDEX(false, "Can only index tensors with integral scalars");
    }
    return this->operator[](index.toLong());
  }
  Tensor operator[](Tensor index) const {
    // These properties are checked in the Scalar constructor, but we already
    // check them here to provide more useful diagnostics for the user.
    if (!index.defined()) {
      TORCH_CHECK_INDEX(false, "Can only index with tensors that are defined");
    }
    if (index.dim() != 0) {
      TORCH_CHECK_INDEX(false,
                        "Can only index with tensors that are scalars (zero-dim)");
    }
    // The Scalar(Tensor) constructor is explicit, so we need to call it.
    return this->operator[](index.item());
  }
  Tensor operator[](int64_t index) const {
    return select(0, index);
  }

  Tensor index(ArrayRef<at::indexing::TensorIndex> indices) const;
  Tensor index(std::initializer_list<at::indexing::TensorIndex> indices) const;

  Tensor & index_put_(ArrayRef<at::indexing::TensorIndex> indices, Tensor const & rhs);
  Tensor & index_put_(ArrayRef<at::indexing::TensorIndex> indices, const Scalar& v);
  Tensor & index_put_(std::initializer_list<at::indexing::TensorIndex> indices, Tensor const & rhs);
  Tensor & index_put_(std::initializer_list<at::indexing::TensorIndex> indices, const Scalar& v);

  Tensor cpu() const {
    return to(options().device(DeviceType::CPU), /*non_blocking*/ false, /*copy*/ false);
  }

  // TODO: The Python version also accepts arguments
  Tensor cuda() const {
    return to(options().device(DeviceType::CUDA), /*non_blocking*/ false, /*copy*/ false);
  }

  Tensor hip() const {
    return to(options().device(DeviceType::HIP), /*non_blocking*/ false, /*copy*/ false);
  }

  Tensor ve() const {
    return to(options().device(DeviceType::VE), /*non_blocking*/ false, /*copy*/ false);
  }

  Tensor vulkan() const {
    return to(options().device(DeviceType::Vulkan), /*non_blocking*/ false, /*copy*/ false);
  }

  Tensor metal() const {
    return to(options().device(DeviceType::Metal), /*non_blocking*/ false, /*copy*/ false);
  }

  Tensor meta() const {
    return to(options().device(DeviceType::Meta), /*non_blocking*/ false, /*copy*/ false);
  }

  // ~~~~~ Autograd API ~~~~~

  /// \fn bool is_leaf() const;
  ///
  /// All Tensors that have `requires_grad()` which is ``false`` will be leaf Tensors by convention.
  ///
  /// For Tensors that have `requires_grad()` which is ``true``, they will be leaf Tensors if they were
  /// created by the user. This means that they are not the result of an operation and so
  /// `grad_fn()` is `nullptr`.
  ///
  /// Only leaf Tensors will have their `grad()` populated during a call to `backward()`.
  /// To get `grad()` populated for non-leaf Tensors, you can use `retain_grad()`.
  ///
  /// Example:
  /// @code
  /// auto a = torch::rand(10, torch::requires_grad());
  /// std::cout << a.is_leaf() << std::endl; // prints `true`
  ///
  /// auto b = torch::rand(10, torch::requires_grad()).to(torch::kCUDA);
  /// std::cout << b.is_leaf() << std::endl; // prints `false`
  /// // b was created by the operation that cast a cpu Tensor into a cuda Tensor
  ///
  /// auto c = torch::rand(10, torch::requires_grad()) + 2;
  /// std::cout << c.is_leaf() << std::endl; // prints `false`
  /// // c was created by the addition operation
  ///
  /// auto d = torch::rand(10).cuda();
  /// std::cout << d.is_leaf() << std::endl; // prints `true`
  /// // d does not require gradients and so has no operation creating it (that is tracked by the autograd engine)
  ///
  /// auto e = torch::rand(10).cuda().requires_grad_();
  /// std::cout << e.is_leaf() << std::endl; // prints `true`
  /// // e requires gradients and has no operations creating it
  ///
  /// auto f = torch::rand(10, torch::device(torch::kCUDA).requires_grad(true));
  /// std::cout << f.is_leaf() << std::endl; // prints `true`
  /// // f requires grad, has no operation creating it
  /// @endcode

  /// \fn void backward(const Tensor & gradient={}, c10::optional<bool> retain_graph=c10::nullopt, bool create_graph=false, c10::optional<TensorList> inputs=c10::nullopt) const;
  ///
  /// Computes the gradient of current tensor with respect to graph leaves.
  ///
  /// The graph is differentiated using the chain rule. If the tensor is
  /// non-scalar (i.e. its data has more than one element) and requires
  /// gradient, the function additionally requires specifying ``gradient``.
  /// It should be a tensor of matching type and location, that contains
  /// the gradient of the differentiated function w.r.t. this Tensor.
  ///
  /// This function accumulates gradients in the leaves - you might need to
  /// zero them before calling it.
  ///
  /// \param gradient Gradient w.r.t. the
  ///     tensor. If it is a tensor, it will be automatically converted
  ///     to a Tensor that does not require grad unless ``create_graph`` is True.
  ///     None values can be specified for scalar Tensors or ones that
  ///     don't require grad. If a None value would be acceptable then
  ///     this argument is optional.
  /// \param retain_graph If ``false``, the graph used to compute
  ///     the grads will be freed. Note that in nearly all cases setting
  ///     this option to True is not needed and often can be worked around
  ///     in a much more efficient way. Defaults to the value of
  ///     ``create_graph``.
  /// \param create_graph If ``true``, graph of the derivative will
  ///     be constructed, allowing to compute higher order derivative
  ///     products. Defaults to ``false``.
  /// \param inputs Inputs w.r.t. which the gradient will be accumulated into
  ///     ``at::Tensor::grad``. All other Tensors will be ignored. If not
  ///     provided, the gradient is accumulated into all the leaf Tensors
  ///     that were used to compute the current tensor.
  ///     When inputs are provided and a given input is not a leaf,
  ///     the current implementation will call its grad_fn (even though it is not strictly needed to get this gradients).
  ///     It is an implementation detail on which the user should not rely.
  ///     See https://github.com/pytorch/pytorch/pull/60521#issuecomment-867061780 for more details.
  void backward(const Tensor & gradient={}, c10::optional<bool> retain_graph=c10::nullopt, bool create_graph=false, c10::optional<TensorList> inputs=c10::nullopt) const {
    // NB: Adding this wrapper to _backward here because we'd like our
    // 'backwards' api to accept the 'inputs' argument optionally. Since code gen
    // currently does not support optional of TensorList our approach is to replace
    // backward in native_functions.yaml with _backward and call it here instead.
    if (inputs.has_value()) {
      TORCH_CHECK(inputs.value().size() > 0, "'inputs' argument to backward cannot be empty")
      this->_backward(inputs.value(), gradient, retain_graph, create_graph);
    } else {
      this->_backward({}, gradient, retain_graph, create_graph);
    }
  }

  /// \fn Tensor detach() const;
  ///
  /// Returns a new Tensor, detached from the current graph.
  /// The result will never require gradient.

  /// \fn Tensor & detach_() const;
  ///
  /// Detaches the Tensor from the graph that created it, making it a leaf.
  /// Views cannot be detached in-place.

  /// \fn void retain_grad() const;
  ///
  /// Enables this Tensor to have their :attr:`grad` populated during
  /// :func:`backward`. This is a no-op for leaf tensors.

  /// \fn bool retains_grad() const;
  ///
  /// Is ``true`` if this Tensor is non-leaf and its :attr:`grad` is enabled to be
  /// populated during :func:`backward`, ``false`` otherwise.

  const Tensor& set_requires_grad(bool requires_grad) const {
    TensorBase::set_requires_grad(requires_grad);
    return *this;
  }

  /// Return a mutable reference to the gradient. This is conventionally
  /// used as `t.grad() = x` to set a gradient to a completely new tensor.
  /// Note that this function work with a non-const Tensor and is not
  /// thread safe.
  Tensor& mutable_grad() const {
    return impl_->mutable_grad();
  }

  /// This function returns an undefined tensor by default and returns a defined tensor
  /// the first time a call to `backward()` computes gradients for this Tensor.
  /// The attribute will then contain the gradients computed and future calls
  /// to `backward()` will accumulate (add) gradients into it.
  const Tensor& grad() const {
    const Tensor& maybe_grad = impl_->grad();
    if (!is_leaf() && !retains_grad() && !maybe_grad.defined()) {
      TORCH_WARN(
        "The .grad attribute of a Tensor that is not a leaf Tensor is being accessed. Its .grad "
        "attribute won't be populated during autograd.backward(). If you indeed want the .grad "
        "field to be populated for a non-leaf Tensor, use .retain_grad() on the non-leaf Tensor. "
        "If you access the non-leaf Tensor by mistake, make sure you access the leaf Tensor "
        "instead. See github.com/pytorch/pytorch/pull/30531 for more informations.");
    }
    return maybe_grad;
  }

  // The Forward AD API functions below are low level and are not to be used by end
  // users who should use the API provided in torch/csrc/autograd.h

  /// This function returns the forward gradient for this Tensor at the given level.
  const Tensor& _fw_grad(uint64_t level) const {
    return impl_->_fw_grad(level, *this);
  }

  /// This function can be used to set the value of the forward grad.
  /// Note that the given new_grad might not be used directly if it has different
  /// metadata (size/stride/storage offset) compared to this Tensor. In that case,
  /// new_grad content will be copied into a new Tensor
  void _set_fw_grad(const TensorBase& new_grad, uint64_t level, bool is_inplace_op) const {
    impl_->_set_fw_grad(new_grad, *this, level, is_inplace_op);
  }


  // STOP.  Thinking of adding a method here, which only makes use
  // of other ATen methods?  Define it in native_functions.yaml.

  //example
  //Tensor * add(Tensor & b);
  ${tensor_method_declarations}

  // Special C++ only overloads for std()-like functions (See gh-40287)
  // These are needed because int -> bool conversion takes precedence over int -> IntArrayRef
  // So, for example std(0) would select the std(unbiased=False) overload

  Tensor var(int dim) const {
    return var(IntArrayRef{dim});
  }

  Tensor std(int dim) const {
    return std(IntArrayRef{dim});
  }

  // We changed .dtype() to return a TypeMeta in #12766. Ideally, we want the
  // at::kDouble and its friends to be TypeMeta's, but that hasn't happened yet.
  // Before that change, we make this method to maintain BC for C++ usage like
  // `x.to(y.dtype)`.
  // TODO: remove following two after at::kDouble and its friends are TypeMeta's.
  inline Tensor to(caffe2::TypeMeta type_meta, bool non_blocking=false, bool copy=false) const {
    return this->to(/*scalar_type=*/typeMetaToScalarType(type_meta), non_blocking, copy);
  }
  inline Tensor to(Device device, caffe2::TypeMeta type_meta, bool non_blocking=false, bool copy=false) const {
    return this->to(device, /*scalar_type=*/typeMetaToScalarType(type_meta), non_blocking, copy);
  }

  template <typename F, typename... Args>
  decltype(auto) m(F func, Args&&... params) const {
    return func(*this, std::forward<Args>(params)...);
  }

  /// NOTE: This is similar to the legacy `.data()` function on `Variable`, and is intended
  /// to be used from functions that need to access the `Variable`'s equivalent `Tensor`
  /// (i.e. `Tensor` that shares the same storage and tensor metadata with the `Variable`).
  ///
  /// One notable difference with the legacy `.data()` function is that changes to the
  /// returned `Tensor`'s tensor metadata (e.g. sizes / strides / storage / storage_offset)
  /// will not update the original `Variable`, due to the fact that this function
  /// shallow-copies the `Variable`'s underlying TensorImpl.
  at::Tensor tensor_data() const {
    return TensorBase::tensor_data();
  }

  /// NOTE: `var.variable_data()` in C++ has the same semantics as `tensor.data`
  /// in Python, which create a new `Variable` that shares the same storage and
  /// tensor metadata with the original `Variable`, but with a completely new
  /// autograd history.
  ///
  /// NOTE: If we change the tensor metadata (e.g. sizes / strides /
  /// storage / storage_offset) of a variable created from `var.variable_data()`, those
  /// changes will not update the original variable `var`. In `.variable_data()`, we set
  /// `allow_tensor_metadata_change_` to false to make such changes explicitly illegal,
  /// in order to prevent users from changing metadata of `var.variable_data()`
  /// and expecting the original variable `var` to also be updated.
  at::Tensor variable_data() const {
    return TensorBase::variable_data();
  }

  // Hooks
  //~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  template <typename T>
  using hook_return_void_t = std::enable_if_t<std::is_void<typename std::result_of<T&(Tensor)>::type>::value, unsigned>;
  template <typename T>
  using hook_return_var_t = std::enable_if_t<std::is_same<typename std::result_of<T&(Tensor)>::type, Tensor>::value, unsigned>;

  /// Registers a backward hook.
  ///
  /// The hook will be called every time a gradient with respect to the Tensor is computed.
  /// The hook should have one of the following signature:
  /// ```
  /// hook(Tensor grad) -> Tensor
  /// ```
  /// ```
  /// hook(Tensor grad) -> void
  /// ```
  /// The hook should not modify its argument, but it can optionally return a new gradient
  /// which will be used in place of `grad`.
  ///
  /// This function returns the index of the hook in the list which can be used to remove hook.
  ///
  /// Example:
  /// @code
  /// auto v = torch::tensor({0., 0., 0.}, torch::requires_grad());
  /// auto h = v.register_hook([](torch::Tensor grad){ return grad * 2; }); // double the gradient
  /// v.backward(torch::tensor({1., 2., 3.}));
  /// // This prints:
  /// // ```
  /// //  2
  /// //  4
  /// //  6
  /// // [ CPUFloatType{3} ]
  /// // ```
  /// std::cout << v.grad() << std::endl;
  /// v.remove_hook(h);  // removes the hook
  /// @endcode
  template <typename T>
  hook_return_void_t<T> register_hook(T&& hook) const;
  template <typename T>
  hook_return_var_t<T> register_hook(T&& hook) const;

  // Variable methods
  //~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  Tensor data() const {
    return TensorBase::data();
  }

  void _backward(TensorList inputs, const c10::optional<Tensor>& gradient, c10::optional<bool> keep_graph, bool create_graph) const;

  const Tensor& requires_grad_(bool _requires_grad=true) const {
    TensorBase::requires_grad_(_requires_grad);
    return *this;
  }
};

namespace detail {
// Helper creator for Tensor class which doesn't requires the users to pass
// in an intrusive_ptr instead it just converts the argument passed to
// requested intrusive_ptr type.
template <typename T, typename... Args>
Tensor make_tensor(Args&&... args) {
  return Tensor(c10::make_intrusive<T>(std::forward<Args>(args)...));
}

} // namespace detail

} // namespace at

// See Note [Avoiding Include Cycles In Static Dispatch]
${static_dispatch_ops_headers}
namespace at {
${tensor_method_definitions}
} // namespace at


namespace c10 {
template <>
struct MaybeOwnedTraits<at::Tensor> {
  using owned_type = at::Tensor;
  using borrow_type = at::Tensor;

  static borrow_type createBorrow(const owned_type& from) {
    // NOTE: this can be implemented without the special
    // unsafe_borrow_t Tensor constructor as
    //
    // return borrow_type(c10::intrusive_ptr<at::TensorImpl, at::UndefinedTensorImpl>::reclaim(from.unsafeGetTensorImpl()));
    //
    // but that hurts inlining due to the nullptr check in the
    // Tensor(c10::intrusive_ptr<...>) constructor. We already know
    // that from.impl_ isn't null because from is a valid Tensor, so
    // we needn't do the check again. (using __builtin_assume can
    // avoid this, but wouldn't be portable to MSVC.)
    return borrow_type(borrow_type::unsafe_borrow_t{}, from);
  }

  static void assignBorrow(borrow_type& lhs, const borrow_type& rhs) {
    lhs.unsafeReleaseTensorImpl();
    // See above note: this can be implemented with public API
    // similarly to createBorrow(), but that would hurt inlining.
    lhs = borrow_type(borrow_type::unsafe_borrow_t{}, rhs);
  }

  static void destroyBorrow(borrow_type& toDestroy) {
    toDestroy.unsafeReleaseTensorImpl(); // "leak" it, but it was already +0.
  }

  static const owned_type& referenceFromBorrow(const borrow_type& borrow) {
    return borrow;
  }

  static const owned_type* pointerFromBorrow(const borrow_type& borrow) {
    return &borrow;
  }

  static bool debugBorrowIsValid(const borrow_type& borrow) {
    return true;
  }
};

template <>
struct ExclusivelyOwnedTraits<at::Tensor> {
  using repr_type = at::Tensor;
  using pointer_type = at::Tensor*;
  using const_pointer_type = const at::Tensor*;

  static repr_type nullRepr() {
    return at::Tensor();
  }

  template <class... Args>
  static repr_type createInPlace(Args&&... args) {
    return at::Tensor(std::forward<Args>(args)...);
  }

  static repr_type moveToRepr(at::Tensor&& x) {
    return std::move(x);
  }

  static void destroyOwned(at::Tensor& x) {
    return ExclusivelyOwnedTraits<at::TensorBase>::destroyOwned(x);
  }

  static at::Tensor take(at::Tensor& x) {
    return std::move(x);
  }

  static pointer_type getImpl(repr_type& x) {
    return &x;
  }

  static const_pointer_type getImpl(const repr_type& x) {
    return &x;
  }
};
} // namespace c10

namespace at {

inline c10::MaybeOwned<Tensor> borrow_from_optional_tensor(
    const c10::optional<Tensor>& opt) {
  return opt.has_value()
    ? c10::MaybeOwned<Tensor>::borrowed(*opt)
    : c10::MaybeOwned<Tensor>::owned(c10::in_place);
}

inline c10::MaybeOwned<Tensor> Tensor::expect_contiguous(MemoryFormat memory_format) const & {
  if (is_contiguous(memory_format)) {
    return c10::MaybeOwned<Tensor>::borrowed(*this);
  } else {
    return c10::MaybeOwned<Tensor>::owned(__dispatch_contiguous(memory_format));
  }
}
} // namespace at
