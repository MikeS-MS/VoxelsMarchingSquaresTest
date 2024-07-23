from brush import *
import perlin_noise
import pygame
import pygame.gfxdraw
from enum import Enum

# Debug controls:
# Up/Down Arrow - Changes the seed.
# Mouse Wheel Up/Down - Changes the zoom level of the noise.
# Shift + Mouse Wheel Up/Down - Changes the block size (basically the visual zoom, not noise zoom).
#
# ~ - Toggles between the modes to calculate values for blocks. Default calculates by summing all 8 blocks
#     around the current one and the current one and then averaging it, toggled changes it to only sum the
#     direct neighbours + current (left, right, up, down).
#
# 1 - Toggles between interpolating the midway points or not.
# 2 - Makes it so that the values for the blocks that are solid are flipped to negative.
# 3 - Anti-aliasing? I don't know, pygame is weird.
# 4 - Toggle the drawing of points in world space of each voxel. Yellow means a solid voxel, blue means an air voxel.
# 5 - Toggles the display of value numbers for each block.
#
# Mouse Button Left/Right - sets the block at the clicked location to air/solid
# Escape - Closes the application.


EdgePairs = [[0, 1],  # 0
             [3, 0],  # 1
             [1, 2],  # 2
             [2, 3],  # 3
             ]
CornerCombinations = [[-1, -1, -1, -1],  # 0
                      [0, 1, -1, -1],  # 1
                      [0, 2, -1, -1],  # 2
                      [1, 2, -1, -1],  # 3
                      [3, 2, -1, -1],  # 4
                      [0, 1, 3, 2],  # 5
                      [0, 3, -1, -1],  # 6
                      [1, 3, -1, -1],  # 7
                      [1, 3, -1, -1],  # 8
                      [3, 0, -1, -1],  # 9
                      [1, 0, 3, 2],  # 10
                      [3, 2, -1, -1],  # 11
                      [1, 2, -1, -1],  # 12
                      [0, 2, -1, -1],  # 13
                      [1, 0, -1, -1],  # 14
                      [-1, -1, -1, -1]  # 15
                      ]


class EMeshingAlgorithm(Enum):
    MarchingCubes = 0
    Squares = 1


