#pragma once

/**
 * GENERATED CODE - DO NOT EDIT DIRECTLY
 * This file is generated by gen_diagnostics.py.
 * See tools/onnx/gen_diagnostics.py for more information.
 *
 * Diagnostic rules for PyTorch ONNX export.
 */

namespace torch::onnx::diagnostics {

enum class Rule : uint32_t {
  /**
   * @brief Node is missing ONNX shape inference.
   */
  kNodeMissingOnnxShapeInference,

  /**
   * @brief Missing symbolic function for custom PyTorch operator, cannot
   * translate node to ONNX.
   */
  kMissingCustomSymbolicFunction,

  /**
   * @brief Missing symbolic function for standard PyTorch operator, cannot
   * translate node to ONNX.
   */
  kMissingStandardSymbolicFunction,

  /**
   * @brief Operator is supported in newer opset version.
   */
  kOperatorSupportedInNewerOpsetVersion,

  /**
   * @brief Transforms graph from FX IR to ONNX IR.
   */
  kFxGraphToOnnx,

  /**
   * @brief Transforms an FX node to an ONNX node.
   */
  kFxNodeToOnnx,

  /**
   * @brief FX graph transformation during ONNX export before converting from FX
   * IR to ONNX IR.
   */
  kFxPass,

  /**
   * @brief Cannot find symbolic function to convert the "call_function" FX node
   * to ONNX.
   */
  kNoSymbolicFunctionForCallFunction,

  /**
   * @brief Result from FX graph analysis to reveal unsupported FX nodes.
   */
  kUnsupportedFxNodeAnalysis,

  /**
   * @brief Report any op level validation failure in warnings.
   */
  kOpLevelDebugging,

  /**
   * @brief Find the OnnxFunction that matches the input/attribute dtypes by
   * comparing them with their opschemas.
   */
  kFindOpschemaMatchedSymbolicFunction,

  /**
   * @brief Determine if type promotion is required for the FX node. Insert cast
   * nodes if needed.
   */
  kFxNodeInsertTypePromotion,

  /**
   * @brief Find the list of OnnxFunction of the PyTorch operator in onnx
   * registry.
   */
  kFindOperatorOverloadsInOnnxRegistry,
};

static constexpr const char* const kPyRuleNames[] = {
    "node_missing_onnx_shape_inference",
    "missing_custom_symbolic_function",
    "missing_standard_symbolic_function",
    "operator_supported_in_newer_opset_version",
    "fx_graph_to_onnx",
    "fx_node_to_onnx",
    "fx_pass",
    "no_symbolic_function_for_call_function",
    "unsupported_fx_node_analysis",
    "op_level_debugging",
    "find_opschema_matched_symbolic_function",
    "fx_node_insert_type_promotion",
    "find_operator_overloads_in_onnx_registry",
};

} // namespace torch::onnx::diagnostics
