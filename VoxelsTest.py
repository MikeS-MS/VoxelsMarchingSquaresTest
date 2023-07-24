import math
import perlin_noise
import pygame
import pygame.gfxdraw

# Debug controls:
# Up/Down Arrow - Changes the seed.
# Mouse Wheel Up/Down - Changes the zoom level of the noise.
# Shift + Mouse Wheel Up/Down - Changes the block size (basically the visual zoom, not noise zoom).
# ~ - Toggles between the modes to calculate values for blocks. Default calculates by summing all 8 blocks
# around the current one and the current one and averaging it, toggled changes it to only sum the direct neighbours
# (left, right, up, down)
# 1 - Toggles between interpolating the midway points or not.
# 2 - Makes it so that the values for the blocks that are solid are flipped to negative.
# 3 - Anti-aliasing? idk, pygame is weird.
# 4 - Toggle the drawing of points in world space of each voxel.
# 5 - Toggles the display of value numbers for each block.
# Mouse Button Left/Right - sets the block at the clicked location to air/solid
# Escape - Closes the application.


class Voxel:
    def __init__(self, solidity: bool, x: int, y: int):
        self.Solidity = solidity
        self.Value = 0.0
        self.X = x
        self.Y = y


EdgePairs = [[0, 1], #0
             [1, 0], #1
             [0, 3], #2
             [3, 0], #3
             [1, 2], #4
             [2, 1], #5
             [3, 2], #6
             [2, 3]  #7
             ]
CornerCombinations = [[-1, -1, -1, -1],   #0
                      [0, 2, -1, -1],     #1
                      [1, 4, -1, -1],     #2
                      [2, 4, -1, -1],     #3
                      [7, 5, -1, -1],     #4
                      [0, 2, 7, 5],       #5
                      [1, 7, -1, -1],     #6
                      [2, 7, -1, -1],     #7
                      [3, 6, -1, -1],     #8
                      [6, 0, -1, -1],     #9
                      [3, 1, 6, 4],       #10
                      [6, 4, -1, -1],     #11
                      [3, 5, -1, -1],     #12
                      [0, 5, -1, -1],     #13
                      [3, 1, -1, -1],     #14
                      [-1, -1, -1, -1]    #15
                      ]


# Constants you can change.
SizeX = 100
SizeY = 50
Zoom = 20
Seed = 0
Octaves = 2
Threshold = 0.5
BlockSize = 25.0
BlockBlending = 1
DebugDrawPointSize = 5.0
AA = False
Invert = False
CheaperCalculation = False
Interpolation = False
DebugPoints = False
DebugNumbers = False

# Data.
VoxelList = []
VoxelList: list[list[Voxel]]
LineList = []
LineList: list[list]


def convert_to_grid_pos(x: float, y: float) -> (int, int):
    return math.floor(x / BlockSize), math.floor(y / BlockSize)


def set_block(x: float, y: float, status: bool):
    converted = convert_to_grid_pos(x, y)
    get_voxel(converted[0], converted[1] + 1).Solidity = status


def fill_list():
    global VoxelList
    VoxelList = []
    noise = perlin_noise.PerlinNoise(octaves=Octaves, seed=Seed)
    for x in range(0, SizeX):
        row = []
        for y in range(0, SizeY):
            value = noise.noise([float(x) / Zoom, float(y) / Zoom])
            voxel = Voxel(True if value > 0.01 else False, x, y)
            voxel.Value = 1.0 if voxel.Solidity else 0.0
            row.append(voxel)
        VoxelList.append(row)


def get_voxel(x: int, y: int) -> Voxel:
    if (x >= SizeX or x < 0) or (y >= SizeY or y < 0):
        return Voxel(False, x, y)
    return VoxelList[x][y]


def get_world_position(x: int, y: int) -> (float, float):
    return [float(x) * float(BlockSize), float(y) * float(BlockSize)]


