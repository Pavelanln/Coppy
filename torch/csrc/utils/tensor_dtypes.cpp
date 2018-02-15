#include <Python.h>
#include "tensor_dtypes.h"
#include "torch/csrc/Dtype.h"
#include "torch/csrc/DynamicTypes.h"
#include "torch/csrc/Exceptions.h"
#include "torch/csrc/autograd/generated/VariableType.h"
#include "torch/csrc/utils/tensor_types.h"

namespace torch { namespace utils {

static std::pair<std::string, std::string> getDtypeNames(at::ScalarType scalarType) {
  switch(scalarType) {
    case at::ScalarType::Byte:
      // no "byte" because byte is signed in numpy and we overload
      // byte to mean bool often
      return std::make_pair("uint8", "");
    case at::ScalarType::Char:
      // no "char" because it is not consistently signed or unsigned; we want
      // to move to int8
      return std::make_pair("int8", "");
    case at::ScalarType::Double:
      return std::make_pair("float64", "double");
    case at::ScalarType::Float:
      return std::make_pair("float32", "float");
    case at::ScalarType::Int:
      return std::make_pair("int32", "int");
    case at::ScalarType::Long:
      return std::make_pair("int64", "long");
    case at::ScalarType::Short:
      return std::make_pair("int16", "short");
    case at::ScalarType::Half:
      return std::make_pair("float16", "half");
    default:
      throw std::runtime_error("Unimplemented scalar type");
  }
}

void initializeDtypes() {
  auto torch_module = THPObjectPtr(PyImport_ImportModule("torch"));
  auto cuda_module = THPObjectPtr(PyImport_ImportModule("torch.cuda"));
  auto sparse_module = THPObjectPtr(PyImport_ImportModule("torch.sparse"));
  auto cuda_sparse_module = THPObjectPtr(PyImport_ImportModule("torch.cuda.sparse"));
  auto& context = at::globalContext();
  for (auto type_pair : torch::utils::all_declared_types()) {
    at::Backend backend;
    at::ScalarType scalarType;
    std::tie(backend, scalarType) = type_pair;
    std::string primary_name, legacy_name;
    std::tie(primary_name, legacy_name) = getDtypeNames(scalarType);
    PyObject *module = nullptr;
    bool is_cuda, is_sparse;
    switch (backend) {
      case at::kCPU: {
        module = torch_module.get();
        is_cuda = false;
        is_sparse = false;
        break;
      }
      case at::kCUDA: {
        module = cuda_module.get();
        is_cuda = true;
        is_sparse = false;
        break;
      }
      case at::kSparseCPU: {
        module = sparse_module.get();
        is_cuda = false;
        is_sparse = true;
        break;
      }
      case at::kSparseCUDA: {
        module = cuda_sparse_module.get();
        is_cuda = true;
        is_sparse = true;
        break;
      }
      default: throw std::runtime_error("Unimplemented backend");
    }
    auto baseType = context.type_registry[static_cast<int>(backend)][static_cast<int>(scalarType)].get();
    auto type = baseType ? torch::autograd::VariableType::getType(*baseType) : nullptr;
    std::string name = std::string(PyModule_GetName(module)) + '.' + primary_name;
    THPDtype *dtype = (THPDtype*)THPDtype_New(type, name, is_cuda, is_sparse);
    if (type) {
      torch::registerDtypeObject(dtype, *type);
    }
    PyModule_AddObject(module, primary_name.c_str(), (PyObject*)dtype);
    if (legacy_name != "") {
      PyModule_AddObject(module, legacy_name.c_str(), (PyObject*)dtype);
    }
  }
}

}} // namespace torch::utils
