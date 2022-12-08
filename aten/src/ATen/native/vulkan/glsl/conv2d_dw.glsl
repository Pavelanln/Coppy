#version 450 core
#define PRECISION $precision
#define FORMAT $format

/*
 * TILE_SIZE = (1, 1, 1)
 * WEIGHT_STORAGE = TEXTURE_2D
 * BIAS_STORAGE = TEXTURE_2D
 * Note that for DW kernel IC = 1 so the weight layout is really OC4, H, W, 4oc
 */

layout(std430) buffer;

/*
 * Output Image
 */
layout(set = 0, binding = 0, FORMAT) uniform PRECISION restrict writeonly image3D uOut;

/*
 * Input Textures
 */
layout(set = 0, binding = 1) uniform PRECISION sampler3D uInput;
layout(set = 0, binding = 2) uniform PRECISION sampler2D uKernel;
layout(set = 0, binding = 3) uniform PRECISION sampler2D uBias;

/*
 * Params Buffer
 */
layout(set = 0, binding = 4) uniform PRECISION restrict Block {
  // extents of the output texture
  ivec4 out_extents;
  // extents of the input texture
  ivec4 in_extents;
  // size of the overlay region of the kernel
  ivec4 overlay_region;
  // width and height of the kernel
  ivec2 kernel_size;
  // convolution parameters
  ivec2 stride;
  ivec2 padding;
  ivec2 dilate;
  vec2 clamp_thresh;
}
uBlock;

/*
 * Local Work Group
 */
layout(local_size_x_id = 0, local_size_y_id = 1, local_size_z_id = 2) in;

/*
 * Computes depthwise convolution. Each shader invocation calculates the output
 * of a single output location.
 */
void main() {
  const ivec3 pos = ivec3(gl_GlobalInvocationID);

  // Return if this global position is outside output texture bounds
  if (any(greaterThanEqual(pos, uBlock.out_extents.xyz))) {
    return;
  }

  // Compute the index of the top-left element of the overlay region. Note that
  // negative indices can be produced indicating that the top-left element is in
  // a region added by padding.
  const ivec2 ipos = pos.xy * uBlock.stride - uBlock.padding;

  // Compute the start and end of the input indices to load. Padding is assumed
  // to be constant 0 padding, so any reads from the padding region is skipped.
  const ivec2 start = ipos;
  const ivec2 end = ipos + uBlock.overlay_region.xy;

  vec4 sum = texelFetch(uBias, ivec2(pos.z, 0), 0);
  const int dil_y = uBlock.dilate.y;
  const int dil_x = uBlock.dilate.x;
  int k_ind = 0;
  for (int y = start.y; y < end.y; y += dil_y) {
    for (int x = start.x; x < end.x; x += dil_x) {
      // The weight kernel was rearranged so that every NxN filter was flattened
      // so that it fits on one row. Each filter was then stacked on top of each
      // other vertically.
      const vec4 k_tex = texelFetch(uKernel, ivec2(k_ind, pos.z), 0);
      const vec4 i_tex = texelFetch(uInput, ivec3(x, y, pos.z), 0);
      sum = fma(i_tex, k_tex, sum);
      k_ind++;
    }
  }

  imageStore(
      uOut, pos, clamp(sum, uBlock.clamp_thresh.x, uBlock.clamp_thresh.y));
}
