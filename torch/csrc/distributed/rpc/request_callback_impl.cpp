#include <torch/csrc/distributed/rpc/request_callback_impl.h>

#include <c10/util/C++17.h>
#include <torch/csrc/autograd/profiler.h>
#include <torch/csrc/distributed/autograd/context/container.h>
#include <torch/csrc/distributed/autograd/context/context.h>
#include <torch/csrc/distributed/autograd/engine/dist_engine.h>
#include <torch/csrc/distributed/autograd/rpc_messages/cleanup_autograd_context_req.h>
#include <torch/csrc/distributed/autograd/rpc_messages/cleanup_autograd_context_resp.h>
#include <torch/csrc/distributed/autograd/rpc_messages/propagate_gradients_req.h>
#include <torch/csrc/distributed/autograd/rpc_messages/propagate_gradients_resp.h>
#include <torch/csrc/distributed/autograd/rpc_messages/rpc_with_autograd.h>
#include <torch/csrc/distributed/autograd/rpc_messages/rpc_with_profiling_req.h>
#include <torch/csrc/distributed/autograd/rpc_messages/rpc_with_profiling_resp.h>
#include <torch/csrc/distributed/autograd/rpc_messages/rref_backward_req.h>
#include <torch/csrc/distributed/autograd/rpc_messages/rref_backward_resp.h>
#include <torch/csrc/distributed/autograd/utils.h>
#include <torch/csrc/distributed/rpc/profiler/server_process_global_profiler.h>
#include <torch/csrc/distributed/rpc/python_call.h>
#include <torch/csrc/distributed/rpc/python_remote_call.h>
#include <torch/csrc/distributed/rpc/python_resp.h>
#include <torch/csrc/distributed/rpc/python_rpc_handler.h>
#include <torch/csrc/distributed/rpc/rref_context.h>
#include <torch/csrc/distributed/rpc/rref_impl.h>
#include <torch/csrc/distributed/rpc/rref_proto.h>
#include <torch/csrc/distributed/rpc/script_call.h>
#include <torch/csrc/distributed/rpc/script_remote_call.h>
#include <torch/csrc/distributed/rpc/script_resp.h>
#include <torch/csrc/distributed/rpc/unpickled_python_call.h>
#include <torch/csrc/distributed/rpc/unpickled_python_remote_call.h>
#include <torch/csrc/distributed/rpc/utils.h>
#include <torch/csrc/jit/frontend/code_template.h>
#include <torch/csrc/jit/python/python_ivalue.h>

