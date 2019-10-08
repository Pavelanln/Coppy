#include <torch/csrc/distributed/rpc/python_rpc_handler.h>

namespace torch {
namespace distributed {
namespace rpc {

namespace {

py::object getFunction(const py::object& module, const char* name) {
  py::object fn = module.attr(name);
  TORCH_CHECK(
      py::isinstance<py::function>(fn),
      "attribute ",
      name,
      " is not a function");
  return fn;
}

} // namespace

PythonRpcHandler::PythonRpcHandler() {
  AutoGIL ag;
  py::object module = py::module::import("torch.distributed.rpc.internal");
  pyRunFunction_ = getFunction(module, "_run_function");
  pyLoadReturnValue_ = getFunction(module, "_load_return_value");
  pySerialize_ = getFunction(module, "serialize");
}

// In default, PythonRpcHandler will call dec_ref() to clean up python objects.
// It is found that PythonRpcHandler will dec_ref() null python objects and
// crashed when program exits in Python 3.5 only (The theory is: the python
// objects are cleaned up before destructing PythonRpcHandler when program
// exits in Python 3.5).
// To avoid PythonRpcHandler destructor to call dec_ref(), explicitly assign
// the py::handle to be none. This will not have memory leak, as when destruting
// PythonRpcHandler singleton when program exits, all memories will be cleaned
// up by OS.
PythonRpcHandler::~PythonRpcHandler() {
  pyRunFunction_ = py::none();
  pyLoadReturnValue_ = py::none();
  pySerialize_ = py::none();
}

PythonRpcHandler& PythonRpcHandler::getInstance() {
  static PythonRpcHandler handler;
  return handler;
}

std::vector<char> PythonRpcHandler::generatePythonUDFResult(
    const std::vector<char>& pickledPayload,
    const std::vector<torch::Tensor>& requestTensorTable,
    std::vector<torch::Tensor>& responseTensorTable) {
  AutoGIL ag;
  auto pargs = py::bytes(pickledPayload.data(), pickledPayload.size());
  TORCH_CHECK(!pyRunFunction_.is_none(), "pyRunFunction_ is none");
  py::tuple pres = pySerialize_(pyRunFunction_(pargs, requestTensorTable));
  const auto& presStr = pres[0].cast<std::string>();
  responseTensorTable = pres[1].cast<std::vector<torch::Tensor>>();
  std::vector<char> payload(presStr.begin(), presStr.end());
  return payload;
}

py::object PythonRpcHandler::loadPythonUDFResult(
    const std::vector<char>& pickledPayload,
    const std::vector<torch::Tensor>& tensorTable) {
  AutoGIL ag;
  auto pargs = py::bytes(pickledPayload.data(), pickledPayload.size());
  TORCH_CHECK(!pyLoadReturnValue_.is_none(), "pyLoadReturnValue_ is none");
  return pyLoadReturnValue_(pargs, tensorTable);
}

py::object PythonRpcHandler::runPythonUDF(
    const SerializedPyObj& serializedObj) {
  AutoGIL ag;
  return pyRunFunction_(
      py::bytes(serializedObj.payload_), serializedObj.tensors_);
}

SerializedPyObj PythonRpcHandler::serialize(const py::object& obj) {
  AutoGIL ag;
  py::tuple t = pySerialize_(obj);
  return SerializedPyObj(
      t[0].cast<std::string>(), t[1].cast<std::vector<torch::Tensor>>());
}

py::object PythonRpcHandler::deserialize(const SerializedPyObj& serializedObj) {
  AutoGIL ag;
  return pyLoadReturnValue_(
      py::bytes(serializedObj.payload_), serializedObj.tensors_);
}

} // namespace rpc
} // namespace distributed
} // namespace torch
