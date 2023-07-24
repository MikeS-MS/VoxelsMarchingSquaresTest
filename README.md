# Python requirement
 - Python 3.9
# Required modules
 - pygame
 - perlin-noise
# Debug controls
- Up/Down Arrow - Changes the seed.
- Mouse Wheel Up/Down - Changes the zoom level of the noise.
- Shift + Mouse Wheel Up/Down - Changes the block size (basically the visual zoom, not noise zoom).
- ~ - Toggles between the modes to calculate values for blocks. Default calculates by summing all 8 blocks around the current one and the current one and averaging it, toggled changes it to only sum the direct neighbours (left, right, up, down)
- 1 - Toggles between interpolating the midway points or not.
- 2 - Makes it so that the calculated values for the blocks that are solid are flipped to negative.
- 3 - Anti-aliasing? idk, pygame is weird.
- 4 - Toggle the drawing of points in world space of each voxel.
- 5 - Toggles the display of value numbers for each block.
- Mouse Button Left/Right - sets the block at the clicked location to air/solid
- Escape - Closes the application.
