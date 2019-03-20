#pragma once

#include <string>
#include <mutex>
#include <memory>
#include <unordered_map>
#include <vector>

namespace torch { namespace jit { namespace logging {

class LoggerBase {
 public:
  virtual void addStatValue(std::string stat_name, float val) = 0;
  virtual std::unordered_map<std::string, float> getCounters() const = 0;
  virtual ~LoggerBase() {}
};

std::shared_ptr<LoggerBase> getLogger();
void setLogger(std::shared_ptr<LoggerBase> logger);

// No-op logger. This is the default and is meant to incur almost no runtime
// overhead.

class NoopLogger : public LoggerBase {
 public:
  void addStatValue(std::string stat_name, float val) override {}
  std::unordered_map<std::string, float> getCounters() const override {
    return {};
  }
  ~NoopLogger() {}
};

// Trivial locking logger. Pass in an instance of this to setLogger() to use it.
// This keeps track of the sum of all statistics.
//
// NOTE: this is not written in a scalable way and should probably only be used
// in the single-threaded case or for testing.
class LockingLogger : public LoggerBase {
 public:
  void addStatValue(std::string stat_name, float val) override;
  std::unordered_map<std::string, float> getCounters() const override;
  enum class AggregationType {
    SUM,
    AVG
  };
  void setAggregationType(std::string stat_name, AggregationType type);
  ~LockingLogger() {}
 private:
  mutable std::mutex m;
  std::unordered_map<std::string, std::vector<float>> raw_counters;
  std::unordered_map<std::string, AggregationType> agg_types;
};

// Make this struct so the timer internals are opaque to the user.
struct JITTimePoint {
  std::chrono::time_point<std::chrono::high_resolution_clock> point;
};

JITTimePoint timePoint();
void recordDurationSince(std::string name, JITTimePoint tp);

}}}