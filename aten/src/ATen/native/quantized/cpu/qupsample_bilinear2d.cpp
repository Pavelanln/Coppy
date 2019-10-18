#include <ATen/ATen.h>
#include <ATen/native/UpSample.h>
#include <ATen/native/quantized/cpu/quantized_ops.h>
#include <ATen/quantized/Quantizer.h>

#include <algorithm>
#include <cmath>
#include <cstring>
#include <limits>

namespace at {
namespace native {
namespace {

// at::native functions for the native_functions.yaml
template <typename scalar_t>
static void upsample_bilinear2d_out_frame(
    Tensor& output,
    const Tensor& input,
    int64_t input_height,
    int64_t input_width,
    int64_t output_height,
    int64_t output_width,
    int64_t nbatch,
    int64_t channels,
    bool align_corners) {
  auto* idata = static_cast<scalar_t*>(input.data_ptr());
  auto* odata = static_cast<scalar_t*>(output.data_ptr());

  channels = channels * nbatch;
  auto* i_p = reinterpret_cast<typename scalar_t::underlying*>(idata);
  auto* o_p = reinterpret_cast<typename scalar_t::underlying*>(odata);

  // special case: just copy
  if (input_height == output_height && input_width == output_width) {
    std::memcpy(
        o_p,
        i_p,
        channels * input_height * input_width *
            sizeof(typename scalar_t::underlying));
    return;
  }

  const auto rheight = area_pixel_compute_scale<float>(
      input_height, output_height, align_corners);

  const auto rwidth =
      area_pixel_compute_scale<float>(input_width, output_width, align_corners);
  float output_scale = output.q_scale() / input.q_scale();

  for (int64_t h2 = 0; h2 < output_height; ++h2) {
    const auto h1r = area_pixel_compute_source_index<float>(
        rheight, h2, align_corners, /*cubic=*/false);

    const int64_t h1 = h1r;
    const int64_t h1p = (h1 < input_height - 1) ? 1 : 0;

    const float h1lambda = h1r - h1;
    const float h0lambda = static_cast<float>(1.) - h1lambda;

    for (int64_t w2 = 0; w2 < output_width; ++w2) {
      const auto w1r = area_pixel_compute_source_index<float>(
          rwidth, w2, align_corners, /*cubic=*/false);

      const int64_t w1 = w1r;
      const int64_t w1p = (w1 < input_width - 1) ? 1 : 0;

      const float w1lambda = w1r - w1;
      const float w0lambda = static_cast<float>(1.) - w1lambda;
      const typename scalar_t::underlying* pos1 = i_p + h1 * input_width + w1;
      typename scalar_t::underlying* pos2 = o_p + h2 * output_width + w2;

      for (int64_t c = 0; c < channels; ++c) {
        float result = h0lambda * (w0lambda * pos1[0] + w1lambda * pos1[w1p]) +
            h1lambda *
                (w0lambda * pos1[h1p * input_width] +
                 w1lambda * pos1[h1p * input_width + w1p]) - input.q_zero_point();
        // requantization
        pos2[0] = at::quantize_val<scalar_t>(
                      output_scale, output.q_zero_point(), result)
                      .val_;
        pos1 += input_width * input_height;
        pos2 += output_width * output_height;
      }
    }
  }
}

} // namespace

Tensor quantized_upsample_bilinear2d_cpu(
    const Tensor& input,
    IntArrayRef output_size,
    double scale_1,
    double scale_2,
    bool align_corners) {
  TORCH_CHECK(
      output_size.size() == 2,
      "It is expected output_size equals to 2, but got size ",
      output_size.size());

  TORCH_CHECK(
      input.numel() != 0 && input.dim() == 4,
      "Non-empty 4D data tensor expected but got a tensor with sizes ",
      input.sizes());

  int64_t output_height = output_size[0];
  int64_t output_width = output_size[1];

  int64_t nbatch = input.size(0);
  int64_t channels = input.size(1);
  int64_t input_height = input.size(2);
  int64_t input_width = input.size(3);
  AT_ASSERT(input_width > 0 && output_width > 0);

  if (input.is_contiguous(c10::MemoryFormat::ChannelsLast)) {
    Tensor output = at::_empty_affine_quantized(
        {nbatch, channels, output_height, output_width},
        input.options(),
        input.q_scale(),
        input.q_zero_point(),
        input.suggest_memory_format());

    qupsample_bilinear2d_nhwc_stub(
        input.device().type(),
        output,
        input,
        input_height,
        input_width,
        output_height,
        output_width,
        nbatch,
        channels,
        align_corners);
    return output;
  } else {
    Tensor output = at::_empty_affine_quantized(
        {nbatch, channels, output_height, output_width},
        input.options(),
        input.q_scale(),
        input.q_zero_point());

    auto input_contig = input.contiguous();
    AT_DISPATCH_QINT_TYPES(
        input_contig.scalar_type(), "upsample_bilinear2d", [&] {
          upsample_bilinear2d_out_frame<scalar_t>(
              output,
              input_contig,
              input_height,
              input_width,
              output_height,
              output_width,
              nbatch,
              channels,
              align_corners);
        });
    return output;
  }
}

DEFINE_DISPATCH(qupsample_bilinear2d_nhwc_stub);
} // namespace native
} // namespace at
