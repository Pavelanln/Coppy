# Owner(s): ["oncall: distributed"]

import itertools

import torch
from torch.distributed._tensor import distribute_tensor, DTensor
from torch.distributed._tensor._utils import (
    compute_local_shape,
    compute_local_shape_and_global_offset,
)
from torch.distributed.device_mesh import DeviceMesh, init_device_mesh
from torch.distributed.tensor._dtensor_spec import DTensorSpec, TensorMeta
from torch.distributed.tensor.debug import CommDebugMode
from torch.distributed.tensor.placement_types import _StridedShard, Replicate, Shard
from torch.testing._internal.common_utils import run_tests
from torch.testing._internal.distributed._tensor.common_dtensor import (
    DTensorTestBase,
    with_comms,
)


c10d_functional = torch.ops.c10d_functional


class UtilTest(DTensorTestBase):
    @property
    def world_size(self):
        return 8

    @with_comms
    def test_compute_local_shape_2d_uneven(self):
        # mesh: 4 * 2
        mesh_tensor = torch.arange(self.world_size).reshape(4, 2)
        mesh = DeviceMesh(self.device_type, mesh_tensor)
        size = torch.Size([7, 7])
        rank_coordinates = mesh.get_coordinate()

        # replicate, shard
        placements2 = [Replicate(), Shard(0)]
        local_size2 = compute_local_shape(size, mesh, placements2)
        if rank_coordinates[1] < 1:
            self.assertEqual(local_size2, torch.Size([4, 7]))
        else:
            self.assertEqual(local_size2, torch.Size([3, 7]))

        # shard, shard
        placements3 = [Shard(0), Shard(1)]
        local_size3 = compute_local_shape(size, mesh, placements3)
        # first dim
        if rank_coordinates[0] < 3:
            self.assertEqual(local_size3[0], 2)
        else:
            self.assertEqual(local_size3[0], 1)
        # second dim
        if rank_coordinates[1] < 1:
            self.assertEqual(local_size3[1], 4)
        else:
            self.assertEqual(local_size3[1], 3)

    @with_comms
    def test_compute_local_shape_and_global_offset_1D(self):
        one_d_placements = [[Shard(0)], [Replicate()]]

        for placements in one_d_placements:
            # When the placements is [Shard(0)], we test for three different scenarios:
            # 1) sharding resulting in empty shards on all or some of the ranks
            # 2) sharding resulting in shards of different size across different ranks
            # 3) sharding resulting in non-empty shards of same size across all ranks
            for size in range(self.world_size * 2 + 1):
                mesh_tensor = torch.arange(self.world_size)
                device_mesh = DeviceMesh(self.device_type, mesh_tensor)
                global_tensor = torch.arange(size)
                global_shape = global_tensor.size()

                dtensor = distribute_tensor(global_tensor, device_mesh, placements)
                local_size, global_offset = compute_local_shape_and_global_offset(
                    global_shape, device_mesh, placements
                )

                # TODO: make this test cleaner and work for nD
                dim0_start = global_offset[0]
                dim0_end = global_offset[0] + local_size[0]

                # Check the local tensor of dtensor is exactly the same
                # if we slice the global_tensor with local_size and global_offset
                self.assertEqual(
                    dtensor.to_local(),
                    global_tensor[dim0_start:dim0_end],
                )

    @with_comms
    def test_compute_local_shape_and_global_offset_2D(self):
        two_d_placements_options = [Shard(0), Shard(1), Replicate()]
        # Generating 6 two-d placements combinations
        two_d_placements = list(
            itertools.combinations_with_replacement(two_d_placements_options, 2)
        )

        for placements in two_d_placements:
            for dim_0_size in (1, 2, 4, 8):
                # mesh: 2 * 4
                mesh_tensor = torch.arange(self.world_size).reshape(2, 4)
                device_mesh = DeviceMesh(self.device_type, mesh_tensor)
                global_tensor = torch.arange(64).view(dim_0_size, -1)
                global_shape = global_tensor.size()

                dtensor = distribute_tensor(global_tensor, device_mesh, placements)
                local_size, global_offset = compute_local_shape_and_global_offset(
                    global_shape, device_mesh, placements
                )

                # TODO: make this test cleaner and work for nD
                dim0_start = global_offset[0]
                dim0_end = global_offset[0] + local_size[0]
                dim1_start = global_offset[1]
                dim1_end = global_offset[1] + local_size[1]

                # Check the local tensor of dtensor is exactly the same
                # if we slice the global_tensor with local_size and global_offset
                self.assertEqual(
                    dtensor.to_local(),
                    global_tensor[dim0_start:dim0_end, dim1_start:dim1_end],
                )

    @with_comms
    def test_fsdp_tp_meta_compute(self):
        # FSDP + TP sharding
        tp_size = 2
        dp_size = self.world_size // tp_size
        global_mesh = init_device_mesh(
            self.device_type, (dp_size, tp_size), mesh_dim_names=("dp", "tp")
        )
        # local shard shape is [2, 2]
        global_tensor_shape = torch.Size([2 * self.world_size, 2])
        placements = [_StridedShard(0, split_factor=tp_size), Shard(0)]

        local_shape, global_offset = compute_local_shape_and_global_offset(
            global_tensor_shape, global_mesh, placements
        )
        assert global_mesh.get_coordinate is not None
        dp_rank = global_mesh.get_local_rank("dp")
        tp_rank = global_mesh.get_local_rank("tp")
        shard_idx_on_dim_0 = tp_rank * dp_size + dp_rank
        expected_local_shape = (2, 2)
        expected_global_offset = (shard_idx_on_dim_0 * 2, 0)
        self.assertEqual(local_shape, expected_local_shape)
        self.assertEqual(global_offset, expected_global_offset)

    @with_comms
    def test_hsdp_tp_meta_compute(self):
        # HSDP + TP sharding
        tp_size = 2
        dp_shard_size = 2
        dp_replic_size = self.world_size // (dp_shard_size * tp_size)
        global_mesh = init_device_mesh(
            self.device_type,
            (dp_replic_size, dp_shard_size, tp_size),
            mesh_dim_names=("dp_replic", "dp_shard", "tp"),
        )
        # local shard shape is [2, 2]
        global_tensor_shape = torch.Size([2 * dp_shard_size * tp_size, 2])
        placements = [Replicate(), _StridedShard(0, split_factor=tp_size), Shard(0)]

        local_shape, global_offset = compute_local_shape_and_global_offset(
            global_tensor_shape, global_mesh, placements
        )
        assert global_mesh.get_coordinate is not None
        dp_replic_rank = global_mesh.get_local_rank("dp_replic")
        dp_shard_rank = global_mesh.get_local_rank("dp_shard")
        tp_rank = global_mesh.get_local_rank("tp")
        shard_idx_on_dim_0 = tp_rank * dp_shard_size + dp_shard_rank
        expected_local_shape = (2, 2)
        expected_global_offset = (shard_idx_on_dim_0 * 2, 0)
        self.assertEqual(local_shape, expected_local_shape)
        self.assertEqual(global_offset, expected_global_offset)

    # TODO: remove this test once we support general meta compute on strided sharding
    @with_comms
    def test_strided_sharding_assumption_in_meta_compute(self):
        # current ``compute_local_shape_and_global_offset`` does not allow Shard(i)
        # placement to appear after the strided sharding part has ended. This test
        # check that ``compute_local_shape_and_global_offset`` does not allow placements
        # that violate the assumption and does not forbid the allowed ones.

        # Test 0: 2-D mesh
        mesh_size_0 = 2
        mesh_size_1 = self.world_size // mesh_size_0
        global_mesh = init_device_mesh(
            self.device_type,
            (mesh_size_0, mesh_size_1),
            mesh_dim_names=("mesh-0", "mesh-1"),
        )
        global_tensor_shape = torch.Size([2 * self.world_size, 2 * self.world_size])

        for shard_dim in [0, 1]:
            placements = [
                _StridedShard(shard_dim, split_factor=mesh_size_1),
                Shard(shard_dim),
            ]
            _, _ = compute_local_shape_and_global_offset(
                global_tensor_shape, global_mesh, placements
            )

        # Test 1: 3-D mesh
        mesh_size_0 = 2
        mesh_size_1 = 2
        mesh_size_2 = self.world_size // (mesh_size_0 * mesh_size_1)
        global_mesh = init_device_mesh(
            self.device_type,
            (mesh_size_0, mesh_size_1, mesh_size_2),
            mesh_dim_names=("mesh-0", "mesh-1", "mesh-2"),
        )

        # legal placements: Shard() appear after the strided part but it's on another
        # tensor dimension.
        placements = [
            _StridedShard(0, split_factor=mesh_size_1),
            Shard(0),
            Shard(1),
        ]
        _, _ = compute_local_shape_and_global_offset(
            global_tensor_shape, global_mesh, placements
        )

        # illegal placements: Shard() appear after the strided part and it's on the
        # same tensor dimension.
        placements = [
            _StridedShard(0, split_factor=mesh_size_1),
            Shard(0),
            Shard(0),
        ]
        with self.assertRaisesRegex(NotImplementedError, "the strided part has ended"):
            _, _ = compute_local_shape_and_global_offset(
                global_tensor_shape, global_mesh, placements
            )

        # Test 2: 4-D mesh
        mesh_size_0 = 1
        mesh_size_1 = 2
        mesh_size_2 = 2
        mesh_size_3 = self.world_size // (mesh_size_0 * mesh_size_1 * mesh_size_2)
        global_mesh = init_device_mesh(
            self.device_type,
            (mesh_size_0, mesh_size_1, mesh_size_2, mesh_size_3),
            mesh_dim_names=("mesh-0", "mesh-1", "mesh-2", "mesh-3"),
        )
        # legal placements: Shard() appear after the strided part but it's on another
        # tensor dimension.
        placements = [
            _StridedShard(0, split_factor=mesh_size_1),
            _StridedShard(1, split_factor=mesh_size_3),
            Shard(0),
            Shard(1),
        ]
        local_shape, _ = compute_local_shape_and_global_offset(
            global_tensor_shape, global_mesh, placements
        )
        expected_local_shape = (
            2 * mesh_size_1 * mesh_size_3,
            2 * mesh_size_0 * mesh_size_2,
        )
        self.assertEqual(local_shape, expected_local_shape)

        # illegal placements: Shard() appear after the strided part and it's on the
        # same tensor dimension.
        placements = [
            _StridedShard(0, split_factor=mesh_size_1),
            _StridedShard(1, split_factor=mesh_size_3),
            Shard(0),
            Shard(0),
        ]
        with self.assertRaisesRegex(NotImplementedError, "the strided part has ended"):
            _, _ = compute_local_shape_and_global_offset(
                global_tensor_shape, global_mesh, placements
            )


