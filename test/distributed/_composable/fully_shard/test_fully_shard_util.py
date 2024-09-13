# Owner(s): ["oncall: distributed"]

import sys

import pytest

import torch
import torch.distributed as dist
from torch.distributed._composable import fully_shard
from torch.distributed.fsdp._debug_utils import (
    _get_sharded_module_tree_with_module_name_to_fqns,
)
from torch.distributed.fsdp.wrap import ModuleWrapPolicy
from torch.testing._internal.common_dist_composable import CompositeModel, UnitModule
from torch.testing._internal.common_distributed import skip_if_lt_x_gpu
from torch.testing._internal.common_fsdp import FSDPTest
from torch.testing._internal.common_utils import (
    run_tests,
    TEST_WITH_DEV_DBG_ASAN,
    TestCase,
)


is_cuda_8_9 = torch.cuda.is_available() and torch.cuda.get_device_capability() >= (8, 9)


if not dist.is_available():
    print("Distributed not available, skipping tests", file=sys.stderr)
    sys.exit(0)

if TEST_WITH_DEV_DBG_ASAN:
    print(
        "Skip dev-asan as torch + multiprocessing spawn have known issues",
        file=sys.stderr,
    )
    sys.exit(0)


class TestUtils(FSDPTest):
    @property
    def world_size(self):
        return 2

    @property
    def process_group(self):
        return dist.distributed_c10d._get_default_group()

    @skip_if_lt_x_gpu(2)
    def test_get_sharded_module_tree_with_module_name_to_fqns(self):
        model = CompositeModel(torch.device("cuda"))
        fully_shard(
            model,
            policy=ModuleWrapPolicy({UnitModule}),
        )
        (
            sharded_tree_info,
            sharded_module_name_to_fqns,
        ) = _get_sharded_module_tree_with_module_name_to_fqns(model)
        self.assertEqual(
            list(sharded_module_name_to_fqns.keys()),
            ["[CompositeModel]", "u1[UnitModule]", "u2[UnitModule]"],
        )
        self.assertEqual(
            list(sharded_module_name_to_fqns.values()),
            [
                ["l1.weight", "l1.bias", "l2.weight", "l2.bias"],
                [
                    "u1.l1.weight",
                    "u1.l1.bias",
                    "u1.seq.1.weight",
                    "u1.seq.1.bias",
                    "u1.l2.weight",
                    "u1.l2.bias",
                ],
                [
                    "u2.l1.weight",
                    "u2.l1.bias",
                    "u2.seq.1.weight",
                    "u2.seq.1.bias",
                    "u2.l2.weight",
                    "u2.l2.bias",
                ],
            ],
        )
        # Test nested fully_shard
        new_model = CompositeModel(torch.device("cuda"))
        fully_shard(new_model.u1)
        fully_shard(new_model)
        (
            sharded_tree_info,
            sharded_module_name_to_fqns,
        ) = _get_sharded_module_tree_with_module_name_to_fqns(new_model)
        self.assertEqual(
            list(sharded_module_name_to_fqns.keys()),
            ["[CompositeModel]", "u1[UnitModule]"],
        )
        self.assertEqual(
            list(sharded_module_name_to_fqns.values()),
            [
                [
                    "l1.weight",
                    "l1.bias",
                    "u2.l1.weight",
                    "u2.l1.bias",
                    "u2.seq.1.weight",
                    "u2.seq.1.bias",
                    "u2.l2.weight",
                    "u2.l2.bias",
                    "l2.weight",
                    "l2.bias",
                ],
                [
                    "u1.l1.weight",
                    "u1.l1.bias",
                    "u1.seq.1.weight",
                    "u1.seq.1.bias",
                    "u1.l2.weight",
                    "u1.l2.bias",
                ],
            ],
        )


class TestUtilsSingleDevice(TestCase):
    @pytest.mark.skipif(not is_cuda_8_9, reason="requires SM89 compatible machine")
    def test_foreach_copy_float8(self):
        for dtype in [
            torch.float8_e4m3fn,
            torch.float8_e4m3fnuz,
            torch.float8_e5m2,
            torch.float8_e5m2fnuz,
        ]:
            src = [torch.zeros(2, 2, device="cuda", dtype=dtype)] * 2
            dst = [torch.zeros(2, 2, device="cuda", dtype=dtype)] * 2
            # needed by fully_shard(Float8Linear)
            torch._foreach_copy_(src, dst)


if __name__ == "__main__":
    run_tests()
