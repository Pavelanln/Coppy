#ifndef CAFFE2_OPERATORS_CHANNEL_SHUFFLE_OP_H_
#define CAFFE2_OPERATORS_CHANNEL_SHUFFLE_OP_H_

#include "caffe2/core/context.h"
#include "caffe2/core/logging.h"
#include "caffe2/core/operator.h"

namespace caffe2 {

template <class Context>
class ChannelShuffleOp final : public Operator<Context> {
 public:
  USE_OPERATOR_CONTEXT_FUNCTIONS;

  template <class... Args>
  explicit ChannelShuffleOp(Args&&... args)
      : Operator<Context>(std::forward<Args>(args)...),
        order_(StringToStorageOrder(
            this->template GetSingleArgument<std::string>("order", "NCHW"))),
        OP_SINGLE_ARG(int, "group", group_, 1) {
    CAFFE_ENFORCE_NE(order_, StorageOrder::UNKNOWN);
  }

  bool RunOnDevice() override {
    return DispatchHelper<TensorTypes<float, double, int, int64_t, at::Half>>::
        call(this, Input(0));
  }

  template <typename T>
  bool DoRunWithType() {
    return order_ == StorageOrder::NCHW ? RunOnDeviceWithOrderNCHW<T>()
                                        : RunOnDeviceWithOrderNHWC<T>();
  }

  template <typename T>
  bool RunOnDeviceWithOrderNCHW();

  template <typename T>
  bool RunOnDeviceWithOrderNHWC();

 private:
  const StorageOrder order_;
  const int group_;
};

template <class Context>
class ChannelShuffleGradientOp final : public Operator<Context> {
 public:
  USE_OPERATOR_CONTEXT_FUNCTIONS;

  template <class... Args>
  explicit ChannelShuffleGradientOp(Args&&... args)
      : Operator<Context>(std::forward<Args>(args)...),
        order_(StringToStorageOrder(
            this->template GetSingleArgument<std::string>("order", "NCHW"))),
        OP_SINGLE_ARG(int, "group", group_, 1) {
    CAFFE_ENFORCE_NE(order_, StorageOrder::UNKNOWN);
  }

  bool RunOnDevice() override {
    return DispatchHelper<TensorTypes<float, double, int, int64_t, at::Half>>::
        call(this, Input(0));
  }

  template <typename T>
  bool DoRunWithType() {
    return order_ == StorageOrder::NCHW ? RunOnDeviceWithOrderNCHW<T>()
                                        : RunOnDeviceWithOrderNHWC<T>();
  }

  template <typename T>
  bool RunOnDeviceWithOrderNCHW();

  template <typename T>
  bool RunOnDeviceWithOrderNHWC();

 private:
  const StorageOrder order_;
  const int group_;
};

} // namespace caffe2

#endif // CAFFE2_OPERATORS_CHANNEL_SHUFFLE_OP_H_
