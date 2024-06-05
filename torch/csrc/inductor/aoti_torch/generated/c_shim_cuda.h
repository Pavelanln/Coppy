

// WARNING: THIS FILE IS AUTOGENERATED BY torchgen. DO NOT MODIFY BY HAND.
// See https://github.com/pytorch/pytorch/blob/7e86a7c0155295539996e0cf422883571126073e/torchgen/gen.py#L2424-L2436 for details

#pragma once

#include <torch/csrc/inductor/aoti_torch/c/shim.h>

#ifdef __cplusplus
extern "C" {
#endif

AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__adaptive_avg_pool2d(AtenTensorHandle self, const int64_t* output_size, int64_t output_size_len_, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__adaptive_avg_pool2d_backward(AtenTensorHandle grad_output, AtenTensorHandle self, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__adaptive_avg_pool3d(AtenTensorHandle self, const int64_t* output_size, int64_t output_size_len_, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__adaptive_avg_pool3d_backward(AtenTensorHandle grad_output, AtenTensorHandle self, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__addmm_activation(AtenTensorHandle self, AtenTensorHandle mat1, AtenTensorHandle mat2, double beta, double alpha, int32_t use_gelu, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__cdist_backward(AtenTensorHandle grad, AtenTensorHandle x1, AtenTensorHandle x2, double p, AtenTensorHandle cdist, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__cdist_forward(AtenTensorHandle x1, AtenTensorHandle x2, double p, int64_t* compute_mode, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__cudnn_rnn(AtenTensorHandle input, const AtenTensorHandle* weight, int64_t weight_len_, int64_t weight_stride0, AtenTensorHandle* weight_buf, AtenTensorHandle hx, AtenTensorHandle* cx, int64_t mode, int64_t hidden_size, int64_t proj_size, int64_t num_layers, int32_t batch_first, double dropout, int32_t train, int32_t bidirectional, const int64_t* batch_sizes, int64_t batch_sizes_len_, AtenTensorHandle* dropout_state, AtenTensorHandle* ret0, AtenTensorHandle* ret1, AtenTensorHandle* ret2, AtenTensorHandle* ret3, AtenTensorHandle* ret4);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__efficient_attention_backward(AtenTensorHandle grad_out_, AtenTensorHandle query, AtenTensorHandle key, AtenTensorHandle value, AtenTensorHandle* bias, AtenTensorHandle out, AtenTensorHandle* cu_seqlens_q, AtenTensorHandle* cu_seqlens_k, int64_t max_seqlen_q, int64_t max_seqlen_k, AtenTensorHandle logsumexp, double dropout_p, AtenTensorHandle philox_seed, AtenTensorHandle philox_offset, int64_t custom_mask_type, int32_t bias_requires_grad, double* scale, int64_t* num_splits_key, int64_t* window_size, int32_t shared_storage_dqdkdv, AtenTensorHandle* ret0, AtenTensorHandle* ret1, AtenTensorHandle* ret2, AtenTensorHandle* ret3);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__efficient_attention_forward(AtenTensorHandle query, AtenTensorHandle key, AtenTensorHandle value, AtenTensorHandle* bias, AtenTensorHandle* cu_seqlens_q, AtenTensorHandle* cu_seqlens_k, int64_t* max_seqlen_q, int64_t* max_seqlen_k, double dropout_p, int64_t custom_mask_type, int32_t compute_log_sumexp, double* scale, AtenTensorHandle* seqlen_k, int64_t* window_size, AtenTensorHandle* ret0, AtenTensorHandle* ret1, AtenTensorHandle* ret2, AtenTensorHandle* ret3, int64_t* ret4, int64_t* ret5);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__efficientzerotensor(const int64_t* size, int64_t size_len_, int32_t* dtype, int32_t* layout, int32_t* device, int32_t device_index_, int32_t* pin_memory, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__embedding_bag(AtenTensorHandle weight, AtenTensorHandle indices, AtenTensorHandle offsets, int32_t scale_grad_by_freq, int64_t mode, int32_t sparse, AtenTensorHandle* per_sample_weights, int32_t include_last_offset, int64_t padding_idx, AtenTensorHandle* ret0, AtenTensorHandle* ret1, AtenTensorHandle* ret2, AtenTensorHandle* ret3);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__embedding_bag_dense_backward(AtenTensorHandle grad, AtenTensorHandle indices, AtenTensorHandle offset2bag, AtenTensorHandle bag_size, AtenTensorHandle maximum_indices, int64_t num_weights, int32_t scale_grad_by_freq, int64_t mode, AtenTensorHandle* per_sample_weights, int64_t padding_idx, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__embedding_bag_forward_only(AtenTensorHandle weight, AtenTensorHandle indices, AtenTensorHandle offsets, int32_t scale_grad_by_freq, int64_t mode, int32_t sparse, AtenTensorHandle* per_sample_weights, int32_t include_last_offset, int64_t padding_idx, AtenTensorHandle* ret0, AtenTensorHandle* ret1, AtenTensorHandle* ret2, AtenTensorHandle* ret3);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__embedding_bag_per_sample_weights_backward(AtenTensorHandle grad, AtenTensorHandle weight, AtenTensorHandle indices, AtenTensorHandle offsets, AtenTensorHandle offset2bag, int64_t mode, int64_t padding_idx, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__fft_c2c(AtenTensorHandle self, const int64_t* dim, int64_t dim_len_, int64_t normalization, int32_t forward, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__fft_r2c(AtenTensorHandle self, const int64_t* dim, int64_t dim_len_, int64_t normalization, int32_t onesided, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__flash_attention_backward(AtenTensorHandle grad_out, AtenTensorHandle query, AtenTensorHandle key, AtenTensorHandle value, AtenTensorHandle out, AtenTensorHandle logsumexp, AtenTensorHandle cum_seq_q, AtenTensorHandle cum_seq_k, int64_t max_q, int64_t max_k, double dropout_p, int32_t is_causal, AtenTensorHandle philox_seed, AtenTensorHandle philox_offset, double* scale, int64_t* window_size_left, int64_t* window_size_right, AtenTensorHandle* ret0, AtenTensorHandle* ret1, AtenTensorHandle* ret2);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__flash_attention_forward(AtenTensorHandle query, AtenTensorHandle key, AtenTensorHandle value, AtenTensorHandle* cum_seq_q, AtenTensorHandle* cum_seq_k, int64_t max_q, int64_t max_k, double dropout_p, int32_t is_causal, int32_t return_debug_mask, double* scale, int64_t* window_size_left, int64_t* window_size_right, AtenTensorHandle* seqused_k, AtenTensorHandle* alibi_slopes, AtenTensorHandle* ret0, AtenTensorHandle* ret1, AtenTensorHandle* ret2, AtenTensorHandle* ret3, AtenTensorHandle* ret4);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__fused_moving_avg_obs_fq_helper(AtenTensorHandle self, AtenTensorHandle observer_on, AtenTensorHandle fake_quant_on, AtenTensorHandle running_min, AtenTensorHandle running_max, AtenTensorHandle scale, AtenTensorHandle zero_point, double averaging_const, int64_t quant_min, int64_t quant_max, int64_t ch_axis, int32_t per_row_fake_quant, int32_t symmetric_quant, AtenTensorHandle* ret0, AtenTensorHandle* ret1);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__fused_moving_avg_obs_fq_helper_functional(AtenTensorHandle self, AtenTensorHandle observer_on, AtenTensorHandle fake_quant_on, AtenTensorHandle running_min, AtenTensorHandle running_max, AtenTensorHandle scale, AtenTensorHandle zero_point, double averaging_const, int64_t quant_min, int64_t quant_max, int64_t ch_axis, int32_t per_row_fake_quant, int32_t symmetric_quant, AtenTensorHandle* ret0, AtenTensorHandle* ret1, AtenTensorHandle* ret2, AtenTensorHandle* ret3, AtenTensorHandle* ret4, AtenTensorHandle* ret5);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__pdist_backward(AtenTensorHandle grad, AtenTensorHandle self, double p, AtenTensorHandle pdist, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__pdist_forward(AtenTensorHandle self, double p, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__scaled_dot_product_efficient_attention(AtenTensorHandle query, AtenTensorHandle key, AtenTensorHandle value, AtenTensorHandle* attn_bias, int32_t compute_log_sumexp, double dropout_p, int32_t is_causal, double* scale, AtenTensorHandle* ret0, AtenTensorHandle* ret1, AtenTensorHandle* ret2, AtenTensorHandle* ret3);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__scaled_dot_product_efficient_attention_backward(AtenTensorHandle grad_out_, AtenTensorHandle query, AtenTensorHandle key, AtenTensorHandle value, AtenTensorHandle attn_bias, AtenTensorHandle out, AtenTensorHandle logsumexp, AtenTensorHandle philox_seed, AtenTensorHandle philox_offset, double dropout_p, const int32_t* grad_input_mask, int64_t grad_input_mask_len_, int32_t is_causal, double* scale, AtenTensorHandle* ret0, AtenTensorHandle* ret1, AtenTensorHandle* ret2, AtenTensorHandle* ret3);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__scaled_dot_product_flash_attention(AtenTensorHandle query, AtenTensorHandle key, AtenTensorHandle value, double dropout_p, int32_t is_causal, int32_t return_debug_mask, double* scale, AtenTensorHandle* ret0, AtenTensorHandle* ret1, AtenTensorHandle* ret2, AtenTensorHandle* ret3, int64_t* ret4, int64_t* ret5, AtenTensorHandle* ret6, AtenTensorHandle* ret7, AtenTensorHandle* ret8);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__scaled_dot_product_flash_attention_backward(AtenTensorHandle grad_out, AtenTensorHandle query, AtenTensorHandle key, AtenTensorHandle value, AtenTensorHandle out, AtenTensorHandle logsumexp, AtenTensorHandle cum_seq_q, AtenTensorHandle cum_seq_k, int64_t max_q, int64_t max_k, double dropout_p, int32_t is_causal, AtenTensorHandle philox_seed, AtenTensorHandle philox_offset, double* scale, AtenTensorHandle* ret0, AtenTensorHandle* ret1, AtenTensorHandle* ret2);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__scaled_mm(AtenTensorHandle self, AtenTensorHandle mat2, AtenTensorHandle* bias, int32_t* out_dtype, AtenTensorHandle* scale_a, AtenTensorHandle* scale_b, AtenTensorHandle* scale_result, int32_t use_fast_accum, AtenTensorHandle* ret0, AtenTensorHandle* ret1);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__segment_reduce_backward(AtenTensorHandle grad, AtenTensorHandle output, AtenTensorHandle data, const char* reduce, AtenTensorHandle* lengths, AtenTensorHandle* offsets, int64_t axis, double* initial, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__thnn_fused_lstm_cell(AtenTensorHandle input_gates, AtenTensorHandle hidden_gates, AtenTensorHandle cx, AtenTensorHandle* input_bias, AtenTensorHandle* hidden_bias, AtenTensorHandle* ret0, AtenTensorHandle* ret1, AtenTensorHandle* ret2);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__to_sparse(AtenTensorHandle self, int32_t* layout, const int64_t** blocksize, int64_t blocksize_len_, int64_t* dense_dim, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda__trilinear(AtenTensorHandle i1, AtenTensorHandle i2, AtenTensorHandle i3, const int64_t* expand1, int64_t expand1_len_, const int64_t* expand2, int64_t expand2_len_, const int64_t* expand3, int64_t expand3_len_, const int64_t* sumdim, int64_t sumdim_len_, int64_t unroll_dim, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_adaptive_max_pool2d(AtenTensorHandle self, const int64_t* output_size, int64_t output_size_len_, AtenTensorHandle* ret0, AtenTensorHandle* ret1);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_adaptive_max_pool2d_backward(AtenTensorHandle grad_output, AtenTensorHandle self, AtenTensorHandle indices, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_adaptive_max_pool3d(AtenTensorHandle self, const int64_t* output_size, int64_t output_size_len_, AtenTensorHandle* ret0, AtenTensorHandle* ret1);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_adaptive_max_pool3d_backward(AtenTensorHandle grad_output, AtenTensorHandle self, AtenTensorHandle indices, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_addbmm(AtenTensorHandle self, AtenTensorHandle batch1, AtenTensorHandle batch2, double beta, double alpha, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_addmm_out(AtenTensorHandle out, AtenTensorHandle self, AtenTensorHandle mat1, AtenTensorHandle mat2, double beta, double alpha);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_addmv(AtenTensorHandle self, AtenTensorHandle mat, AtenTensorHandle vec, double beta, double alpha, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_angle(AtenTensorHandle self, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_avg_pool2d(AtenTensorHandle self, const int64_t* kernel_size, int64_t kernel_size_len_, const int64_t* stride, int64_t stride_len_, const int64_t* padding, int64_t padding_len_, int32_t ceil_mode, int32_t count_include_pad, int64_t* divisor_override, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_avg_pool2d_backward(AtenTensorHandle grad_output, AtenTensorHandle self, const int64_t* kernel_size, int64_t kernel_size_len_, const int64_t* stride, int64_t stride_len_, const int64_t* padding, int64_t padding_len_, int32_t ceil_mode, int32_t count_include_pad, int64_t* divisor_override, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_avg_pool3d(AtenTensorHandle self, const int64_t* kernel_size, int64_t kernel_size_len_, const int64_t* stride, int64_t stride_len_, const int64_t* padding, int64_t padding_len_, int32_t ceil_mode, int32_t count_include_pad, int64_t* divisor_override, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_avg_pool3d_backward(AtenTensorHandle grad_output, AtenTensorHandle self, const int64_t* kernel_size, int64_t kernel_size_len_, const int64_t* stride, int64_t stride_len_, const int64_t* padding, int64_t padding_len_, int32_t ceil_mode, int32_t count_include_pad, int64_t* divisor_override, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_bernoulli__Tensor(AtenTensorHandle self, AtenTensorHandle p, AtenGeneratorHandle* generator);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_bernoulli__float(AtenTensorHandle self, double p, AtenGeneratorHandle* generator);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_bmm_out(AtenTensorHandle out, AtenTensorHandle self, AtenTensorHandle mat2);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_bucketize_Tensor(AtenTensorHandle self, AtenTensorHandle boundaries, int32_t out_int32, int32_t right, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_cat(const AtenTensorHandle* tensors, int64_t tensors_len_, int64_t dim, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_cholesky_inverse(AtenTensorHandle self, int32_t upper, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_cholesky_solve(AtenTensorHandle self, AtenTensorHandle input2, int32_t upper, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_convolution(AtenTensorHandle input, AtenTensorHandle weight, AtenTensorHandle* bias, const int64_t* stride, int64_t stride_len_, const int64_t* padding, int64_t padding_len_, const int64_t* dilation, int64_t dilation_len_, int32_t transposed, const int64_t* output_padding, int64_t output_padding_len_, int64_t groups, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_convolution_backward(AtenTensorHandle grad_output, AtenTensorHandle input, AtenTensorHandle weight, const int64_t** bias_sizes, int64_t bias_sizes_len_, const int64_t* stride, int64_t stride_len_, const int64_t* padding, int64_t padding_len_, const int64_t* dilation, int64_t dilation_len_, int32_t transposed, const int64_t* output_padding, int64_t output_padding_len_, int64_t groups, const int32_t* output_mask, int64_t output_mask_len_, AtenTensorHandle* ret0, AtenTensorHandle* ret1, AtenTensorHandle* ret2);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_cummax(AtenTensorHandle self, int64_t dim, AtenTensorHandle* ret0, AtenTensorHandle* ret1);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_cummin(AtenTensorHandle self, int64_t dim, AtenTensorHandle* ret0, AtenTensorHandle* ret1);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_cumprod(AtenTensorHandle self, int64_t dim, int32_t* dtype, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_cumsum(AtenTensorHandle self, int64_t dim, int32_t* dtype, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_exponential(AtenTensorHandle self, double lambd, AtenGeneratorHandle* generator, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_fractional_max_pool2d(AtenTensorHandle self, const int64_t* kernel_size, int64_t kernel_size_len_, const int64_t* output_size, int64_t output_size_len_, AtenTensorHandle random_samples, AtenTensorHandle* ret0, AtenTensorHandle* ret1);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_fractional_max_pool2d_backward(AtenTensorHandle grad_output, AtenTensorHandle self, const int64_t* kernel_size, int64_t kernel_size_len_, const int64_t* output_size, int64_t output_size_len_, AtenTensorHandle indices, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_fractional_max_pool3d(AtenTensorHandle self, const int64_t* kernel_size, int64_t kernel_size_len_, const int64_t* output_size, int64_t output_size_len_, AtenTensorHandle random_samples, AtenTensorHandle* ret0, AtenTensorHandle* ret1);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_fractional_max_pool3d_backward(AtenTensorHandle grad_output, AtenTensorHandle self, const int64_t* kernel_size, int64_t kernel_size_len_, const int64_t* output_size, int64_t output_size_len_, AtenTensorHandle indices, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_gcd(AtenTensorHandle self, AtenTensorHandle other, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_geqrf(AtenTensorHandle self, AtenTensorHandle* ret0, AtenTensorHandle* ret1);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_grid_sampler_2d_backward(AtenTensorHandle grad_output, AtenTensorHandle input, AtenTensorHandle grid, int64_t interpolation_mode, int64_t padding_mode, int32_t align_corners, const int32_t* output_mask, int64_t output_mask_len_, AtenTensorHandle* ret0, AtenTensorHandle* ret1);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_histc(AtenTensorHandle self, int64_t bins, double min, double max, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_index_Tensor(AtenTensorHandle self, const AtenTensorHandle** indices, int64_t indices_len_, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_index_put(AtenTensorHandle self, const AtenTensorHandle** indices, int64_t indices_len_, AtenTensorHandle values, int32_t accumulate, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_index_reduce(AtenTensorHandle self, int64_t dim, AtenTensorHandle index, AtenTensorHandle source, const char* reduce, int32_t include_self, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_kthvalue(AtenTensorHandle self, int64_t k, int64_t dim, int32_t keepdim, AtenTensorHandle* ret0, AtenTensorHandle* ret1);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_logcumsumexp(AtenTensorHandle self, int64_t dim, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_lu_unpack(AtenTensorHandle LU_data, AtenTensorHandle LU_pivots, int32_t unpack_data, int32_t unpack_pivots, AtenTensorHandle* ret0, AtenTensorHandle* ret1, AtenTensorHandle* ret2);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_masked_scatter(AtenTensorHandle self, AtenTensorHandle mask, AtenTensorHandle source, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_masked_scatter_backward(AtenTensorHandle grad_output, AtenTensorHandle mask, const int64_t* sizes, int64_t sizes_len_, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_max_pool2d_with_indices(AtenTensorHandle self, const int64_t* kernel_size, int64_t kernel_size_len_, const int64_t* stride, int64_t stride_len_, const int64_t* padding, int64_t padding_len_, const int64_t* dilation, int64_t dilation_len_, int32_t ceil_mode, AtenTensorHandle* ret0, AtenTensorHandle* ret1);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_max_pool2d_with_indices_backward(AtenTensorHandle grad_output, AtenTensorHandle self, const int64_t* kernel_size, int64_t kernel_size_len_, const int64_t* stride, int64_t stride_len_, const int64_t* padding, int64_t padding_len_, const int64_t* dilation, int64_t dilation_len_, int32_t ceil_mode, AtenTensorHandle indices, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_max_pool3d_with_indices(AtenTensorHandle self, const int64_t* kernel_size, int64_t kernel_size_len_, const int64_t* stride, int64_t stride_len_, const int64_t* padding, int64_t padding_len_, const int64_t* dilation, int64_t dilation_len_, int32_t ceil_mode, AtenTensorHandle* ret0, AtenTensorHandle* ret1);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_max_pool3d_with_indices_backward(AtenTensorHandle grad_output, AtenTensorHandle self, const int64_t* kernel_size, int64_t kernel_size_len_, const int64_t* stride, int64_t stride_len_, const int64_t* padding, int64_t padding_len_, const int64_t* dilation, int64_t dilation_len_, int32_t ceil_mode, AtenTensorHandle indices, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_max_unpool2d(AtenTensorHandle self, AtenTensorHandle indices, const int64_t* output_size, int64_t output_size_len_, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_max_unpool3d(AtenTensorHandle self, AtenTensorHandle indices, const int64_t* output_size, int64_t output_size_len_, const int64_t* stride, int64_t stride_len_, const int64_t* padding, int64_t padding_len_, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_median(AtenTensorHandle self, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_mm_out(AtenTensorHandle out, AtenTensorHandle self, AtenTensorHandle mat2);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_mode(AtenTensorHandle self, int64_t dim, int32_t keepdim, AtenTensorHandle* ret0, AtenTensorHandle* ret1);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_mul_Scalar(AtenTensorHandle self, double other, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_mul_Tensor(AtenTensorHandle self, AtenTensorHandle other, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_nanmedian(AtenTensorHandle self, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_native_dropout(AtenTensorHandle input, double p, int32_t* train, AtenTensorHandle* ret0, AtenTensorHandle* ret1);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_nonzero(AtenTensorHandle self, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_normal_functional(AtenTensorHandle self, double mean, double std, AtenGeneratorHandle* generator, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_ormqr(AtenTensorHandle self, AtenTensorHandle input2, AtenTensorHandle input3, int32_t left, int32_t transpose, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_pow_Scalar(double self, AtenTensorHandle exponent, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_pow_Tensor_Scalar(AtenTensorHandle self, double exponent, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_pow_Tensor_Tensor(AtenTensorHandle self, AtenTensorHandle exponent, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_rand(const int64_t* size, int64_t size_len_, int32_t* dtype, int32_t* layout, int32_t* device, int32_t device_index_, int32_t* pin_memory, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_rand_generator(const int64_t* size, int64_t size_len_, AtenGeneratorHandle* generator, int32_t* dtype, int32_t* layout, int32_t* device, int32_t device_index_, int32_t* pin_memory, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_randint(int64_t high, const int64_t* size, int64_t size_len_, int32_t* dtype, int32_t* layout, int32_t* device, int32_t device_index_, int32_t* pin_memory, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_randint_generator(int64_t high, const int64_t* size, int64_t size_len_, AtenGeneratorHandle* generator, int32_t* dtype, int32_t* layout, int32_t* device, int32_t device_index_, int32_t* pin_memory, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_randint_low(int64_t low, int64_t high, const int64_t* size, int64_t size_len_, int32_t* dtype, int32_t* layout, int32_t* device, int32_t device_index_, int32_t* pin_memory, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_randint_low_out(AtenTensorHandle out, int64_t low, int64_t high, const int64_t* size, int64_t size_len_);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_randn(const int64_t* size, int64_t size_len_, int32_t* dtype, int32_t* layout, int32_t* device, int32_t device_index_, int32_t* pin_memory, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_randn_generator(const int64_t* size, int64_t size_len_, AtenGeneratorHandle* generator, int32_t* dtype, int32_t* layout, int32_t* device, int32_t device_index_, int32_t* pin_memory, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_randperm(int64_t n, int32_t* dtype, int32_t* layout, int32_t* device, int32_t device_index_, int32_t* pin_memory, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_repeat_interleave_Tensor(AtenTensorHandle repeats, int64_t* output_size, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_replication_pad1d_backward(AtenTensorHandle grad_output, AtenTensorHandle self, const int64_t* padding, int64_t padding_len_, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_replication_pad2d_backward(AtenTensorHandle grad_output, AtenTensorHandle self, const int64_t* padding, int64_t padding_len_, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_reshape(AtenTensorHandle self, const int64_t* shape, int64_t shape_len_, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_resize_(AtenTensorHandle self, const int64_t* size, int64_t size_len_, int32_t* memory_format);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_resize_as_(AtenTensorHandle self, AtenTensorHandle the_template, int32_t* memory_format);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_scatter_src_out(AtenTensorHandle out, AtenTensorHandle self, int64_t dim, AtenTensorHandle index, AtenTensorHandle src);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_scatter_value_out(AtenTensorHandle out, AtenTensorHandle self, int64_t dim, AtenTensorHandle index, double value);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_scatter_reduce_two_out(AtenTensorHandle out, AtenTensorHandle self, int64_t dim, AtenTensorHandle index, AtenTensorHandle src, const char* reduce, int32_t include_self);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_segment_reduce(AtenTensorHandle data, const char* reduce, AtenTensorHandle* lengths, AtenTensorHandle* indices, AtenTensorHandle* offsets, int64_t axis, int32_t unsafe, double* initial, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_slice_Tensor(AtenTensorHandle self, int64_t dim, int64_t* start, int64_t* end, int64_t step, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_soft_margin_loss_backward(AtenTensorHandle grad_output, AtenTensorHandle self, AtenTensorHandle target, int64_t reduction, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_sort(AtenTensorHandle self, int64_t dim, int32_t descending, AtenTensorHandle* ret0, AtenTensorHandle* ret1);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_sort_stable(AtenTensorHandle self, int32_t* stable, int64_t dim, int32_t descending, AtenTensorHandle* ret0, AtenTensorHandle* ret1);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_to_sparse(AtenTensorHandle self, int32_t* layout, const int64_t** blocksize, int64_t blocksize_len_, int64_t* dense_dim, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_topk(AtenTensorHandle self, int64_t k, int64_t dim, int32_t largest, int32_t sorted, AtenTensorHandle* ret0, AtenTensorHandle* ret1);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_triangular_solve(AtenTensorHandle self, AtenTensorHandle A, int32_t upper, int32_t transpose, int32_t unitriangular, AtenTensorHandle* ret0, AtenTensorHandle* ret1);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_uniform(AtenTensorHandle self, double from, double to, AtenGeneratorHandle* generator, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_upsample_bicubic2d_backward(AtenTensorHandle grad_output, const int64_t* output_size, int64_t output_size_len_, const int64_t* input_size, int64_t input_size_len_, int32_t align_corners, double* scales_h, double* scales_w, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_upsample_linear1d_backward(AtenTensorHandle grad_output, const int64_t* output_size, int64_t output_size_len_, const int64_t* input_size, int64_t input_size_len_, int32_t align_corners, double* scales, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_upsample_trilinear3d_backward(AtenTensorHandle grad_output, const int64_t* output_size, int64_t output_size_len_, const int64_t* input_size, int64_t input_size_len_, int32_t align_corners, double* scales_d, double* scales_h, double* scales_w, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_view_dtype(AtenTensorHandle self, int32_t dtype, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_view_as_complex(AtenTensorHandle self, AtenTensorHandle* ret0);
AOTI_TORCH_EXPORT AOTITorchError aoti_torch_cuda_view_as_real(AtenTensorHandle self, AtenTensorHandle* ret0);

#ifdef __cplusplus
} // extern "C"
#endif
