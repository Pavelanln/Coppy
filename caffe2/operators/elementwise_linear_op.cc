#include "elementwise_linear_op.h"

namespace caffe2 {

template<>
bool ElementwiseLinearOp<float, CPUContext>::RunOnDevice(){
  const auto& X = Input(0);
  const auto& a = Input(1);
  const auto& b = Input(2);
  auto* Y = Output(0);
  CAFFE_ENFORCE(X.ndim() == 2, X.ndim());
  CAFFE_ENFORCE(a.ndim() == 1, a.ndim());
  CAFFE_ENFORCE(X.dim32(1) == a.dim32(0));
  CAFFE_ENFORCE(a.dims() == b.dims());
  Y->ResizeLike(X);

  const float* X_data = X.data<float>();
  const float* a_data = a.data<float>();
  const float* b_data = b.data<float>();
  float* Y_data = Y->mutable_data<float>();

  const int N = X.dim32(0);
  const int D = X.dim32(1);
  int p = 0;
  for (int n = 0; n < N; ++n) {
    for (int d = 0; d < D; ++d) {
      Y_data[p] = X_data[p] * a_data[d] + b_data[d];
      p++;
    }
  }
  return true;
}

template<>
bool ElementwiseLinearGradientOp<float, CPUContext>::RunOnDevice(){
  const auto& g_o = Input(0);
  const auto& X = Input(1);
  const auto& a = Input(2);
  CAFFE_ENFORCE(X.ndim() == 2, X.ndim());
  CAFFE_ENFORCE(a.ndim() == 1, a.ndim());
  CAFFE_ENFORCE(X.dim32(1) == a.dim32(0));

  auto *g_X = Output(0);
  auto *g_a = Output(1);
  auto *g_b = Output(2);
  g_X->ResizeLike(X);
  g_a->ResizeLike(a);
  g_b->ResizeLike(a);

  const int N = X.dim32(0);
  const int D = X.dim32(1);

  const float* g_o_data = g_o.data<float>();
  const float* X_data = X.data<float>();
  const float* a_data = a.data<float>();
  float* g_X_data = g_X->mutable_data<float>();
  float* g_a_data = g_a->mutable_data<float>();
  float* g_b_data = g_b->mutable_data<float>();

  math::Set<float, CPUContext>(g_a->size(), 0.f, g_a_data, &context_);
  math::Set<float, CPUContext>(g_b->size(), 0.f, g_b_data, &context_);

  int p = 0;
  for (int n = 0; n < N; ++n) {
    for (int d = 0; d < D; ++d) {
      g_X_data[p] = g_o_data[p] * a_data[d];
      g_a_data[d] += g_o_data[p] * X_data[p];
      g_b_data[d] += g_o_data[p];
      p++;
    }
  }
  return true;
}

namespace {

REGISTER_CPU_OPERATOR(
  ElementwiseLinear,
  ElementwiseLinearOp<float, CPUContext>);
REGISTER_CPU_OPERATOR(
  ElementwiseLinearGradient,
  ElementwiseLinearGradientOp<float, CPUContext>);

OPERATOR_SCHEMA(ElementwiseLinear)
  .NumInputs(3)
  .NumOutputs(1)
  .SetDoc(R"DOC(
    Given inputs X of size (N x D), a of size D and b of size D,
    the op computes Y of size (N X D) where Y_{nd} = X_{nd} * a_d + b_d
  )DOC")
  .Input(0, "X", "2D input tensor of size (N X D) data")
  .Input(1, "a", "1D scaling factors of size D")
  .Input(2, "b", "1D biases of size D")
  .Output(0, "Y", "2D output tensor");

OPERATOR_SCHEMA(ElementwiseLinearGradient)
  .NumInputs(3)
  .NumOutputs(3);

struct GetElementwiseLinearGradient : public GradientMakerBase {
  using GradientMakerBase::GradientMakerBase;
  vector<OperatorDef> GetGradientDefs() override {
    return SingleGradientDef(
      "ElementwiseLinearGradient",
      "",
      vector<string>{GO(0), I(0), I(1)},
      vector<string>{GI(0), GI(1), GI(2)});
    }
};

REGISTER_GRADIENT(
  ElementwiseLinear,
  GetElementwiseLinearGradient
);

}  // namespace
}  // namespace caffe2