namespace torch {
namespace distributed {
namespace rpc {

using namespace torch::distributed::autograd;

namespace {

std::unique_ptr<RpcCommandBase> deserializePythonRpcCommandReference(
    RpcCommandBase& rpc,
    const MessageType& messageType) {
  switch (messageType) {
    case MessageType::PYTHON_CALL: {
      auto& pc = static_cast<PythonCall&>(rpc);
      return std::make_unique<UnpickledPythonCall>(
          pc.serializedPyObj(), pc.isAsyncExecution());
    }
    case MessageType::PYTHON_REMOTE_CALL: {
      auto& prc = static_cast<PythonRemoteCall&>(rpc);
      return std::make_unique<UnpickledPythonRemoteCall>(
          prc.serializedPyObj(),
          prc.retRRefId(),
          prc.retForkId(),
          prc.isAsyncExecution());
    }
    case MessageType::FORWARD_AUTOGRAD_REQ: {
      // Deserialize the wrapped RPC if it contains Python UDF
      auto& rwa = static_cast<RpcWithAutograd&>(rpc);
      auto& wrappedRpc = rwa.wrappedRpc();
      auto pythonRpc = deserializePythonRpcCommandReference(
          wrappedRpc, rwa.wrappedMessageType());
      if (pythonRpc) {
        rwa.setWrappedRpc(std::move(pythonRpc));
      }
      return nullptr;
    }
    case MessageType::RUN_WITH_PROFILING_REQ: {
      // Deserialize wrapped RPC if it contains python call
      auto& rpcWithProfilingReq = static_cast<RpcWithProfilingReq&>(rpc);
      auto& wrappedRpc = rpcWithProfilingReq.wrappedRpc();
      auto pythonRpc = deserializePythonRpcCommandReference(
          wrappedRpc, rpcWithProfilingReq.wrappedMessageType());
      if (pythonRpc) {
        rpcWithProfilingReq.setWrappedRpc(std::move(pythonRpc));
      }
      return nullptr;
    }
    default: {
      return nullptr;
    }
  }
}

SerializedPyObj serializePyObject(IValue value) {
  auto& pythonRpcHandler = PythonRpcHandler::getInstance();
  // Need this GIL to guard jit::toPyObj and destruct its returned
  // py::object
  py::gil_scoped_acquire acquire;
  try {
    return pythonRpcHandler.serialize(jit::toPyObject(value));
  } catch (py::error_already_set& e) {
    // py::error_already_set requires GIL to destruct, take special care.
    auto err = std::runtime_error(e.what());
    e.restore();
    PyErr_Clear();
    throw err;
  }
}

} // anonymous namespace

c10::intrusive_ptr<JitFuture> RequestCallbackImpl::runPythonFunction(
    const py::object& function,
    bool isAsyncExecution) const {
  auto& pythonRpcHandler = PythonRpcHandler::getInstance();
  py::gil_scoped_acquire acquire;

  py::object result;
  try {
    result = pythonRpcHandler.runPythonUdf(function);
  } catch (py::error_already_set& e) {
    // py::error_already_set requires GIL to destruct, take special care.
    auto future =
        asFuture(std::make_exception_ptr(std::runtime_error(e.what())));
    e.restore();
    PyErr_Clear();
    return future;
  } catch (std::exception& e) {
    return asFuture(std::current_exception());
  }

  // After sync exection or failed async execution return the value as-is.
  if (pythonRpcHandler.isRemoteException(result) || !isAsyncExecution) {
    return asFuture(
        c10::ivalue::ConcretePyObjectHolder::create(result),
        at::PyObjectType::get());
  }

  try {
    return result.cast<jit::PythonFutureWrapper&>().fut;
  } catch (const py::cast_error& e) {
    auto type = result.get_type();
    auto errMsg = c10::str(
        e.what(),
        ". Functions decorated with @rpc.async_function must return a "
        "torch.futures.Future object, but got ",
        type.attr("__module__").cast<std::string>(),
        ".",
        type.attr("__qualname__").cast<std::string>());
    return asFuture(std::make_exception_ptr(std::runtime_error(errMsg)));
  }
}

std::unique_ptr<RpcCommandBase> RequestCallbackImpl::
    deserializePythonRpcCommand(
        std::unique_ptr<RpcCommandBase> rpc,
        const MessageType& messageType) const {
  auto pythonRpc = deserializePythonRpcCommandReference(*rpc, messageType);
  return pythonRpc ? std::move(pythonRpc) : std::move(rpc);
}

c10::intrusive_ptr<JitFuture> RequestCallbackImpl::processScriptCall(
    RpcCommandBase& rpc) const {
  auto& scriptCall = static_cast<ScriptCall&>(rpc);

  c10::intrusive_ptr<JitFuture> future;
  if (scriptCall.hasOp()) {
    future = runJitOperator(*scriptCall.op(), scriptCall.stackRef());
  } else {
    future = runJitFunction(
        scriptCall.qualifiedName(),
        scriptCall.stackRef(),
        scriptCall.isAsyncExecution());
  }

  return future->then(
      [](JitFuture& jitFuture) {
        return c10::make_intrusive<Message>(
            ScriptResp(jitFuture.value()).toMessage());
      },
      c10::getCustomClassType<c10::intrusive_ptr<Message>>());
}

c10::intrusive_ptr<JitFuture> RequestCallbackImpl::processPythonCall(
    RpcCommandBase& rpc) const {
  auto& upc = static_cast<UnpickledPythonCall&>(rpc);
  auto future = runPythonFunction(upc.pythonUdf(), upc.isAsyncExecution());

  return future->then(
      [](JitFuture& future) {
        return c10::make_intrusive<Message>(
            PythonResp(serializePyObject(future.value())).toMessage());
      },
      c10::getCustomClassType<c10::intrusive_ptr<Message>>());
}

c10::intrusive_ptr<JitFuture> RequestCallbackImpl::processScriptRemoteCall(
    RpcCommandBase& rpc) const {
  auto& scriptRemoteCall = static_cast<ScriptRemoteCall&>(rpc);

  c10::intrusive_ptr<JitFuture> future;
  if (scriptRemoteCall.hasOp()) {
    future =
        runJitOperator(*scriptRemoteCall.op(), scriptRemoteCall.stackRef());
  } else {
    future = runJitFunction(
        scriptRemoteCall.qualifiedName(),
        scriptRemoteCall.stackRef(),
        scriptRemoteCall.isAsyncExecution());
  }

  return assignOwnerRRef(
      scriptRemoteCall.retRRefId(),
      scriptRemoteCall.retForkId(),
      std::move(future),
      /*lsctx=*/nullptr);
}

c10::intrusive_ptr<JitFuture> RequestCallbackImpl::processPythonRemoteCall(
    RpcCommandBase& rpc,
    std::shared_ptr<LazyStreamContext> lsctx) const {
  auto& uprc = static_cast<UnpickledPythonRemoteCall&>(rpc);
  auto future = runPythonFunction(uprc.pythonUdf(), uprc.isAsyncExecution());

  return assignOwnerRRef(
      uprc.rrefId(), uprc.forkId(), std::move(future), std::move(lsctx));
}

c10::intrusive_ptr<JitFuture> RequestCallbackImpl::processPythonRRefFetchCall(
    RpcCommandBase& rpc,
    std::shared_ptr<LazyStreamContext> lsctx) const {
  auto& prf = static_cast<PythonRRefFetchCall&>(rpc);

  auto future = retrieveOwnerRRef(prf.rrefId(), std::move(lsctx));

  return future->then(
      [](JitFuture& future) {
        SerializedPyObj result = serializePyObject(future.value());
        return c10::make_intrusive<Message>(
            PythonRRefFetchRet(std::move(result).toIValues()).toMessage());
      },
      c10::getCustomClassType<c10::intrusive_ptr<Message>>());
}

void RequestCallbackImpl::handleRRefDelete(
    c10::intrusive_ptr<RRef>& rref) const {
  if (rref && rref->isPyObj()) {
    py::gil_scoped_acquire acquire;
    rref.reset();
  }
}

c10::intrusive_ptr<JitFuture> RequestCallbackImpl::processRpcWithErrors(
    RpcCommandBase& rpc,
    const MessageType& messageType,
    std::shared_ptr<LazyStreamContext> ctx) const {
  try {
    return processRpc(rpc, messageType, std::move(ctx));
  } catch (py::error_already_set& e) {
    // Pass a dummy message ID since it will be overwritten anyways.
    auto future = asFuture(handleError(e, messageType, -1));
    // There are request callback impls in Python, where Python
    // exceptions could be thrown. For releasing Python exception
    // py::objects, GIL must be held.
    py::gil_scoped_acquire acquire;
    e.restore(); // Release ownership on py::objects and also restore
                 // Python Error Indicator.
    PyErr_Clear(); // Clear the Python Error Indicator as we has
                   // recorded the exception in the response message.
    return future;
  } catch (std::exception& e) {
    // Pass a dummy message ID since it will be overwritten anyways.
    return asFuture(handleError(e, messageType, -1));
  }
}

bool RequestCallbackImpl::cudaAvailable() const {
#ifdef USE_CUDA
  return true;
#else
  return false;
#endif
}

c10::intrusive_ptr<JitFuture> RequestCallbackImpl::processRRefBackward(
    RpcCommandBase& rpc) const {
  auto& rrefBackwardReq = static_cast<RRefBackwardReq&>(rpc);

  auto future =
      retrieveOwnerRRef(rrefBackwardReq.getRRefId(), /*lsctx=*/nullptr);

  return future->then(
      [autogradContextId = rrefBackwardReq.getAutogradContextId(),
       retainGraph = rrefBackwardReq.retainGraph()](JitFuture& future) {
        // Run backward (TODO: make this async?).
        PyRRef::backwardOwnerRRef(
            autogradContextId, retainGraph, future.value());

        return c10::make_intrusive<Message>(RRefBackwardResp().toMessage());
      },
      c10::getCustomClassType<c10::intrusive_ptr<Message>>());
}

c10::intrusive_ptr<JitFuture> RequestCallbackImpl::runJitFunction(
    const c10::QualifiedName& name,
    std::vector<at::IValue>& stack,
    bool isAsyncExecution) const {
  c10::intrusive_ptr<JitFuture> future;
  try {
    // runAsync() starts in the calling thread, but may return an uncompleted
    // future (though for non-async code, it will typically be completed).
    // If it was async, our callback will typically be invoked by the
    // continuation on an at::launch() thread.
    future = PythonRpcHandler::getInstance()
                 .jitCompilationUnit()
                 ->get_function(name)
                 .runAsync(stack);
  } catch (const std::exception&) {
    return asFuture(std::current_exception());
  }

  if (isAsyncExecution) {
    at::TypePtr type = future->elementType();
    if (type->kind() != at::FutureType::Kind) {
      return asFuture(std::make_exception_ptr(std::runtime_error(c10::str(
          "Async functions must return an IValue of Future type, but got ",
          type->str()))));
    }
    future = future->thenAsync(
        [](JitFuture& future) { return future.value().toFuture(); },
        type->cast<at::FutureType>()->getElementType());
  }

  return future;
}

} // namespace rpc
} // namespace distributed
} // namespace torch
