from voxel import *
from utils import *


class Brush:
    def __init__(self, size: int, strength: float, start_falloff: float, falloff_percent: float):
        self.Strength = strength
        self.StartFallOff = 0.0
        self.StartFallOff: float
        self.FallOffPercent = falloff_percent
        self.FallOffPercent: float
        self.Size = size
        self.Size: int
        self.FallOffBlocksAwayFromCenter = 0
        self.FallOffBlocksAwayFromCenter: int
        self.set_start_falloff(start_falloff)

    def set_size(self, size: int):
        self.Size = size
        self.set_start_falloff(self.StartFallOff)

    def set_start_falloff(self, start_falloff: float):
        self.StartFallOff = clamp(start_falloff, 0.0, 1.0)
        self.FallOffBlocksAwayFromCenter = int(float(self.Size) * start_falloff)

    def apply_to_grid(self, x: int, y: int, voxel_grid: VoxelGridInfo):
        for dx in range(x - self.Size, x + self.Size + 1):
            for dy in range(y - self.Size, y + self.Size + 1):
                dist = distance(dx, dy, x, y)

                if dist > self.Size or voxel_grid.is_location_inside(dx, dy) is False:
                    continue

                voxel = voxel_grid.get_voxel(dx, dy)
                if dist <= self.FallOffBlocksAwayFromCenter:
                    value = self.apply_pre_fall_off(voxel)
                    voxel.Value = value
                    new_voxel_value = value
                else:
                    blocks_out = abs(self.FallOffBlocksAwayFromCenter - dist)
                    current_strength = self.Strength - (blocks_out * self.FallOffPercent)
                    if current_strength <= 0:
                        continue
                    value = self.apply_falloff(voxel, current_strength)
                    voxel.Value = value
                    new_voxel_value = value
                voxel.Solidity = True if new_voxel_value > 0 else False

    def apply_pre_fall_off(self, voxel: Voxel) -> float:
        return self.Strength

    def apply_falloff(self, voxel: Voxel, current_strength) -> float:
        return current_strength


class AdditiveBrush(Brush):
    def apply_pre_fall_off(self, voxel: Voxel) -> float:
        return clamp(voxel.Value + self.Strength, 0.0, 1.0)

    def apply_falloff(self, voxel: Voxel, current_strength) -> float:
        return clamp(voxel.Value + current_strength, 0.0, 1.0)
