class Voxel:
    def __init__(self, solidity: bool, value: float, x: int, y: int):
        self.Solidity = solidity
        self.Value = value
        self.X = x
        self.Y = y


class VoxelGridInfo:
    def __init__(self, size_x: int, size_y: int):
        self.SizeX = size_x
        self.SizeY = size_y
        self.VoxelList = []

    def is_location_inside(self, x: int, y: int):
        return 0 <= x < self.SizeX and 0 <= y < self.SizeY

    def get_voxel(self, x: int, y: int) -> Voxel:
        if self.is_location_inside(x, y) is False:
            return Voxel(False, 0.0, x, y)
        return self.VoxelList[x][y]
