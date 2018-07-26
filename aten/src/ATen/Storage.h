#pragma once

#include <ATen/StorageImpl.h>

namespace at {

struct Storage {
public:
  Storage() = delete;
  Storage(StorageImpl* storage_impl) {
    storage_impl_ = storage_impl;
    if (storage_impl_)
      storage_impl_->retain();
  };
  ~Storage();
  // There are reasonable interpretations of these constructors, but they're to
  // be implemented on demand.
  Storage(Storage&) = delete;
  Storage(const Storage&) = delete;
  Storage(Storage&&) = delete;
  Storage(const Storage&&) = delete;
  void* unsafeGetTH(bool retain_) const {
    if (retain_ && storage_impl_)
      storage_impl_->retain();
    return storage_impl_;
  }
  StorageImpl* pImpl() {
    return storage_impl_;
  }
  StorageImpl* pImpl() const {
    return storage_impl_;
  }

 protected:
  StorageImpl* storage_impl_;
};

} // namespace at
