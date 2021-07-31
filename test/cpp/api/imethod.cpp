// (c) Facebook, Inc. and its affiliates. Confidential and proprietary.

#include <gtest/gtest.h>
#include <torch/csrc/deploy/deploy.h>
#include <torch/script.h>
#include <torch/torch.h>

using namespace ::testing;
using namespace caffe2;

const char* simple = "torch/csrc/deploy/example/generated/simple";
const char* simpleJit = "torch/csrc/deploy/example/generated/simple_jit";

// TODO(jwtan): Try unifying cmake and buck for getting the path.
const char* path(const char* envname, const char* path) {
  const char* e = getenv(envname);
  return e ? e : path;
}

// TODO(jwtan): Considering moving the following tests to somewhere else as linking deploy (sub-classes)
// doesn't seem appropriate for torch API tests, and removing the corresponding cmake/buck configurations too.
TEST(IMethodTest, CallMethod) {
  auto scriptModel = torch::jit::load(path("SIMPLE_JIT", simpleJit));
  auto scriptMethod = scriptModel.get_method("forward");

  torch::deploy::InterpreterManager manager(3);
  torch::deploy::Package package = manager.load_package(path("SIMPLE", simple));
  auto pyModel = package.load_pickle("model", "model.pkl");
  torch::deploy::PythonMethodWrapper pyMethod(pyModel, "forward");

  auto input = torch::ones({10, 20});
  auto outputPy = pyMethod({input});
  auto outputScript = scriptMethod({input});
  EXPECT_TRUE(outputPy.isTensor());
  EXPECT_TRUE(outputScript.isTensor());
  auto outputPyTensor = outputPy.toTensor();
  auto outputScript_tensor = outputScript.toTensor();

  EXPECT_TRUE(outputPyTensor.equal(outputScript_tensor));
  EXPECT_EQ(outputPyTensor.numel(), 200);
}

TEST(IMethodTest, GetArgumentNames) {
  auto scriptModel = torch::jit::load(path("SIMPLE_JIT", simpleJit));
  auto scriptMethod = scriptModel.get_method("forward");

  auto& scriptNames = scriptMethod.getArgumentNames();
  EXPECT_EQ(scriptNames.size(), 2);
  EXPECT_STREQ(scriptNames[0].c_str(), "self");
  EXPECT_STREQ(scriptNames[1].c_str(), "input");

  torch::deploy::InterpreterManager manager(3);
  torch::deploy::Package package = manager.load_package(path("SIMPLE", simple));
  auto pyModel = package.load_pickle("model", "model.pkl");
  torch::deploy::PythonMethodWrapper pyMethod(pyModel, "forward");

  auto& pyNames = pyMethod.getArgumentNames();
  EXPECT_EQ(pyNames.size(), 2);
  EXPECT_STREQ(pyNames[0].c_str(), "input");
  EXPECT_STREQ(pyNames[1].c_str(), "kwargs");
}