def clamp(value: float, minimum: float, maximum: float) -> float:
    if minimum > maximum:
        minimum = maximum
    if maximum < minimum:
        maximum = minimum

    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


# Calculates the value of the current block that'll be used in the interpolation.
def calculate_value(x: int, y: int) -> float:
    summ = 0.0
    summ: float
    count = 0
    count: int

    if CheaperCalculation:
        count = 5
        summ += int(get_voxel(x - 1, y).Solidity)
        summ += int(get_voxel(x + 1, y).Solidity)
        summ += int(get_voxel(x, y - 1).Solidity)
        summ += int(get_voxel(x, y + 1).Solidity)
        summ += int(get_voxel(x, y).Solidity)
    else:
        for dx in range(x - 1, x + 2):
            for dy in range(y - 1, y + 2):
                summ += int(get_voxel(dx, dy).Solidity)
                count += 1

    value = float(summ) / float(count)

    if Invert:
        value = value if not get_voxel(x, y).Solidity else -value
    return value


def calculate_values():
    global VoxelList
    for x in range(SizeX):
        for y in range(SizeY):
            voxel = VoxelList[x][y]
            voxel.Value = calculate_value(x, y)


def get_configuration(corners: list) -> int:
    configuration = 0
    power = 1
    for i in range(len(corners)):
        configuration += int(corners[i].Solidity) * power
        power *= 2
    return configuration


def interp(first: (float, float), second: (float, float), interpolation: float) -> (float, float):
    result = [0, 0]
    result[0] = first[0] + ((second[0] - first[0]) * interpolation) + float(DebugDrawPointSize) / 2.0
    result[1] = first[1] + ((second[1] - first[1]) * interpolation) + float(DebugDrawPointSize) / 2.0
    return result


# first_corner is always the one that's solid, second_corner is always the one that's air
def get_middle_point(configuration: int, edge_index: int, corners: list) -> (float, float):
    edge = EdgePairs[CornerCombinations[configuration][edge_index]]
    first_corner = corners[edge[0]]
    second_corner = corners[edge[1]]
    first_pos = get_world_position(first_corner.X, first_corner.Y)
    second_pos = get_world_position(second_corner.X, second_corner.Y)

    if not Interpolation:
        return interp(first_pos, second_pos, 0.5)
    elif abs(Threshold - first_corner.Value) <= 0:
        return first_pos
    elif abs(Threshold - second_corner.Value) <= 0:
        return second_pos
    elif abs(first_corner.Value - second_corner.Value) <= 0:
        return first_pos

    medium_value = (Threshold - first_corner.Value) / (second_corner.Value - first_corner.Value)
    return interp(first_pos, second_pos, clamp(medium_value, 0.0, 1.0))


def march_squares():
    global LineList

    LineList = []
    for x in range(SizeX):
        for y in range(SizeY):
            #   The order of corners when checking for surface is the following
            #    3 ---- 2
            #    |      |
            #    |      |
            #    0 ---- 1
            corners = [get_voxel(x, y),
                       get_voxel(x + 1, y),
                       get_voxel(x + 1, y + 1),
                       get_voxel(x, y + 1)]

            configuration = get_configuration(corners)
            if configuration == 0 or configuration == 15:
                continue

            for i in range(0, 4, 2):
                if CornerCombinations[configuration][i] == -1:
                    break
                first_middle_point = get_middle_point(configuration, i, corners)
                second_middle_point = get_middle_point(configuration, i + 1, corners)
                LineList.append([first_middle_point, second_middle_point])


def list_voxels():
    for x in range(SizeX):
        line = ""
        for y in range(SizeY):
            line += str(VoxelList[x][y].Value)
            line += " "
        print(line)


