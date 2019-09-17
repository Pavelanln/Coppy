#include <ATen/ATen.h>
#include <ATen/core/op_registration/op_registration.h>
#include <ATen/cpp_custom_type_hack.h>
#include <ATen/native/quantized/cpu/fbgemm_utils.h>

#include <algorithm>
#include <string>

namespace at {
namespace native {
namespace {

template <bool ReluFused>
class QLinearInt8 final : public torch::OperatorKernel {
 public:
#ifdef USE_FBGEMM
  at::Tensor operator()(
      at::Tensor input,
      at::Tensor packed_weight,
      double output_scale,
      int64_t output_zero_point) {
    // uint8 * int8 -> uint8 (no quantization/dequantization)

    // We make a strong guarantee that models using these operators will have
    // the same numerics across different machines. Therefore, we do not provide
    // a fallback path and rather fail loudly if we cannot run FBGEMM.
    TORCH_CHECK(
        fbgemm::fbgemmSupportedCPU(), "Your CPU does not support FBGEMM.");

    // TODO: contiguous is called for further jit optimizations.
    auto input_contig = input.contiguous();
    const auto* input_ptr =
        reinterpret_cast<uint8_t*>(input_contig.data_ptr<c10::quint8>());

    TORCH_CHECK(
        input.dim() >= 2,
        "The dimension of input tensor should be larger than or equal to 2");
    // C(output) = A(input) x B(weight), where C, A, B are M x N, M x K, K x N
    // matrices, respectively.
    int64_t M = size_to_dim_(input.dim() - 1, input.sizes());

    // Pull out the PackBMatrix and col_offsets instance from the owning tensor.
    auto& pack_ptr =
        cpp_custom_type_hack::cast<PackedLinearWeight>(packed_weight);
    auto packB = pack_ptr.w.get();
    // packB->printPackedMatrix("packedB inside fbgemm_linear (QLinearInt8): ");
    auto& col_offsets = pack_ptr.col_offsets;

    int64_t N = static_cast<int64_t>(packB->numCols());
    int64_t K = input.size(input.dim() - 1);
    TORCH_CHECK(
        K == static_cast<int64_t>(packB->numRows()),
        "The number of rows in the packB should be equal to K: " +
            std::to_string(K));

    float input_scale_float = input.q_scale();
    int32_t input_zero_point_int32 = input.q_zero_point();

    std::vector<float> output_multiplier_float(1, 0.0);
    std::vector<float> act_times_w_scale(1, 0.0);
    TORCH_CHECK(
        pack_ptr.w_scale.size() == pack_ptr.w_zp.size(),
        "Weight scales and zero points vectors should have the same size.");
    if (pack_ptr.q_scheme == kPerTensorAffine) {
      // Process the per tensor quantization.
      act_times_w_scale[0] = (input_scale_float * pack_ptr.w_scale[0]);
      output_multiplier_float[0] =
          act_times_w_scale[0] / static_cast<float>(output_scale);
    } else if (pack_ptr.q_scheme == kPerChannelAffine) {
      // Process the per channel quantization.
      output_multiplier_float.resize(N, 0.0);
      act_times_w_scale.resize(N, 1.0f);
      for (int i = 0; i < N; ++i) {
        act_times_w_scale[i] = (input_scale_float * pack_ptr.w_scale[i]);
        output_multiplier_float[i] =
            act_times_w_scale[i] / static_cast<float>(output_scale);
      }
    }
    int32_t output_zero_point_int32 = static_cast<int32_t>(output_zero_point);

    // This operation does the following:
    // 1) Creates a "row buffer" vector with offset values that must be added
    //    to the integer matrix multiplication operation to ensure correctness.
    //    This "row buffer" is also called the row offset, and it is needed when
    //    we use affine quantization for weights.
    // 2) Packs the resulting quantized matrix into vector-register and cache
    //    friendly tiles.
    //
    //  Note this is not executed eagerly, but rather within the fbgemmPacked
    //  call below.
    fbgemm::PackAWithRowOffset<uint8_t> packA(
        /*trans=*/fbgemm::matrix_op_t::NoTranspose,
        /*nRow=*/M,
        /*nCol=*/K,
        /*smat=*/input_ptr,
        /*ld=*/K,
        /*pmat=*/nullptr); // Currently, packA manages ownership of `pmat`.
                           // TODO: Consider a way to pre-allocate and reuse
                           // pmat buffer.

    // ReQuantizeOutput requires pointers to the zero point values,
    // since in the case of rowwise quantization these will be arrays rather
    // than scalars. But in this case, we're doing whole-tensor quantization so
    // we just pass a pointer to the scale values (and internally
    // ReQuantizeOutput won't index past 0.

    // This is the end of the pipeline, pass the resulting matrix through.
    fbgemm::DoNothing<> doNothingObj{};

    const float* bias_ptr = nullptr;
    at::Tensor bias;
    if (pack_ptr.bias.has_value()) {
      bias = pack_ptr.bias.value();
      bias = bias.contiguous();
      TORCH_CHECK(bias.dim() == 1, "bias should be a vector (1D Tensor)");
      TORCH_CHECK(
          bias.size(0) == N,
          "bias should have N elements: " + std::to_string(N));
      bias_ptr = reinterpret_cast<float*>(bias.data_ptr<float>());
    }

    // The resulting matrix here is 2-D, let's view it with the original
    // left hand dimensions of the input. Here are two examples:
    // 1. If the input tensor is {M, K}, the output tensor is {M, N}.
    // 2. If the input tensor is {b, M, K}, the output tensor is {b, M, N}.
    std::vector<int64_t> out_sizes = input.sizes().vec();
    out_sizes.back() = N;
    // Allocate output Tensor and a buffer for fbgemmPacked to use
    auto output = _empty_affine_quantized(
        out_sizes,
        at::device(kCPU).dtype(kQUInt8),
        output_scale,
        output_zero_point);

    auto buffer = at::zeros_like(output, output.options().dtype(at::kInt));

    if (pack_ptr.q_scheme == kPerTensorAffine) {
      // Process the per tensor quantization.
      //
      // After the uint8 * int8 matrix multiplication is performed, this
      // operation does:
      //  1) Add in row and column offsets to the rows and columns,
      //  respectively.
      //  2) Add in the bias term.
      fbgemm::ReQuantizeOutput<
          ReluFused,
          fbgemm::QuantizationGranularity::TENSOR,
          float>
          outputProcObj(
              doNothingObj,
              output_multiplier_float.data(),
              output_zero_point_int32,
              input_zero_point_int32,
              pack_ptr.w_zp.data(),
              packA.getRowOffsetBuffer(),
              col_offsets.data(),
              bias_ptr,
              N, /* nCol */
              1 /* groups */,
              act_times_w_scale.data());

      // Do the GEMM
      fbgemm::fbgemmPacked(
          /*packA=*/packA,
          /*packB=*/*packB,
          /*C=*/reinterpret_cast<uint8_t*>(output.data_ptr<c10::quint8>()),
          /*C_buffer=*/buffer.data_ptr<int32_t>(),
          /*ldc=*/N,
          /*outProcess=*/outputProcObj,
          /*thread_id=*/0,
          /*num_threads=*/1);
    } else if (pack_ptr.q_scheme == kPerChannelAffine) {
      // Process the per channel quantization.
      //
      // After the uint8 * int8 matrix multiplication is performed, this
      // operation does:
      //  1) Add in row and column offsets to the rows and columns,
      //  respectively.
      //  2) Add in the bias term.
      fbgemm::ReQuantizeOutput<
          ReluFused,
          fbgemm::QuantizationGranularity::OUT_CHANNEL,
          float>
          outputProcObj(
              doNothingObj,
              output_multiplier_float.data(),
              output_zero_point_int32,
              input_zero_point_int32,
              pack_ptr.w_zp.data(),
              packA.getRowOffsetBuffer(),
              col_offsets.data(),
              bias_ptr,
              N, /*nCol=*/
              1, /* groups*/
              act_times_w_scale.data());

      // Do the GEMM
      fbgemm::fbgemmPacked(
          /*packA=*/packA,
          /*packB=*/*packB,
          /*C=*/reinterpret_cast<uint8_t*>(output.data_ptr<c10::quint8>()),
          /*C_buffer=*/buffer.data_ptr<int32_t>(),
          /*ldc=*/N,
          /*outProcess=*/outputProcObj,
          /*thread_id=*/0,
          /*num_threads=*/1);
    }
    return output;
  }
#else // USE_FBGEMM
  at::Tensor operator()(
      at::Tensor /* input */,
      at::Tensor /* packed_weight */,
      double /* output_scale */,
      int64_t /* output_zero_point */) {
    // We make a strong guarantee that models using these operators will have
    // the same numerics across different machines. Therefore, we do not provide
    // a fallback path and rather fail loudly if we cannot run FBGEMM.
    TORCH_CHECK(
        false, "This PyTorch installation was not built with FBGEMM operators");
  }
#endif // USE_FBGEMM
};

static auto registry =
    torch::RegisterOperators()
        .op("quantized::linear(Tensor X, Tensor W_prepack, float Y_scale_i, int Y_zero_point_i) -> Tensor Y",
            torch::RegisterOperators::options().kernel<QLinearInt8<false>>(
                TensorTypeId::QuantizedCPUTensorId))
        .op("quantized::linear_relu(Tensor X, Tensor W_prepack, float Y_scale_i, int Y_zero_point_i) -> Tensor Y",
            torch::RegisterOperators::options().kernel<QLinearInt8<true>>(
                TensorTypeId::QuantizedCPUTensorId));
} // namespace
} // namespace native
} // namespace at