class TestStridedSharding(DTensorTestBase):
    @property
    def world_size(self):
        return 4

    @with_comms
    def test_1d_mesh_strided_sharding(self):
        mesh_1d = init_device_mesh(self.device_type, (self.world_size,))
        # Test 1: 1-d tensor over 1-d mesh
        x = torch.arange(2 * self.world_size, device=self.device_type)
        """
        contiguous sharding: [0, 1 | 2, 3 | 4, 5 | 6, 7]
        """
        shard_placement = _StridedShard(0, split_factor=1)  # same as Shard(0)
        tensor_list, _ = shard_placement._split_tensor(x, self.world_size)
        shard_x = tensor_list[self.rank]
        self.assertEqual(shard_x, x.view(self.world_size, -1)[self.rank])
        # shard_to_replicate
        full_tensor = shard_placement._to_replicate_tensor(
            shard_x,
            mesh_1d,
            mesh_dim=0,
            current_logical_shape=list(x.shape),
        )
        self.assertEqual(full_tensor, x)

        """
        strided sharding: [0, 4 | 1, 5 | 2, 6 | 3, 7]
        """
        shard_placement = _StridedShard(0, split_factor=2)
        tensor_list, _ = shard_placement._split_tensor(x, self.world_size)
        shard_x = tensor_list[self.rank]
        self.assertEqual(
            shard_x, x.view(-1, self.world_size).swapdims(-1, 0)[self.rank]
        )
        # shard_to_replicate
        full_tensor = shard_placement._to_replicate_tensor(
            shard_x,
            mesh_1d,
            mesh_dim=0,
            current_logical_shape=list(x.shape),
        )
        self.assertEqual(full_tensor, x)

    @with_comms
    def test_2d_mesh_strided_sharding(self):
        # Test 2: 1-d tensor over 2-d mesh
        mesh_2d = init_device_mesh(
            self.device_type, (2, self.world_size // 2), mesh_dim_names=("dim0", "dim1")
        )
        mesh_dim0_size = mesh_2d["dim0"].size()
        mesh_dim1_size = mesh_2d["dim1"].size()
        mesh_dim0_local_rank = mesh_2d["dim0"].get_local_rank(mesh_dim=0)
        mesh_dim1_local_rank = mesh_2d["dim1"].get_local_rank(mesh_dim=0)
        x = torch.arange(2 * self.world_size, device=self.device_type)
        """
        contiguous sharding: [
            [ 0, 1 | 2, 3 ],
            [ 4, 5 | 6, 7 ],
        ]
        """
        # shard on mesh dim-0
        shard_placement_dim0 = _StridedShard(0, split_factor=1)  # same as Shard(0)
        tensor_list, _ = shard_placement_dim0._split_tensor(x, mesh_dim0_size)
        expected_shard_dim0 = x.view(mesh_dim0_size, -1)[mesh_dim0_local_rank]
        shard_x = tensor_list[mesh_dim0_local_rank]
        self.assertEqual(shard_x, expected_shard_dim0)

        # shard on mesh dim-1
        shard_placement_dim1 = _StridedShard(0, split_factor=1)  # same as Shard(0)
        tensor_list, _ = shard_placement_dim1._split_tensor(shard_x, mesh_dim1_size)
        expected_shard_dim1 = shard_x.view(mesh_dim1_size, -1)[mesh_dim1_local_rank]
        shard_x = tensor_list[mesh_dim1_local_rank]
        self.assertEqual(shard_x, expected_shard_dim1)

        # shard_to_replicate on mesh dim-1
        full_tensor = shard_placement_dim1._to_replicate_tensor(
            shard_x,
            mesh_2d,
            mesh_dim=1,
            current_logical_shape=list(expected_shard_dim0.shape),
        )
        self.assertEqual(full_tensor, expected_shard_dim0)

        # shard_to_replicate on mesh dim-0
        full_tensor = shard_placement_dim0._to_replicate_tensor(
            full_tensor,
            mesh_2d,
            mesh_dim=0,
            current_logical_shape=list(x.shape),
        )
        self.assertEqual(full_tensor, x)

        """
        strided sharding: [
            [ 0, 1 | 4, 5 ],
            [ 2, 3 | 6, 7 ],
        ]
        """
        split_factor = 2
        # shard on mesh dim-0
        shard_placement_dim0 = _StridedShard(0, split_factor=split_factor)
        tensor_list, _ = shard_placement_dim0._split_tensor(x, mesh_dim0_size)
        shard_x = tensor_list[mesh_dim0_local_rank]
        expected_shard_dim0 = (
            torch.tensor([0, 1, 4, 5], device=self.device_type)
            if mesh_dim0_local_rank == 0
            else torch.tensor([2, 3, 6, 7], device=self.device_type)
        )
        self.assertEqual(shard_x, expected_shard_dim0)

        # shard on mesh dim-1
        shard_placement_dim1 = _StridedShard(0, split_factor=1)  # same as Shard(0)
        tensor_list, _ = shard_placement_dim1._split_tensor(shard_x, mesh_dim1_size)
        shard_x = tensor_list[mesh_dim1_local_rank]
        expected_shard_dim1 = expected_shard_dim0.view(mesh_dim1_size, -1)[
            mesh_dim1_local_rank
        ]
        self.assertEqual(shard_x, expected_shard_dim1)

        # shard_to_replicate on mesh dim-1
        full_tensor = shard_placement_dim1._to_replicate_tensor(
            shard_x,
            mesh_2d,
            mesh_dim=1,
            current_logical_shape=list(expected_shard_dim0.shape),
        )
        self.assertEqual(full_tensor, expected_shard_dim0)

        # shard_to_replicate on mesh dim-0
        full_tensor = shard_placement_dim0._to_replicate_tensor(
            full_tensor,
            mesh_2d,
            mesh_dim=0,
            current_logical_shape=list(x.shape),
        )
        self.assertEqual(full_tensor, x)

    @with_comms
    def test_2d_mesh_2d_tensor_strided_sharding(self):
        # Test 2: 1-d tensor over 2-d mesh
        mesh_2d = init_device_mesh(
            self.device_type, (2, self.world_size // 2), mesh_dim_names=("dim0", "dim1")
        )
        mesh_dim0_size = mesh_2d["dim0"].size()
        mesh_dim1_size = mesh_2d["dim1"].size()
        mesh_dim0_local_rank = mesh_2d["dim0"].get_local_rank(mesh_dim=0)
        mesh_dim1_local_rank = mesh_2d["dim1"].get_local_rank(mesh_dim=0)
        x = torch.arange(2 * self.world_size, device=self.device_type).reshape(2, -1)
        """
        strided sharding:
            rank 0: [[0], [4]]
            rank 1: [[2], [6]]
            rank 2: [[1], [5]]
            rank 3: [[3], [7]]
        """
        split_factor = 2
        # shard on mesh dim-0
        shard_placement_dim0 = _StridedShard(1, split_factor=split_factor)
        tensor_list, _ = shard_placement_dim0._split_tensor(x, mesh_dim0_size)
        shard_x = tensor_list[mesh_dim0_local_rank]
        expected_shard_dim0 = (
            torch.tensor([[0, 2], [4, 6]], device=self.device_type)
            if mesh_dim0_local_rank == 0
            else torch.tensor([[1, 3], [5, 7]], device=self.device_type)
        )
        self.assertEqual(shard_x, expected_shard_dim0)

        # shard on mesh dim-1
        shard_placement_dim1 = _StridedShard(1, split_factor=1)  # same as Shard(1)
        tensor_list, _ = shard_placement_dim1._split_tensor(shard_x, mesh_dim1_size)
        shard_x = tensor_list[mesh_dim1_local_rank]
        expected_shard_dim1 = [
            torch.tensor(value, device=self.device_type)
            for value in [[[0], [4]], [[2], [6]], [[1], [5]], [[3], [7]]]
        ][self.rank]
        self.assertEqual(shard_x, expected_shard_dim1)

        # shard_to_replicate on mesh dim-1
        full_tensor = shard_placement_dim1._to_replicate_tensor(
            shard_x,
            mesh_2d,
            mesh_dim=1,
            current_logical_shape=list(expected_shard_dim0.shape),
        )
        self.assertEqual(full_tensor, expected_shard_dim0)

        # shard_to_replicate on mesh dim-0
        full_tensor = shard_placement_dim0._to_replicate_tensor(
            full_tensor,
            mesh_2d,
            mesh_dim=0,
            current_logical_shape=list(x.shape),
        )
        self.assertEqual(full_tensor, x)


class Test2DStridedLocalShard(DTensorTestBase):
    @property
    def world_size(self):
        return 4

    @with_comms
    def test_fsdp1_tp_2d_dtensor_local_shards_and_offsets(self):
        # We are mimicking the behavior of FSDP1 + TP.
        # Currently, the 2D DTensor's local shard is correct, since from_local + redistribute incurs a all_gather behind the scene.
        # When we have a global_tensor of [0, 1, 2, 3, 4, 5, 6, 7], the local shard of 2D DTensor would be:
        # rank0: [0, 1], rank1: [2, 3], rank2: [4, 5], rank3: [6, 7]
        with CommDebugMode() as comm_mode:
            global_tensor = torch.arange(8).view(4, 2)
            mesh_2d = init_device_mesh(
                self.device_type, (2, 2), mesh_dim_names=("DP", "TP")
            )
            tp_mesh = mesh_2d["TP"]
            dtensor_tp = distribute_tensor(
                global_tensor, tp_mesh, placements=[Shard(0)]
            )
            dtensor_2d = DTensor.from_local(
                dtensor_tp.to_local(), mesh_2d, [Replicate(), Shard(0)], run_check=False
            ).redistribute(mesh_2d, [Shard(0), Shard(0)])
            self.assertEqual(
                comm_mode.get_comm_counts()[c10d_functional.all_gather_into_tensor], 1
            )

        self.assertEqual(
            dtensor_2d.to_local(), global_tensor[self.rank : self.rank + 1]
        )
        # compute_local_shape_and_global_offset currently does take into consideration of strided sharding,
        # which should after strided sharding is added.
        local_size, global_offset = compute_local_shape_and_global_offset(
            global_tensor.shape, mesh_2d, [Shard(0), Shard(0)]
        )
        self.assertEqual(local_size, torch.Size([1, 2]))
        self.assertEqual(global_offset, torch.Size([self.rank, 0]))

    @with_comms
    def test_fsdp2_tp_2d_dtensor_local_shards_and_offsets(self):
        # We are mimicking the behavior of FSDP2 + TP.
        # Currently, the 2D DTensor's local shard is incorrect for resharding, since we want to avoid extra communication.
        # It's incorrect for resharding, since `compute_local_shape_and_global_offset`
        # doesn't know the correct offsets for resharding.
        # When we have a global_tensor of [0, 1, 2, 3, 4, 5, 6, 7], the local shard of 2D DTensor would be:
        # local tensor -- rank0: [0, 1], rank1: [4, 5], rank2: [2, 3], rank3: [6, 7]
        # current offsets -- rank0: [0, 0], rank1: [1, 0], rank2: [2, 0], rank3: [3, 0]
        # Ideally, with strided sharding, the offsets should be  rank0: [0, 0], rank1: [2, 0], rank2: [1, 0], rank3: [3, 0]
        # TODO: to make the local shard of FSDP2 + TP correct for resharding, it would require strided_sharding
        # as well as let compute_local_shape_and_global_offset takes into consideration of strided_sharding.
        global_tensor = torch.arange(8).view(4, 2)
        with CommDebugMode() as comm_mode:
            mesh_2d = init_device_mesh(
                self.device_type, (2, 2), mesh_dim_names=("DP", "TP")
            )
            tp_mesh = mesh_2d["TP"]
            dtensor_tp = distribute_tensor(
                global_tensor, tp_mesh, placements=[Shard(0)]
            )
            chunks = list(torch.chunk(dtensor_tp.to_local(), 2, dim=0))
            shard_rank = 0 if self.rank // 2 == 0 else 1
            sharded_param = chunks[shard_rank]
            spec_2d = DTensorSpec(
                mesh=mesh_2d,
                placements=(_StridedShard(0, split_factor=2), Shard(0)),
                tensor_meta=TensorMeta(
                    global_tensor.size(),
                    global_tensor.stride(),
                    global_tensor.dtype,
                ),
            )

            dtensor_2d = DTensor(
                sharded_param,
                spec_2d,
                requires_grad=False,
            )

        self.assertEqual(
            comm_mode.get_comm_counts()[c10d_functional.all_gather_into_tensor], 0
        )

        self.assertEqual(global_tensor, dtensor_2d.full_tensor())


if __name__ == "__main__":
    run_tests()