def draw_voxels(renderer: pygame.surface.Surface, font: pygame.font.Font):
    for x in range(SizeX):
        for y in range(SizeY):
            position = get_world_position(x, y)
            voxel = get_voxel(x, y)
            if DebugPoints:
                renderer.fill((255, 255, 0, 255) if VoxelList[x][y].Solidity is True else (0, 200, 255, 255),
                              pygame.rect.Rect(position[0], position[1], BlockSize / 5, BlockSize / 5))
            if DebugNumbers:
                value_text = font.render(str(round(voxel.Value, 2)), True, (255, 255, 255, 255))
                renderer.blit(value_text, (position[0] - value_text.get_size()[0] / 2, position[1]))


def draw_outlines(renderer: pygame.surface.Surface):
    for line in LineList:
        if AA:
            pygame.gfxdraw.line(renderer,
                                int(line[0][0]),
                                int(line[0][1]),
                                int(line[1][0]),
                                int(line[1][1]),
                                (0, 0, 0, 255))
        else:
            pygame.draw.line(renderer, (0, 0, 0, 0), line[0], line[1])


def reset():
    fill_list()
    calculate_values()
    march_squares()


def test_voxels():
    global BlockSize
    global Zoom
    global Seed
    global AA
    global CheaperCalculation
    global Invert
    global Interpolation
    global DebugPoints
    global DebugNumbers
    global VoxelList
    global LineList

    reset()
    pygame.init()
    window = pygame.display
    window.set_caption("Voxels Test")
    image = pygame.image.load("icon.png")
    window.set_icon(image)
    renderer = window.set_mode((1280, 720), flags=pygame.RESIZABLE)
    debug_font = pygame.font.SysFont("arial", 32)
    small_debug_font = pygame.font.SysFont("arial", int(BlockSize / 2))
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_BACKQUOTE:
                    CheaperCalculation = not CheaperCalculation
                    calculate_values()
                    march_squares()
                if event.key == pygame.K_1:
                    Interpolation = not Interpolation
                    march_squares()
                if event.key == pygame.K_2:
                    Invert = not Invert
                    calculate_values()
                    march_squares()
                if event.key == pygame.K_3:
                    AA = not AA
                if event.key == pygame.K_4:
                    DebugPoints = not DebugPoints
                if event.key == pygame.K_5:
                    DebugNumbers = not DebugNumbers
                if event.key == pygame.K_UP:
                    Seed += 1
                    reset()
                if event.key == pygame.K_DOWN:
                    Seed -= 1
                    reset()
            if event.type == pygame.MOUSEWHEEL:
                if event.y < 0:
                    if pygame.key.get_pressed()[pygame.K_LSHIFT]:
                        BlockSize -= 1
                        small_debug_font = pygame.font.SysFont("arial", int(BlockSize / 1.8))
                    else:
                        Zoom -= 1
                    reset()
                if event.y > 0:
                    if pygame.key.get_pressed()[pygame.K_LSHIFT]:
                        small_debug_font = pygame.font.SysFont("arial", int(BlockSize / 1.8))
                        BlockSize += 1
                    else:
                        Zoom += 1
                    reset()

            if pygame.mouse.get_pressed()[0]:
                pos = pygame.mouse.get_pos()
                set_block(pos[0], pos[1], False)
                calculate_values()
                march_squares()
            if pygame.mouse.get_pressed()[2]:
                pos = pygame.mouse.get_pos()
                set_block(pos[0], pos[1], True)
                calculate_values()
                march_squares()

        renderer.fill((127, 127, 127, 127))
        draw_outlines(renderer)
        draw_voxels(renderer, small_debug_font)
        seed_text = debug_font.render("Seed: " + str(Seed), True, (255, 255, 255, 255))
        block_size_text = debug_font.render("Block Size: " + str(BlockSize), True, (255, 255, 255, 255))
        zoom_text = debug_font.render("Zoom: " + str(Zoom), True, (255, 255, 255, 255))
        renderer.blit(seed_text, (0, 0))
        renderer.blit(block_size_text, (0, seed_text.get_size()[1]))
        renderer.blit(zoom_text, (0, block_size_text.get_size()[1] + seed_text.get_size()[1]))
        window.flip()

    pygame.quit()


if __name__ == '__main__':
    test_voxels()
