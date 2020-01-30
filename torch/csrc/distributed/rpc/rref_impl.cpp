#include <torch/csrc/distributed/rpc/rref_impl.h>

#include <torch/csrc/distributed/autograd/rpc_messages/rpc_with_autograd.h>
#include <torch/csrc/distributed/autograd/utils.h>
#include <torch/csrc/distributed/rpc/python_rpc_handler.h>
#include <torch/csrc/distributed/rpc/rref_context.h>
#include <torch/csrc/distributed/rpc/rref_proto.h>
#include <torch/csrc/distributed/rpc/utils.h>
#include <torch/csrc/jit/pybind_utils.h>

namespace torch {
namespace distributed {
namespace rpc {

std::atomic<local_id_t> RRefContext::nextLocalId_{0};

//////////////////////////  RRefForkData  /////////////////////////////////

RRefForkData::RRefForkData(
    worker_id_t ownerId,
    const RRefId& rrefId,
    const ForkId& forkId,
    worker_id_t parent,
    std::string typeStr)
    : ownerId_(ownerId),
      rrefId_(rrefId),
      forkId_(forkId),
      parent_(parent),
      typeStr_(std::move(typeStr)) {}

//////////////////////////////  RRef  /////////////////////////////////////

RRef::RRef(worker_id_t ownerId, const RRefId& rrefId, TypePtr type)
    : RRefInterface(),
      ownerId_(ownerId),
      rrefId_(rrefId),
      type_(std::move(type)) {}

RRefForkData RRef::fork() const {
  auto& ctx = RRefContext::getInstance();
  return RRefForkData(
      ownerId_,
      rrefId_,
      ctx.genGloballyUniqueId(),
      ctx.getWorkerId(),
      type_->str());
}

//////////////////////////  UserRRef  /////////////////////////////////////

UserRRef::UserRRef(
    worker_id_t ownerId,
    const RRefId& rrefId,
    const ForkId& forkId,
    TypePtr type)
    : RRef(ownerId, rrefId, std::move(type)), forkId_(forkId) {
  // Do nothing,
  // (1) If this UserRRef is a fork of an existing RRef, RRefContext will send
  //     a RREF_FORK_REQUEST message to the owner.
  // (2) If this the creator UserRRef, ScriptRemoteCall or PythonRemoteCall will
  //     properly notify the owner.
}

UserRRef::~UserRRef() {
  try {
    RRefContext::getInstance().delUser(ownerId_, rrefId_, forkId_);
  } catch (const std::exception& ex) {
    LOG(ERROR) << "Error occurred when deleting UserRRef instance, "
               << "RRefId = " << rrefId_ << ", ForkId = " << forkId_ << " : "
               << ex.what();
  } catch (...) {
    LOG(ERROR) << "Error occurred when deleting UserRRef instance, "
               << "RRefId = " << rrefId_ << ", ForkId = " << forkId_ << " : "
               << "unknown error";
  }
}

const ForkId& UserRRef::forkId() const {
  return forkId_;
}

IValue UserRRef::toHere() {
  auto agent = RpcAgent::getCurrentRpcAgent();

  // ScriptRRefFetchCall message always carries autograd context id even if
  // the message itself does not contain any tensor, because the response would
  // potentially contain tensors.
  Message msgToSend;

  if (isPyObj()) {
    msgToSend = PythonRRefFetchCall(ownerId_, rrefId()).toMessage();
  } else {
    msgToSend = ScriptRRefFetchCall(ownerId_, rrefId()).toMessage();
  }

  auto futureResponse = autograd::sendMessageWithAutograd(
      *agent,
      agent->getWorkerInfo(ownerId_),
      std::move(msgToSend),
      true /* forceGradRecording */);

  const Message& message = futureResponse->wait();
  MessageType msgType = message.type();
  auto response = deserializeResponse(message, msgType);
  TORCH_INTERNAL_ASSERT(
      msgType == MessageType::SCRIPT_RREF_FETCH_RET ||
          msgType == MessageType::PYTHON_RREF_FETCH_RET,
      "Message type should either be SCRIPT_RREF_FETCH_RET "
      "or PYTHON_RREF_FETCH_RET");
  RpcCommandBase& rpc = *response;
  if (isPyObj()) {
    auto& pythonRRefFetchRet = static_cast<PythonRRefFetchRet&>(rpc);
    return jit::toIValue(
        PythonRpcHandler::getInstance().deserialize(
            SerializedPyObj::fromIValues(pythonRRefFetchRet.values())),
        PyObjectType::get());
  } else {
    auto& pythonRRefFetchRet = static_cast<ScriptRRefFetchRet&>(rpc);
    return pythonRRefFetchRet.values().front();
  }
}

//////////////////////////  OwnerRRef  /////////////////////////////////////

const IValue& OwnerRRef::getValue() const {
  std::unique_lock<std::mutex> lock(mutex_);
  valueCV_.wait(lock, [this] { return value_.has_value(); });
  return value_.value();
}

bool OwnerRRef::hasValue() const {
  std::lock_guard<std::mutex> lock(mutex_);
  return value_.has_value();
}

std::shared_ptr<FutureMessage> OwnerRRef::getFuture() {
  std::unique_lock<std::mutex> lock(mutex_);
  if (future_.get()) {
    return future_;
  }
  future_ = std::make_shared<FutureMessage>();
  std::shared_ptr<FutureMessage> ret = future_;
  if (value_.has_value()) {
    lock.unlock();
    ret->markCompleted(Message());
  }
  return ret;
}

void OwnerRRef::setValue(IValue&& value) {
  std::unique_lock<std::mutex> lock(mutex_);
  value_ = std::move(value);
  std::shared_ptr<FutureMessage> future;
  future.swap(future_);
  lock.unlock();
  valueCV_.notify_all();
  if (future.get() && !future->completed()) {
    future->markCompleted(Message());
  }
}

} // namespace rpc
} // namespace distributed
} // namespace torch