# PB = PlacingBrush
# DB = DeletingBrush
class VoxelWorld:
    def __init__(self):
        self.CurrentIndexToChange = 0
        self.CurrentIndexToChange: int
        self.ScrollingIndexes = [
                                    "NoiseZoom",
                                    "BlockSize",
                                    "Brush_Size",
                                    "Brush_Strength",
                                    "Brush_StartFalloffPercent",
                                    "Brush_Falloff",
                                 ]
        self.Seed = 0
        self.Octaves = 2
        self.Zoom = 20
        self.Threshold = 0.0
        self.BlockSize = 25
        self.BlockBlending = 1
        self.DebugDrawPointSize = 5.0

        self.AA = False
        self.Invert = False
        self.AlgorithmToUse = EMeshingAlgorithm.MarchingCubes
        self.Interpolation = False
        self.OriginalMCMethod = False
        self.CheaperCalculation = False
        self.DebugPoints = True
        self.DebugNumbers = False
        self.DrawDebugMenu = True
        self.BrushIndex = 0

        self.PlacingBrush = Brush(4, 0.5, 0.5, 0.1)
        self.AdditiveBrush = AdditiveBrush(4, 0.12, 0.5, 0.1)
        self.DeletingBrush = Brush(4, 0.0, 1.0, 0.0)
        self.VoxelGrid = VoxelGridInfo(165, 165)
        self.LineList = []
        self.LineList: list[list]
        self.RenderSurface = None
        self.RenderSurface: pygame.surface.Surface

    def convert_to_grid_pos(self, x: float, y: float) -> (int, int):
        return math.floor(x / self.BlockSize), math.floor(y / self.BlockSize)

    def get_world_position(self, x: int, y: int) -> (float, float):
        return [float(x) * float(self.BlockSize), float(y) * float(self.BlockSize)]

    def get_brush_information(self) -> (int, float, float, float):
        if self.BrushIndex == 0:
            return self.PlacingBrush.Size, self.PlacingBrush.Strength, self.PlacingBrush.StartFallOff, self.PlacingBrush.FallOffPercent, "PlacingBrush"
        elif self.BrushIndex == 1:
            return self.AdditiveBrush.Size, self.AdditiveBrush.Strength, self.AdditiveBrush.StartFallOff, self.AdditiveBrush.FallOffPercent, "AdditiveBrush"
        elif self.BrushIndex == 2:
            return self.DeletingBrush.Size, self.DeletingBrush.Strength, self.DeletingBrush.StartFallOff, self.DeletingBrush.FallOffPercent, "DeletingBrush"

    def is_location_inside_screen(self, x: float, y: float):
        self.RenderSurface: pygame.surface.Surface
        size = self.RenderSurface.get_size()

        return 0 <= x < size[0] and 0 <= y < size[1]

    def set_block(self, x: float, y: float, status: bool):
        converted = self.convert_to_grid_pos(x, y)
        voxel = self.VoxelGrid.get_voxel(converted[0], converted[1] + 1)
        voxel.Solidity = status

        if status:
            voxel.Value = 1.0
        else:
            voxel.Value = 0.0

    def fill_list(self):
        self.VoxelGrid.VoxelList = []
        noise = perlin_noise.PerlinNoise(octaves=self.Octaves, seed=self.Seed)
        for x in range(0, self.VoxelGrid.SizeX):
            row = []
            for y in range(0, self.VoxelGrid.SizeY):
                value = noise.noise([float(x) / self.Zoom, float(y) / self.Zoom])
                solid = True if value < 0 else False
                voxel = Voxel(solid, value if self.OriginalMCMethod else (0.8 if solid else 0.0), x, y)
                row.append(voxel)
            self.VoxelGrid.VoxelList.append(row)

    # Calculates the value of the current block that'll be used in the interpolation.
    def calculate_value(self, x: int, y: int) -> float:
        aggregate = 0.0
        aggregate: float
        count = 0
        count: int
        is_solid = self.VoxelGrid.get_voxel(x, y).Solidity

        if self.CheaperCalculation:
            count = 4
            aggregate += float(int(self.VoxelGrid.get_voxel(x - 1, y).Solidity))
            aggregate += float(int(self.VoxelGrid.get_voxel(x + 1, y).Solidity))
            aggregate += float(int(self.VoxelGrid.get_voxel(x, y - 1).Solidity))
            aggregate += float(int(self.VoxelGrid.get_voxel(x, y + 1).Solidity))
            # can uncomment this
            # aggregate += float(int(get_voxel(x, y).Solidity))
        else:
            for dx in range(x - self.BlockBlending, x + self.BlockBlending + 1):
                for dy in range(y - self.BlockBlending, y + self.BlockBlending + 1):
                    # can change this
                    if dx == x and dy == y:
                        continue
                    count += 1
                    aggregate += float(int(self.VoxelGrid.get_voxel(dx, dy).Solidity))

        value = float(aggregate) / float(count)

        if self.Invert:
            return value if not self.VoxelGrid.get_voxel(x, y).Solidity else -value
        return value if is_solid else value

    def calculate_values(self):
        pass
        # if OriginalMCMethod:
        #     return
        #
        # for x in range(SizeX):
        #     for y in range(SizeY):
        #         voxel = VoxelList[x][y]
        #         voxel.Value = calculate_value(x, y)

    def get_configuration(self, corners: list[Voxel]) -> int:
        configuration = 0
        power = 1
        for i in range(len(corners)):
            configuration += int(corners[i].Value > self.Threshold) * power
            # if OriginalMCMethod else int(corners[i].Solidity) * power
            power *= 2
        return configuration

    def interp(self, first: (float, float), second: (float, float), interpolation: float) -> (float, float):
        result = [0, 0]
        result[0] = first[0] + ((second[0] - first[0]) * interpolation) + float(self.DebugDrawPointSize) / 2.0
        result[1] = first[1] + ((second[1] - first[1]) * interpolation) + float(self.DebugDrawPointSize) / 2.0
        return result

    # first_corner is always the one that's solid, second_corner is always the one that's air
    def get_middle_point(self, configuration: int, edge_index: int, corners: list[Voxel]) -> (float, float):
        edge = EdgePairs[CornerCombinations[configuration][edge_index]]
        first_corner = corners[edge[0]]
        second_corner = corners[edge[1]]

        first_pos = self.get_world_position(first_corner.X, first_corner.Y)
        second_pos = self.get_world_position(second_corner.X, second_corner.Y)

        first_value = first_corner.Value
        second_value = second_corner.Value

        if not self.Interpolation:
            return self.interp(first_pos, second_pos, 0.5)
        elif abs(self.Threshold - first_value) <= 0:
            return first_pos
        elif abs(self.Threshold - second_value) <= 0:
            return second_pos
        elif abs(first_value - second_value) <= 0:
            return first_pos

        medium_value = (self.Threshold - first_value) / (second_value - first_value)
        return self.interp(first_pos, second_pos, clamp(medium_value, 0.0, 1.0))

    def get_middle_point_my_own(self, configuration: int, edge_index: int, corners: list[Voxel]) -> (float, float):
        edge = EdgePairs[CornerCombinations[configuration][edge_index]]
        first_corner = corners[edge[0]]
        second_corner = corners[edge[1]]
        first_corner_valid = bool(first_corner.Solidity)

        first_corner_pos = self.get_world_position(first_corner.X, first_corner.Y)
        second_corner_pos = self.get_world_position(second_corner.X, second_corner.Y)

        first_pos = first_corner_pos if first_corner_valid else second_corner_pos
        second_pos = second_corner_pos if first_corner_valid else first_corner_pos

        first_value = (first_corner.Value if first_corner_valid else second_corner.Value)
        second_value = (second_corner.Value if first_corner_valid else first_corner.Value)

        if not self.Interpolation:
            return self.interp(first_pos, second_pos, 0.5)

        medium_value = first_value
        return self.interp(first_pos, second_pos, clamp(medium_value, 0.0, 1.0))

    def march_squares(self):
        self.LineList = []
        for x in range(self.VoxelGrid.SizeX):
            for y in range(self.VoxelGrid.SizeY):
                #   The order of corners when checking for surface is the following
                #    3 ---- 2
                #    |      |
                #    |      |
                #    0 ---- 1
                corners = [self.VoxelGrid.get_voxel(x, y),
                           self.VoxelGrid.get_voxel(x + 1, y),
                           self.VoxelGrid.get_voxel(x + 1, y + 1),
                           self.VoxelGrid.get_voxel(x, y + 1)]

                configuration = self.get_configuration(corners)
                if configuration == 0 or configuration == 15:
                    continue

                for i in range(0, 4, 2):
                    if CornerCombinations[configuration][i] == -1:
                        break
                    first_middle_point = self.get_middle_point(configuration, i, corners) if self.OriginalMCMethod else self.get_middle_point_my_own(configuration, i, corners)
                    second_middle_point = self.get_middle_point(configuration, i + 1, corners) if self.OriginalMCMethod else self.get_middle_point_my_own(configuration, i + 1, corners)
                    self.LineList.append([first_middle_point, second_middle_point])

    def squares(self):
        self.LineList = []
        for x in range(self.VoxelGrid.SizeX):
            for y in range(self.VoxelGrid.SizeY):
                voxel = self.VoxelGrid.VoxelList[x][y]

                if not voxel.Solidity:
                    continue

                top = self.VoxelGrid.get_voxel(x, y - 1)
                bottom = self.VoxelGrid.get_voxel(x, y + 1)
                left = self.VoxelGrid.get_voxel(x - 1, y)
                right = self.VoxelGrid.get_voxel(x + 1, y)

                current_pos = self.get_world_position(x, y)
                right_pos = self.get_world_position(x + 1, y)
                bottom_pos = self.get_world_position(x, y + 1)
                bottom_right_pos = self.get_world_position(x + 1, y + 1)

                if not left.Solidity:
                    self.LineList.append((current_pos, bottom_pos))

                if not right.Solidity:
                    self.LineList.append((right_pos, bottom_right_pos))

                if not top.Solidity:
                    self.LineList.append((current_pos, right_pos))

                if not bottom.Solidity:
                    self.LineList.append((bottom_pos, bottom_right_pos))

    def meshing_algorithm(self):
        if self.AlgorithmToUse == EMeshingAlgorithm.Squares:
            self.squares()
        elif self.AlgorithmToUse == EMeshingAlgorithm.MarchingCubes:
            self.march_squares()

    def list_voxels(self):
        for x in range(self.VoxelGrid.SizeX):
            line = ""
            for y in range(self.VoxelGrid.SizeY):
                line += str(self.VoxelGrid.VoxelList[x][y].Value)
                line += " "
            print(line)

    def draw_voxels(self, renderer: pygame.surface.Surface, font: pygame.font.Font):
        for x in range(self.VoxelGrid.SizeX):
            for y in range(self.VoxelGrid.SizeY):
                position = self.get_world_position(x, y)

                if not self.is_location_inside_screen(position[0], position[1]):
                    continue

                voxel = self.VoxelGrid.get_voxel(x, y)
                if self.DebugPoints:
                    renderer.fill((255, 255, 0, 255) if voxel.Solidity is True else (0, 200, 255, 255),
                                  pygame.rect.Rect(position[0], position[1], self.BlockSize / 5, self.BlockSize / 5))
                if self.DebugNumbers:
                    value_text = font.render(str(round(voxel.Value, 2)), True, (255, 255, 255, 255))
                    renderer.blit(value_text, (position[0] - value_text.get_size()[0] / 2, position[1]))

    def draw_outlines(self, renderer: pygame.surface.Surface):
        for line in self.LineList:
            first_pos = line[0]
            second_pos = line[1]

            first_is_inside = self.is_location_inside_screen(first_pos[0], first_pos[1])
            second_is_inside = self.is_location_inside_screen(second_pos[0], second_pos[1])

            if not first_is_inside and not second_is_inside:
                continue

            if self.AA:
                pygame.gfxdraw.line(renderer,
                                    int(line[0][0]),
                                    int(line[0][1]),
                                    int(line[1][0]),
                                    int(line[1][1]),
                                    (0, 0, 0, 255))
            else:
                pygame.draw.line(renderer, (0, 0, 0, 0), line[0], line[1])

    def draw_brush(self, renderer: pygame.surface.Surface):
        mouse_pos = pygame.mouse.get_pos()
        color = (0, 0, 0, 0)
        if self.BrushIndex == 0:
            pygame.draw.circle(renderer, color, mouse_pos, self.PlacingBrush.Size * self.BlockSize, 2)
            pygame.draw.circle(renderer, color, mouse_pos, self.PlacingBrush.FallOffBlocksAwayFromCenter * self.BlockSize, 1)
        elif self.BrushIndex == 1:
            pygame.draw.circle(renderer, color, mouse_pos, self.AdditiveBrush.Size * self.BlockSize, 2)
            pygame.draw.circle(renderer, color, mouse_pos, self.AdditiveBrush.FallOffBlocksAwayFromCenter * self.BlockSize, 1)
        elif self.BrushIndex == 2:
            pygame.draw.circle(renderer, color, mouse_pos, self.DeletingBrush.Size * self.BlockSize, 2)

    @staticmethod
    def draw_debug_values(renderer: pygame.surface.Surface, font: pygame.font.Font, values: dict[str:object]):
        current_y = 0
        max_x = 0
        max_y = 0
        texts = []
        for key in values:
            text = font.render(key + ": " + str(values[key]), True, (255, 255, 255, 255))
            texts.append(text)
            size = text.get_size()
            if size[0] > max_x:
                max_x = size[0]
            max_y += size[1]

        overlay = pygame.Surface((max_x, max_y))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(50)
        renderer.blit(overlay, (0, 0))
        for text in texts:
            renderer.blit(text, (0, current_y))
            size = text.get_size()
            current_y += size[1]

    def reset(self):
        self.fill_list()
        self.calculate_values()
        self.meshing_algorithm()

    def handle_scroll_up(self):
        if self.CurrentIndexToChange == 0:
            self.Zoom += 1
            self.reset()
        elif self.CurrentIndexToChange == 1:
            self.BlockSize += 1
            self.meshing_algorithm()
        elif self.CurrentIndexToChange == 2:
            if self.BrushIndex == 0:
                self.PlacingBrush.set_size(self.PlacingBrush.Size + 1)
            elif self.BrushIndex == 1:
                self.AdditiveBrush.set_size(self.AdditiveBrush.Size + 1)
            elif self.BrushIndex == 2:
                self.DeletingBrush.set_size(self.DeletingBrush.Size + 1)
        elif self.CurrentIndexToChange == 3:
            if self.BrushIndex == 0:
                self.PlacingBrush.Strength = clamp(self.PlacingBrush.Strength + 0.01, 0.0, 1.0)
            elif self.BrushIndex == 1:
                self.AdditiveBrush.Strength = clamp(self.AdditiveBrush.Strength + 0.01, 0.0, 1.0)
        elif self.CurrentIndexToChange == 4:
            if self.BrushIndex == 0:
                self.PlacingBrush.set_start_falloff(self.PlacingBrush.StartFallOff + 0.01)
            elif self.BrushIndex == 1:
                self.AdditiveBrush.set_start_falloff(self.AdditiveBrush.StartFallOff + 0.01)
        elif self.CurrentIndexToChange == 5:
            if self.BrushIndex == 0:
                self.PlacingBrush.FallOffPercent = clamp(self.PlacingBrush.FallOffPercent + 0.01, 0.0, 1.0)
            elif self.BrushIndex == 1:
                self.AdditiveBrush.FallOffPercent = clamp(self.AdditiveBrush.FallOffPercent + 0.01, 0.0, 1.0)

    def handle_scroll_down(self):
        if self.CurrentIndexToChange == 0:
            self.Zoom = clamp(self.Zoom - 1, 0, self.Zoom)
            self.reset()
        elif self.CurrentIndexToChange == 1:
            self.BlockSize = clamp(self.BlockSize - 1, 0, self.BlockSize)
            self.meshing_algorithm()
        elif self.CurrentIndexToChange == 2:
            if self.BrushIndex == 0:
                self.PlacingBrush.set_size(clamp(self.PlacingBrush.Size - 1, 0, self.PlacingBrush.Size))
            elif self.BrushIndex == 1:
                self.AdditiveBrush.set_size(clamp(self.AdditiveBrush.Size - 1, 0, self.AdditiveBrush.Size))
            elif self.BrushIndex == 2:
                self.DeletingBrush.set_size(clamp(self.DeletingBrush.Size - 1, 0, self.DeletingBrush.Size))
        elif self.CurrentIndexToChange == 3:
            if self.BrushIndex == 0:
                self.PlacingBrush.Strength = clamp(self.PlacingBrush.Strength - 0.01, 0.0, self.PlacingBrush.Strength)
            elif self.BrushIndex == 1:
                self.AdditiveBrush.Strength = clamp(self.AdditiveBrush.Strength - 0.01, 0.0, self.AdditiveBrush.Strength)
        elif self.CurrentIndexToChange == 4:
            if self.BrushIndex == 0:
                self.PlacingBrush.set_start_falloff(self.PlacingBrush.StartFallOff - 0.01)
            elif self.BrushIndex == 1:
                self.AdditiveBrush.set_start_falloff(self.AdditiveBrush.StartFallOff - 0.01)
        elif self.CurrentIndexToChange == 5:
            if self.BrushIndex == 0:
                self.PlacingBrush.FallOffPercent = clamp(self.PlacingBrush.FallOffPercent - 0.01, 0.0, self.PlacingBrush.FallOffPercent)
            elif self.BrushIndex == 1:
                self.AdditiveBrush.FallOffPercent = clamp(self.AdditiveBrush.FallOffPercent - 0.01, 0.0, self.AdditiveBrush.FallOffPercent)


    def run(self):
        self.reset()
        pygame.init()
        window = pygame.display
        window.set_caption("Voxels Test")
        image = pygame.image.load("icon.png")
        window.set_icon(image)
        renderer = window.set_mode((1280, 720), flags=pygame.RESIZABLE)
        self.RenderSurface = renderer
        debug_font = pygame.font.SysFont("arial", 32)
        small_debug_font = pygame.font.SysFont("arial", int(self.BlockSize / 2))
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    shift_pressed = pygame.key.get_pressed()[pygame.K_LSHIFT]
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    if event.key == pygame.K_BACKQUOTE:
                        self.CheaperCalculation = not self.CheaperCalculation
                        self.calculate_values()
                        self.meshing_algorithm()
                    if event.key == pygame.K_b:
                        self.BrushIndex = 0
                    if event.key == pygame.K_a:
                        self.BrushIndex = 1
                    if event.key == pygame.K_e:
                        self.BrushIndex = 2
                    if event.key == pygame.K_q:
                        self.DrawDebugMenu = not self.DrawDebugMenu
                    if event.key == pygame.K_1:
                        if shift_pressed:
                            self.Interpolation = not self.Interpolation
                            self.meshing_algorithm()
                        else:
                            self.CurrentIndexToChange = 0
                    if event.key == pygame.K_2:
                        if shift_pressed:
                            self.Invert = not self.Invert
                            self.calculate_values()
                            self.meshing_algorithm()
                        else:
                            self.CurrentIndexToChange = 1
                    if event.key == pygame.K_3:
                        if shift_pressed:
                            self.AA = not self.AA
                        else:
                            self.CurrentIndexToChange = 2
                    if event.key == pygame.K_4:
                        if shift_pressed:
                            self.DebugPoints = not self.DebugPoints
                        else:
                            self.CurrentIndexToChange = 3
                    if event.key == pygame.K_5:
                        if shift_pressed:
                            self.DebugNumbers = not self.DebugNumbers
                        else:
                            self.CurrentIndexToChange = 4
                    if event.key == pygame.K_6:
                        self.CurrentIndexToChange = 5
                    if event.key == pygame.K_7:
                        self.CurrentIndexToChange = 6
                    if event.key == pygame.K_UP:
                        self.Seed += 1
                        self.reset()
                    if event.key == pygame.K_DOWN:
                        self.Seed -= 1
                        self.reset()
                    if event.key == pygame.K_LEFT:
                        self.Threshold -= 0.01
                        self.meshing_algorithm()
                    if event.key == pygame.K_RIGHT:
                        self.Threshold += 0.01
                        self.meshing_algorithm()
                    if event.key == pygame.K_LEFTBRACKET:
                        pass
                        # CurrentBlockValueIndex = clamp(CurrentBlockValueIndex - 1, 0, len(PossibleBlockValues) - 1)
                    if event.key == pygame.K_RIGHTBRACKET:
                        pass
                        # CurrentBlockValueIndex = clamp(CurrentBlockValueIndex + 1, 0, len(PossibleBlockValues) - 1)

                if event.type == pygame.MOUSEWHEEL:
                    if event.y < 0:
                        self.handle_scroll_down()
                    if event.y > 0:
                        self.handle_scroll_up()

                if pygame.mouse.get_pressed()[0]:
                    pos = pygame.mouse.get_pos()
                    converted = self.convert_to_grid_pos(pos[0], pos[1])
                    if self.BrushIndex == 0:
                        self.PlacingBrush.apply_to_grid(converted[0], converted[1], self.VoxelGrid)
                    elif self.BrushIndex == 1:
                        self.AdditiveBrush.apply_to_grid(converted[0], converted[1], self.VoxelGrid)
                    elif self.BrushIndex == 2:
                        self.DeletingBrush.apply_to_grid(converted[0], converted[1], self.VoxelGrid)
                    # set_block(pos[0], pos[1], False)
                    self.calculate_values()
                    self.meshing_algorithm()

            renderer.fill((127, 127, 127, 127))
            self.draw_outlines(renderer)
            self.draw_voxels(renderer, small_debug_font)
            self.draw_brush(renderer)

            brush_info = self.get_brush_information()
            if self.DrawDebugMenu:
                VoxelWorld.draw_debug_values(renderer, debug_font, {
                    "Seed": self.Seed,
                    "Zoom": self.Zoom,
                    "BlockSize": self.BlockSize,
                    "Threshold": self.Threshold,
                    self.ScrollingIndexes[2]: brush_info[0],
                    self.ScrollingIndexes[3]: brush_info[1],
                    self.ScrollingIndexes[4]: brush_info[2],
                    self.ScrollingIndexes[5]: brush_info[3],
                    "CurrentlyModifying": self.ScrollingIndexes[self.CurrentIndexToChange],
                    "CurrentBrush": brush_info[4]
                })
            window.flip()

        pygame.quit()


if __name__ == '__main__':
    voxel_world = VoxelWorld()
    voxel_world.run()
